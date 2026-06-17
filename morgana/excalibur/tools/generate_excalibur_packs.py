#!/usr/bin/env python3
"""
Excalibur Pack Generator — X3M.AI
Uses Azure OpenAI to generate complete Excalibur pack JSON files
for all MITRE ATT&CK domains, platforms, and tactics.

Usage:
    Set environment variables first:
        $env:AZURE_OPENAI_KEY = "your-key"
        $env:AZURE_OPENAI_ENDPOINT = "https://x3m-ai.openai.azure.com/"
        $env:AZURE_OPENAI_DEPLOYMENT = "gpt-4o"

    Run all jobs:
        python generate_excalibur_packs.py

    Run a single job by index (0-based):
        python generate_excalibur_packs.py --job 0

    Dry run (show prompts without calling API):
        python generate_excalibur_packs.py --dry-run

    Force regenerate even if file exists:
        python generate_excalibur_packs.py --force

    Filter by domain:
        python generate_excalibur_packs.py --domain enterprise-attack
        python generate_excalibur_packs.py --domain ics-attack
        python generate_excalibur_packs.py --domain mobile-attack

    Filter by platform:
        python generate_excalibur_packs.py --platform windows
        python generate_excalibur_packs.py --platform linux

    Filter by tactic:
        python generate_excalibur_packs.py --tactic TA0002
"""

import json
import os
import sys
import time
import argparse
import traceback
from pathlib import Path
from datetime import datetime, timezone
import urllib.request
import urllib.error
import urllib.parse
import logging

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TOOLS_DIR = Path(__file__).parent
EXCALIBUR_DIR = TOOLS_DIR.parent
JOBS_FILE = TOOLS_DIR / "generation_jobs.json"
LOG_FILE = TOOLS_DIR / "generation_log.json"
REFERENCE_PACK = EXCALIBUR_DIR / "excalibur-persistence-emulation-pack.json"

# ---------------------------------------------------------------------------
# Azure OpenAI config
# ---------------------------------------------------------------------------
AZURE_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_KEY = os.environ.get("AZURE_OPENAI_KEY", "")
AZURE_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5-codex")
AZURE_API_VERSION = "2024-12-01-preview"

