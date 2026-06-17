"""
generate_execution_pack.py
Generates missing sub-technique scripts for the Excalibur Execution (TA0002) pack
using the Azure OpenAI deployment configured in Morgana ai_provider.json.

Usage:
    python generate_execution_pack.py

Output:
    Overwrites excalibur-execution-emulation-pack.json with expanded scripts + chains.
"""

import base64, json, os, sys, ssl, time
import urllib.request, urllib.error
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────

MORGANA_DIR  = Path(r"C:\Users\ninoc\OfficeAddinApps\Morgana")
CAMELOT_DIR  = Path(r"C:\Users\ninoc\OfficeAddinApps\Camelot")
PACK_PATH    = CAMELOT_DIR / "morgana/excalibur/enterprise/windows/excalibur-execution-emulation-pack.json"
AI_PROV_PATH = MORGANA_DIR / "ai_provider.json"
MASTER_KEY_PATH = Path(r"C:\ProgramData\Morgana\data\master.key")
AUTHORING_GUIDE = (MORGANA_DIR / ".github/EXCALIBUR_AUTHORING.md").read_text(encoding="utf-8")

# ── Key decryption ────────────────────────────────────────────────────────────

def _xor_deobfuscate(token: str, key: str) -> str:
    if not token:
        return ""
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
    except Exception:
        return ""
    kb = key.encode("utf-8") or b"morgana"
    out = bytearray()
    for i, ch in enumerate(raw):
        out.append(ch ^ kb[i % len(kb)])
    try:
        return out.decode("utf-8")
    except Exception:
        return ""

mkey = MASTER_KEY_PATH.read_text(encoding="utf-8").strip() or "morgana"
ai_prov = json.loads(AI_PROV_PATH.read_text(encoding="utf-8"))
az = ai_prov["providers"]["azure-openai"]
AZURE_ENDPOINT   = az["endpoint_url"].rstrip("/")
AZURE_DEPLOYMENT = az["deployment_name"] or az["model"] or "gpt-4.1"
AZURE_API_VERSION = az.get("api_version") or "2025-01-01-preview"
AZURE_API_KEY    = _xor_deobfuscate(az["api_key_obf"], mkey)

if not AZURE_API_KEY:
    print("[ERROR] Could not decrypt Azure API key from ai_provider.json")
    sys.exit(1)

CHAT_URL = f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions?api-version={AZURE_API_VERSION}"
print(f"[INFO] Using Azure OpenAI: {AZURE_ENDPOINT}  deployment={AZURE_DEPLOYMENT}")

# ── Load existing pack ────────────────────────────────────────────────────────

pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
existing_tcodes = {s["tcode"] for s in pack["scripts"]}
print(f"[INFO] Existing scripts: {len(pack['scripts'])} TCodes: {sorted(existing_tcodes)}")

# ── Sub-techniques to generate ───────────────────────────────────────────────
# Full TA0002 Execution sub-technique coverage for Windows — only what is missing

ALL_SUBTECHNIQUES = [
    # T1047 - already covered (parent)
    # T1053 sub-techniques
    ("T1053.002", "Execution",  "At",                             "Windows"),
    ("T1053.005", "Execution",  "Scheduled Task",                 "Windows"),
    # T1059 sub-techniques
    ("T1059.001", "Execution",  "PowerShell",                     "Windows"),
    ("T1059.003", "Execution",  "Windows Command Shell",          "Windows"),  # exists, skip
    ("T1059.005", "Execution",  "Visual Basic",                   "Windows"),  # exists, skip
    ("T1059.006", "Execution",  "Python",                         "Windows"),  # exists, skip
    ("T1059.007", "Execution",  "JavaScript",                     "Windows"),  # exists, skip
    ("T1059.009", "Execution",  "Cloud API",                      "Windows"),  # exists, skip
    # Missing T1059 subs
    ("T1059.008", "Execution",  "Network Device CLI",             "Windows"),
    # T1106 sub - none
    # T1129 sub - none
    # T1204 sub-techniques
    ("T1204.001", "Execution",  "Malicious Link",                 "Windows"),
    ("T1204.002", "Execution",  "Malicious File",                 "Windows"),
    ("T1204.003", "Execution",  "Malicious Image",                "Windows"),
    # T1559 sub-techniques
    ("T1559.001", "Execution",  "Component Object Model",         "Windows"),
    ("T1559.002", "Execution",  "Dynamic Data Exchange",          "Windows"),
    ("T1559.003", "Execution",  "XPC Services",                   "Windows"),
    # T1569 sub-techniques
    ("T1569.001", "Execution",  "Launchctl",                      "Windows"),
    ("T1569.002", "Execution",  "Service Execution",              "Windows"),
    # T1047 sub - none
]