MAX_RETRIES = 5
RETRY_DELAYS = [10, 20, 40, 80, 160]
REQUEST_TIMEOUT = 300

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(TOOLS_DIR / "generator.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("excalibur-gen")


# ---------------------------------------------------------------------------
# Compact schema reference for system prompt
# ---------------------------------------------------------------------------
PACK_SCHEMA = """
TOP-LEVEL PACK SCHEMA (exact field names required):
{
  "package_id": "excalibur-{domain-short}-{platform}-{tactic_id}-{tactic_slug}",
  "package_name": "Excalibur - {Domain} {Platform} {TacticName} ({TacticID})",
  "version": "1.0.0",
  "description": "...",
  "author": "X3M.AI",
  "created": "YYYY-MM-DD",
  "mitre_domain": "enterprise-attack | ics-attack | mobile-attack",
  "mitre_tactic": "TA0002",
  "mitre_tactic_name": "Execution",
  "platform": "windows | linux | android | ios",
  "prerequisites": ["..."],
  "tag_categories": [ ... ],
  "scripts": [ ... ],
  "chains": [ ... ]
}

SCRIPT SCHEMA (one script per technique/sub-technique):
{
  "id": "Excalibur - {Domain}-{Platform}-{TCode}-{TechniqueName}",
  "name": "Excalibur - {Domain}-{Platform}-{TCode}-{TechniqueName}",
  "description": "Detailed description: what it simulates, what telemetry it generates, which Sentinel/SIEM rule it triggers.",
  "tactic": "Persistence",
  "tcode": "T1547.001",
  "technique_name": "Boot or Logon Autostart Execution: Registry Run Keys / Startup Folder",
  "executor": "powershell",
  "platform": "windows",
  "required_tags": ["tag_key_1", "tag_key_2"],
  "command": "Write-Host '[START] ...'; try { ... Write-Host '[SUCCESS] ...' } catch { Write-Host ('[ERROR] ' + $_.Exception.Message) }",
  "cleanup_command": "...",
  "detection_rule": "Sentinel rule name or detection description",
  "sentinel_connector": "Microsoft Defender for Endpoint | Windows Security Events via AMA | Sysmon | ...",
  "package": "excalibur",
  "package_id": "<same as top-level package_id>"
}

CHAIN SCHEMA (one chain per technique/sub-technique):
{
  "id": "{package_id}-chain-{tcode}",
  "name": "{TCode} - {TechniqueName}",
  "description": "...",
  "steps": [
    { "script_id": "<script id>", "order": 1 }
  ],
  "package_id": "<same as top-level package_id>"
}

TAG_CATEGORY SCHEMA:
{
  "category_id": "common_local",
  "label": "...",
  "description": "...",
  "scope": "local",
  "used_by_tcodes": ["T1547.001"],
  "tags": [
    {
      "key": "excalibur_temp_dir",
      "label": "Temp Directory",
      "description": "...",
      "default": "C:\\\\ProgramData\\\\Morgana\\\\temp",
      "example": "C:\\\\ProgramData\\\\Morgana\\\\temp",
      "sensitive": false,
      "required": false
    }
  ]
}
"""

EXAMPLE_SCRIPT_WINDOWS = """{
  "id": "Excalibur - Enterprise-Windows-T1547.001-Registry Run Keys",
  "name": "Excalibur - Enterprise-Windows-T1547.001-Registry Run Keys",
  "description": "Writes a value to HKCU:\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run, simulating Run Key persistence. Removed immediately after creation. Generates MDE registry modification telemetry and Sentinel alert.",
  "tactic": "Persistence",
  "tcode": "T1547.001",
  "technique_name": "Boot or Logon Autostart Execution: Registry Run Keys / Startup Folder",
  "executor": "powershell",
  "platform": "windows",
  "required_tags": ["excalibur_temp_dir"],
  "command": "Write-Host '[START] T1547.001 - Registry Run Keys persistence'; $regPath = 'HKCU:\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run'; $valueName = 'MorganaTest-AutoRun'; $valuePath = 'C:\\\\Windows\\\\System32\\\\calc.exe'; try { New-ItemProperty -Path $regPath -Name $valueName -Value $valuePath -PropertyType String -Force | Out-Null; Write-Host ('[INFO] Run key created: ' + $regPath + ' -> ' + $valueName); Start-Sleep 2; Remove-ItemProperty -Path $regPath -Name $valueName -ErrorAction SilentlyContinue; Write-Host '[SUCCESS] T1547.001 - Registry Run key created and removed. Sentinel target: Registry Key Created for Boot/Logon Autostart' } catch { Write-Host ('[ERROR] ' + $_.Exception.Message); Remove-ItemProperty -Path $regPath -Name $valueName -ErrorAction SilentlyContinue }",
  "cleanup_command": "Remove-ItemProperty -Path 'HKCU:\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run' -Name 'MorganaTest-AutoRun' -ErrorAction SilentlyContinue; Write-Host '[INFO] Cleanup complete'",
  "detection_rule": "Registry Key Created for Boot/Logon Autostart Execution",
  "sentinel_connector": "Microsoft Defender for Endpoint",
  "package": "excalibur"
}"""

EXAMPLE_SCRIPT_LINUX = """{
  "id": "Excalibur - Enterprise-Linux-T1053.003-Cron Job",
  "name": "Excalibur - Enterprise-Linux-T1053.003-Cron Job",
  "description": "Creates a cron job entry simulating scheduled task persistence via crontab. Entry is removed immediately. Generates auditd/syslog telemetry.",
  "tactic": "Persistence",
  "tcode": "T1053.003",
  "technique_name": "Scheduled Task/Job: Cron",
  "executor": "bash",
  "platform": "linux",
  "required_tags": ["excalibur_temp_dir_linux"],
  "command": "echo '[START] T1053.003 - Cron Job persistence'; TMPDIR=#{excalibur_temp_dir_linux}; mkdir -p $TMPDIR; CRON_ENTRY='* * * * * /bin/echo morgana-test'; CRON_FILE=$TMPDIR/morgana_cron_test; echo $CRON_ENTRY > $CRON_FILE; crontab -l 2>/dev/null > $CRON_FILE.bak; (crontab -l 2>/dev/null; echo \"$CRON_ENTRY\") | crontab - && echo '[INFO] Cron entry added' || echo '[WARN] crontab not available, creating /etc/cron.d entry'; sleep 2; crontab -l | grep -v 'morgana-test' | crontab - && echo '[INFO] Cron entry removed'; rm -f $CRON_FILE $CRON_FILE.bak; echo '[SUCCESS] T1053.003 - Cron persistence simulated and cleaned. Detection: auditd crontab modification'",
  "cleanup_command": "crontab -l 2>/dev/null | grep -v 'morgana-test' | crontab - 2>/dev/null; rm -f #{excalibur_temp_dir_linux}/morgana_cron_test*; echo '[INFO] Cleanup complete'",
  "detection_rule": "Scheduled Task/Job: Cron (auditd/syslog)",
  "sentinel_connector": "Syslog / auditd via AMA",
  "package": "excalibur"
}"""


def build_system_prompt(platform: str, domain: str) -> str:
    executor_info = ""
    if platform == "windows":
        executor_info = 'For Windows: executor is "powershell", use PowerShell 5.1 syntax. Temp files: C:\\\\ProgramData\\\\Morgana\\\\temp (via #{excalibur_temp_dir} tag).'
        example = EXAMPLE_SCRIPT_WINDOWS
    elif platform == "linux":
        executor_info = 'For Linux: executor is "bash", use bash syntax. Temp files: /tmp/morgana-test/ (via #{excalibur_temp_dir_linux} tag).'
        example = EXAMPLE_SCRIPT_LINUX
    elif platform == "android":
        executor_info = 'For Android: executor is "bash", use adb shell commands or bash simulation. Document detection via Android security tooling or MDM.'
        example = EXAMPLE_SCRIPT_LINUX
    elif platform == "ios":
        executor_info = 'For iOS: executor is "bash", use bash simulation commands. Document detection via MDM / mobile security tooling.'
        example = EXAMPLE_SCRIPT_LINUX
    else:
        executor_info = f'Platform: {platform}. Use the most appropriate executor and syntax.'
        example = EXAMPLE_SCRIPT_LINUX

    return f"""You are an expert Red Team engineer and adversary emulation specialist at X3M.AI.
You generate Excalibur attack scripts for the Morgana Red Team platform.
Your output must be valid JSON only — no markdown fences, no explanation text, no comments.

CRITICAL RULES:
1. Return ONLY valid JSON — no markdown, no text before or after the JSON object.
2. NEVER use emoji. Use [START], [SUCCESS], [ERROR], [INFO], [WARN] tags only.
3. Every #{{tag_key}} placeholder in a command MUST appear in required_tags.
4. cleanup_command MUST reverse exactly what command does.
5. All scripts MUST be test-safe: no real damage, use TEST-NET IPs (198.51.100.x) for network targets.
6. Scripts MUST include try/catch (PowerShell) or explicit error handling (bash).
7. Scripts MUST end with a clear [SUCCESS] or [ERROR] message.
8. Temp files on Windows: C:\\\\ProgramData\\\\Morgana\\\\temp ONLY (via #{{excalibur_temp_dir}} tag).
9. Temp files on Linux: /tmp/morgana-test/ (via #{{excalibur_temp_dir_linux}} tag).
10. sensitive: true is REQUIRED for passwords, secrets, tokens, API keys.
11. Each technique and sub-technique that applies to this platform gets exactly 1 script and 1 chain.
12. Tag keys must be globally unique within the pack (use technique code as prefix, e.g. excalibur_t1547_runkey_name).
13. Scripts must generate realistic telemetry detectable by Microsoft Sentinel or equivalent SIEM.

{executor_info}

DOMAIN: {domain}

SCHEMA REFERENCE:
{PACK_SCHEMA}

EXAMPLE SCRIPT:
{example}
"""


def build_user_prompt(job: dict) -> str:
    domain = job["domain"]
    platform = job["platform"]
    tactic_id = job["tactic_id"]
    tactic_name = job["tactic_name"]
    techniques = job.get("techniques", [])
    package_id = build_package_id(job)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    techniques_list = ""
    if techniques:
        techniques_list = f"\nTechniques to cover (cover ALL of these plus any additional applicable sub-techniques): {', '.join(techniques)}"

    domain_label_map = {
        "enterprise-attack": "Enterprise",
        "ics-attack": "ICS",
        "mobile-attack": "Mobile",
    }
    domain_label = domain_label_map.get(domain, domain)

    return f"""Generate a complete Excalibur pack JSON for:
- MITRE ATT&CK Domain: {domain} ({domain_label})
- Tactic: {tactic_id} — {tactic_name}
- Platform: {platform}
- package_id: {package_id}
- created: {today}
{techniques_list}

Requirements:
- Cover ALL techniques and sub-techniques in {tactic_id} ({tactic_name}) that apply to {platform}.
- Use MITRE ATT&CK v15 technique list.
- Each technique/sub-technique gets exactly 1 script and 1 chain entry.
- All commands must be realistic, functional, and generate telemetry detectable by a SIEM.
- Include a "tag_categories" block with one category per technique/group of related techniques.
- Include a "prerequisites" array (max 6 items, realistic for {platform}).
- The "scripts" array must have at least 8 scripts (more is better — cover all sub-techniques).
- Every script must have: id, name, description, tactic, tcode, technique_name, executor, platform, required_tags, command, cleanup_command, detection_rule, sentinel_connector, package, package_id.
- Every chain must have: id, name, description, steps (array with script_id and order), package_id.

Return ONLY the JSON object. No markdown, no explanation.
"""


def build_package_id(job: dict) -> str:
    domain = job["domain"]
    platform = job["platform"]
    tactic_id = job["tactic_id"].lower()
    tactic_slug = job["tactic_name"].lower().replace(" ", "").replace("/", "")

    domain_short_map = {
        "enterprise-attack": "enterprise",
        "ics-attack": "ics",
        "mobile-attack": "mobile",
    }
    domain_short = domain_short_map.get(domain, domain.split("-")[0])

    return f"excalibur-{domain_short}-{platform}-{tactic_id}-{tactic_slug}"


def call_azure_openai(system_prompt: str, user_prompt: str) -> str:
    """Call Azure OpenAI chat completions API. Returns the response content string."""
    if not AZURE_KEY:
        raise ValueError("AZURE_OPENAI_KEY environment variable is not set.")
    if not AZURE_ENDPOINT:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is not set.")

    url = f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions?api-version={AZURE_API_VERSION}"

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 16000,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "api-key": AZURE_KEY,
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]


def validate_pack(pack: dict, job: dict) -> list:
    """Validate pack structure. Returns list of error strings."""
    errors = []
    required_top = [
        "package_id", "package_name", "version", "description", "author",
        "created", "mitre_domain", "mitre_tactic", "mitre_tactic_name",
        "platform", "prerequisites", "tag_categories", "scripts", "chains",
    ]
    for field in required_top:
        if field not in pack:
            errors.append(f"Missing top-level field: {field}")

    if pack.get("mitre_tactic") != job["tactic_id"]:
        errors.append(f"mitre_tactic mismatch: got {pack.get('mitre_tactic')!r}, expected {job['tactic_id']!r}")
    if pack.get("platform") != job["platform"]:
        errors.append(f"platform mismatch: got {pack.get('platform')!r}, expected {job['platform']!r}")

    scripts = pack.get("scripts", [])
    if not isinstance(scripts, list) or len(scripts) == 0:
        errors.append("scripts must be a non-empty array")
    else:
        for i, s in enumerate(scripts):
            for sf in ["id", "name", "tcode", "executor", "command", "cleanup_command", "required_tags"]:
                if sf not in s:
                    errors.append(f"scripts[{i}] missing field: {sf}")
            # Check every #{tag} in command appears in required_tags
            cmd = s.get("command", "")
            import re
            placeholders = re.findall(r'#\{(\w+)\}', cmd)
            req_tags = s.get("required_tags", [])
            for ph in placeholders:
                if ph not in req_tags:
                    errors.append(f"scripts[{i}] ({s.get('id', '?')}): placeholder #{{{{ {ph} }}}} not in required_tags")

    chains = pack.get("chains", [])
    if not isinstance(chains, list) or len(chains) == 0:
        errors.append("chains must be a non-empty array")
    else:
        script_ids = {s.get("id") for s in scripts}
        for i, c in enumerate(chains):
            for cf in ["id", "name", "steps", "package_id"]:
                if cf not in c:
                    errors.append(f"chains[{i}] missing field: {cf}")
            for step in c.get("steps", []):
                if step.get("script_id") not in script_ids:
                    errors.append(f"chains[{i}] references unknown script_id: {step.get('script_id')!r}")

    tag_categories = pack.get("tag_categories", [])
    if not isinstance(tag_categories, list):
        errors.append("tag_categories must be an array")
    else:
        for i, tc in enumerate(tag_categories):
            for tcf in ["category_id", "label", "tags"]:
                if tcf not in tc:
                    errors.append(f"tag_categories[{i}] missing field: {tcf}")
            for j, t in enumerate(tc.get("tags", [])):
                for tf in ["key", "label", "default", "sensitive", "required"]:
                    if tf not in t:
                        errors.append(f"tag_categories[{i}].tags[{j}] missing field: {tf}")

    return errors