# Filter out already-covered tcodes
TO_GENERATE = [(tc, tac, name, plat) for tc, tac, name, plat in ALL_SUBTECHNIQUES
               if tc not in existing_tcodes]

print(f"[INFO] Sub-techniques to generate: {len(TO_GENERATE)}")
for tc, _, name, _ in TO_GENERATE:
    print(f"  {tc} - {name}")

if not TO_GENERATE:
    print("[OK] All sub-techniques already covered. Nothing to generate.")
    sys.exit(0)

# ── System prompt ─────────────────────────────────────────────────────────────

PLACEHOLDER_TAG  = "#{excalibur_tag_key}"
PLACEHOLDER_TCODE = "#{tcode_value}"

SYSTEM_PROMPT = f"""You are an expert Red Team engineer specialising in adversary emulation for Purple Teaming exercises.
You create high-quality Excalibur pack scripts for the Morgana Red Team Platform.

Your output is ALWAYS a valid JSON object with this exact schema. Nothing else — no markdown, no explanation.

AUTHORING GUIDE (MANDATORY — follow every rule):
{AUTHORING_GUIDE}

CRITICAL QUALITY REQUIREMENTS:
1. Scripts must be SERIOUS adversary emulation — realistic TTPs that generate real telemetry in Microsoft Defender for Endpoint and Microsoft Sentinel. NOT toy examples.
2. Each script MUST start with: Write-Host '[START] <TCODE> - <technique_name>'
3. Each script MUST end with: Write-Host '[SUCCESS] <TCODE> complete'
4. Use realistic payloads — actual API calls, real registry keys, real file paths, real network probes.
5. All scripts must be SAFE for lab execution: no lateral movement to production, no data destruction, no exfiltration of real data. Use TEST-NET IPs (198.51.100.x) or temp paths only.
6. Include a proper cleanup_command wherever the script creates files, registry keys, scheduled tasks, services, or any persistent artifact. Use Write-Host '[INFO] <TCODE> cleanup: none' ONLY if truly nothing to clean.
7. Tags: use {PLACEHOLDER_TAG} placeholders for any value that should be configurable at execution time (target IPs, filenames, task names, service names). Always declare them in required_tags.
8. Tag key naming: excalibur_exec_<short_description> (e.g. excalibur_exec_target_host, excalibur_exec_payload_file)
9. detection_rule: write a specific, actionable detection rule name/description for a Sentinel/MDE analyst. Not generic.
10. sentinel_connector: use the most appropriate connector ("Microsoft Defender for Endpoint", "Microsoft Sentinel", "Windows Security Events via AMA", etc.)
11. JSON escaping: NEVER use unescaped double-quotes inside command strings. Use single quotes in PowerShell wherever possible. When double-quotes are required inside JSON strings, escape them as \\". When Windows paths contain backslash, escape as \\\\.

OUTPUT FORMAT — return ONLY this JSON object, nothing else:
{{
  "scripts": [
    {{
      "id": "Excalibur - Execution-<TCODE>-<TechniqueName>",
      "name": "Excalibur - Execution-<TCODE>-<TechniqueName>",
      "description": "One to two sentences. What the script does, what telemetry it generates, why it matters for Purple Teaming.",
      "tactic": "Execution",
      "tcode": "<TCODE>",
      "technique_name": "<TechniqueName>",
      "executor": "powershell",
      "platform": "windows",
      "required_tags": ["<tag_key_if_needed>"],
      "command": "<full PowerShell command — single line — properly JSON-escaped>",
      "cleanup_command": "<cleanup PowerShell — or Write-Host '[INFO] <TCODE> cleanup: none'>",
      "detection_rule": "<specific detection rule description>",
      "sentinel_connector": "<connector name>",
      "package": "excalibur"
    }}
  ],
  "chains": [
    {{
      "name": "Excalibur - Execution-<TCODE>-<TechniqueName>",
      "description": "One sentence.",
      "package": "excalibur",
      "tcode": "<TCODE>",
      "tactic": "Execution",
      "script_refs": ["Excalibur - Execution-<TCODE>-<TechniqueName>"]
    }}
  ],
  "new_tag_categories": [
    {{
      "category_id": "exec_<tcode_slug>",
      "label": "<Human label>",
      "description": "<What these tags are for>",
      "scope": "local",
      "used_by_tcodes": ["<TCODE>"],
      "tags": [
        {{
          "key": "excalibur_exec_<name>",
          "label": "<Human label>",
          "description": "<What to put here>",
          "default": "<safe default>",
          "example": "<realistic example>",
          "sensitive": false,
          "required": false
        }}
      ]
    }}
  ]
}}

If a script needs NO configurable tags, set "required_tags": [] and "new_tag_categories": [].
"""