def load_log() -> dict:
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"runs": []}


def save_log(data: dict) -> None:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def process_job(job: dict, args) -> dict:
    """Process a single generation job. Returns a log entry dict."""
    output_rel = job["output_file"]
    output_path = EXCALIBUR_DIR / output_rel
    package_id = build_package_id(job)

    entry = {
        "job": output_rel,
        "package_id": package_id,
        "domain": job["domain"],
        "platform": job["platform"],
        "tactic_id": job["tactic_id"],
        "tactic_name": job["tactic_name"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "skipped",
        "script_count": 0,
        "chain_count": 0,
        "errors": [],
    }

    if output_path.exists() and not args.force:
        log.info("[SKIP] Already exists: %s", output_rel)
        entry["status"] = "skipped"
        return entry

    if args.dry_run:
        system_prompt = build_system_prompt(job["platform"], job["domain"])
        user_prompt = build_user_prompt(job)
        log.info("[DRY-RUN] Would generate: %s", output_rel)
        log.info("--- SYSTEM PROMPT (first 200 chars) ---\n%s...", system_prompt[:200])
        log.info("--- USER PROMPT ---\n%s", user_prompt)
        entry["status"] = "dry_run"
        return entry

    log.info("[START] Generating: %s  (%s / %s / %s)", output_rel, job["domain"], job["platform"], job["tactic_id"])
    system_prompt = build_system_prompt(job["platform"], job["domain"])
    user_prompt = build_user_prompt(job)

    raw_content = None
    for attempt in range(MAX_RETRIES):
        try:
            raw_content = call_azure_openai(system_prompt, user_prompt)
            break
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            if exc.code == 429:
                wait = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                log.warning("[RATE LIMIT] Attempt %d/%d — waiting %ds. %s", attempt + 1, MAX_RETRIES, wait, body_text[:200])
                time.sleep(wait)
            elif exc.code in (500, 502, 503, 504):
                wait = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                log.warning("[SERVER ERROR %d] Attempt %d/%d — waiting %ds", exc.code, attempt + 1, MAX_RETRIES, wait)
                time.sleep(wait)
            else:
                log.error("[HTTP ERROR %d] %s — %s", exc.code, output_rel, body_text[:400])
                entry["status"] = "failed"
                entry["errors"].append(f"HTTP {exc.code}: {body_text[:400]}")
                return entry
        except Exception as exc:
            wait = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            log.warning("[ERROR] Attempt %d/%d — %s — waiting %ds", attempt + 1, MAX_RETRIES, str(exc), wait)
            time.sleep(wait)
    else:
        log.error("[FAILED] Max retries exhausted: %s", output_rel)
        entry["status"] = "failed"
        entry["errors"].append("Max retries exhausted")
        return entry

    # Parse JSON
    try:
        pack = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        log.error("[PARSE ERROR] %s: %s", output_rel, exc)
        # Save raw for debugging
        raw_path = output_path.with_suffix(".raw.txt")
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(raw_content, encoding="utf-8")
        log.info("[DEBUG] Raw response saved: %s", raw_path)
        entry["status"] = "parse_error"
        entry["errors"].append(f"JSON parse error: {exc}")
        return entry

    # Ensure package_id is correct
    pack["package_id"] = package_id

    # Validate
    errors = validate_pack(pack, job)
    if errors:
        log.warning("[VALIDATION WARNINGS] %s — %d issues:", output_rel, len(errors))
        for e in errors:
            log.warning("  - %s", e)
        entry["errors"] = errors
        if any("Missing top-level" in e or "must be a non-empty" in e for e in errors):
            entry["status"] = "invalid"
            # Still save for inspection
            raw_path = output_path.with_suffix(".invalid.json")
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(pack, f, indent=2, ensure_ascii=False)
            log.info("[SAVED INVALID] %s", raw_path)
            return entry

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2, ensure_ascii=False)

    script_count = len(pack.get("scripts", []))
    chain_count = len(pack.get("chains", []))
    entry["status"] = "success"
    entry["script_count"] = script_count
    entry["chain_count"] = chain_count
    log.info("[SUCCESS] %s — %d scripts, %d chains", output_rel, script_count, chain_count)

    return entry