# ── LLM call ──────────────────────────────────────────────────────────────────

def call_azure(tcode: str, technique_name: str) -> dict:
    user_msg = (
        f"Generate a complete, realistic Excalibur script for:\n"
        f"  TCode: {tcode}\n"
        f"  Technique: {technique_name}\n"
        f"  Tactic: Execution (TA0002)\n"
        f"  Platform: Windows\n\n"
        f"Return ONLY the JSON object described in the system prompt. No markdown fences, no explanation."
    )
    payload = json.dumps({
        "model": AZURE_DEPLOYMENT,
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": user_msg},
        ],
        "temperature": 0.2,
        "max_tokens": 3000,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    ctx = ssl.create_default_context()
    try:
        ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
    except Exception:
        pass

    req = urllib.request.Request(
        CHAT_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "api-key": AZURE_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  [HTTP ERROR {e.code}] {body[:300]}")
        return {}
    except Exception as e:
        print(f"  [ERROR] {e}")
        return {}

# ── Generate and merge ────────────────────────────────────────────────────────

new_scripts        = []
new_chains         = []
new_tag_categories = []
failed             = []

for i, (tcode, tactic, technique_name, platform) in enumerate(TO_GENERATE):
    print(f"\n[{i+1}/{len(TO_GENERATE)}] Generating {tcode} - {technique_name} ...", flush=True)
    result = call_azure(tcode, technique_name)

    if not result:
        print(f"  [SKIP] Empty response for {tcode}")
        failed.append(tcode)
        continue

    scripts  = result.get("scripts", [])
    chains   = result.get("chains", [])
    tag_cats = result.get("new_tag_categories", [])

    # Validate JSON of each script command
    valid = True
    for s in scripts:
        try:
            # Re-encode as JSON to test escaping
            json.loads(json.dumps(s))
        except Exception as e:
            print(f"  [WARN] Script JSON invalid: {e}")
            valid = False

    if not scripts:
        print(f"  [SKIP] No scripts in response for {tcode}")
        failed.append(tcode)
        continue

    new_scripts.extend(scripts)
    new_chains.extend(chains)
    new_tag_categories.extend(tag_cats)
    print(f"  [OK] +{len(scripts)} script(s), +{len(chains)} chain(s), +{len(tag_cats)} tag_category/ies")

    # Polite rate-limit: 0.5s between calls
    if i < len(TO_GENERATE) - 1:
        time.sleep(0.5)

# ── Merge into pack ───────────────────────────────────────────────────────────

if new_scripts:
    # Deduplicate by tcode (keep new over old if same tcode)
    existing_by_tcode = {s["tcode"]: s for s in pack["scripts"]}
    for s in new_scripts:
        existing_by_tcode[s["tcode"]] = s
    pack["scripts"] = list(existing_by_tcode.values())

    existing_chains_by_tcode = {c["tcode"]: c for c in pack["chains"]}
    for c in new_chains:
        existing_chains_by_tcode[c["tcode"]] = c
    pack["chains"] = list(existing_chains_by_tcode.values())

    # Merge tag categories (by category_id)
    existing_cats = {tc["category_id"]: tc for tc in pack.get("tag_categories", [])}
    for tc in new_tag_categories:
        existing_cats[tc["category_id"]] = tc
    pack["tag_categories"] = list(existing_cats.values())

    # Final validation
    pack_json = json.dumps(pack, indent=2, ensure_ascii=False)
    json.loads(pack_json)  # raises if invalid

    PACK_PATH.write_text(pack_json, encoding="utf-8")
    print(f"\n[OK] Pack saved: {len(pack['scripts'])} scripts, {len(pack['chains'])} chains")
    print(f"     File: {PACK_PATH}")
else:
    print("\n[WARN] No new scripts generated — pack not updated.")

if failed:
    print(f"\n[WARN] Failed TCodes ({len(failed)}): {failed}")
    print("       Re-run the script to retry them.")

print("\n[DONE]")