def update_catalog(generated_jobs: list) -> None:
    """Append new pack entries to catalog.json for successfully generated packs."""
    catalog_path = EXCALIBUR_DIR / "catalog.json"
    if not catalog_path.exists():
        log.warning("[CATALOG] catalog.json not found, skipping catalog update")
        return

    with open(catalog_path, encoding="utf-8") as f:
        catalog = json.load(f)

    existing_ids = {p["package_id"] for p in catalog.get("packs", [])}
    added = 0

    for entry in generated_jobs:
        if entry.get("status") != "success":
            continue
        pid = entry["package_id"]
        if pid in existing_ids:
            continue

        output_path = EXCALIBUR_DIR / entry["job"]
        if not output_path.exists():
            continue

        with open(output_path, encoding="utf-8") as f:
            pack = json.load(f)

        tcodes = [s.get("tcode", "") for s in pack.get("scripts", []) if s.get("tcode")]
        tcodes = sorted(set(tcodes))

        catalog_entry = {
            "package_id": pid,
            "package_name": pack.get("package_name", pid),
            "version": pack.get("version", "1.0.0"),
            "description": pack.get("description", ""),
            "mitre_tactic": f"{pack.get('mitre_tactic_name', '')} ({pack.get('mitre_tactic', '')})",
            "mitre_tcodes": tcodes,
            "script_count": entry["script_count"],
            "chain_count": entry["chain_count"],
            "platform": [entry["platform"]],
            "status": "stable",
            "url": (
                f"https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/"
                f"{entry['job']}"
            ),
        }
        catalog["packs"].append(catalog_entry)
        existing_ids.add(pid)
        added += 1

    if added > 0:
        catalog["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        log.info("[CATALOG] Added %d new entries to catalog.json", added)
    else:
        log.info("[CATALOG] No new entries to add")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Excalibur Packs via Azure OpenAI")
    parser.add_argument("--job", type=int, default=None, help="Run a single job by 0-based index")
    parser.add_argument("--dry-run", action="store_true", help="Show prompts without calling API")
    parser.add_argument("--force", action="store_true", help="Regenerate even if file exists")
    parser.add_argument("--domain", default=None, help="Filter by domain (enterprise-attack, ics-attack, mobile-attack)")
    parser.add_argument("--platform", default=None, help="Filter by platform (windows, linux, android, ios)")
    parser.add_argument("--tactic", default=None, help="Filter by tactic ID (e.g. TA0002)")
    parser.add_argument("--no-catalog", action="store_true", help="Skip catalog.json update")
    args = parser.parse_args()

    if not args.dry_run:
        if not AZURE_KEY:
            log.error("[ERROR] AZURE_OPENAI_KEY environment variable is not set.")
            log.error("  Run: $env:AZURE_OPENAI_KEY = 'your-key'")
            return 1
        if not AZURE_ENDPOINT:
            log.error("[ERROR] AZURE_OPENAI_ENDPOINT environment variable is not set.")
            log.error("  Run: $env:AZURE_OPENAI_ENDPOINT = 'https://x3m-ai.openai.azure.com/'")
            return 1

    if not JOBS_FILE.exists():
        log.error("[ERROR] Jobs file not found: %s", JOBS_FILE)
        return 1

    with open(JOBS_FILE, encoding="utf-8") as f:
        jobs = json.load(f)

    # Apply filters
    if args.job is not None:
        if args.job < 0 or args.job >= len(jobs):
            log.error("[ERROR] Job index %d out of range (0-%d)", args.job, len(jobs) - 1)
            return 1
        jobs = [jobs[args.job]]
    else:
        if args.domain:
            jobs = [j for j in jobs if j["domain"] == args.domain]
        if args.platform:
            jobs = [j for j in jobs if j["platform"] == args.platform]
        if args.tactic:
            jobs = [j for j in jobs if j["tactic_id"] == args.tactic]

    if not jobs:
        log.warning("[WARN] No jobs match the specified filters.")
        return 0

    log.info("[INFO] Total jobs to process: %d", len(jobs))

    gen_log = load_log()
    session_entries = []
    stats = {"success": 0, "skipped": 0, "failed": 0, "invalid": 0, "dry_run": 0, "parse_error": 0}

    for i, job in enumerate(jobs):
        log.info("\n[JOB %d/%d] %s", i + 1, len(jobs), job["output_file"])
        entry = process_job(job, args)
        session_entries.append(entry)
        stats[entry["status"]] = stats.get(entry["status"], 0) + 1

        # Save log after each job
        gen_log["runs"].append(entry)
        save_log(gen_log)

        # Small delay between calls to avoid rate limiting
        if not args.dry_run and entry["status"] in ("success", "invalid", "parse_error"):
            time.sleep(3)

    # Summary
    log.info("\n" + "=" * 60)
    log.info("[SUMMARY] Jobs: %d total", len(jobs))
    for k, v in stats.items():
        if v > 0:
            log.info("  %-15s %d", k + ":", v)

    # Update catalog
    if not args.dry_run and not args.no_catalog and stats.get("success", 0) > 0:
        update_catalog(session_entries)

    return 0 if stats.get("failed", 0) == 0 and stats.get("invalid", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
