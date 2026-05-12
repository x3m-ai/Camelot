# Morgana AI Test Review Engine – Integration Instructions for Claude Sonnet

## Context

You already know the Merlino and Morgana architecture, the current production codebase, and the purpose of the platform.

This document defines the development work required to integrate a new capability into the existing Morgana/Merlino ecosystem:

> **AI-assisted review of Morgana test results**, using local multi-agent analysis to enrich each executed test with technical interpretation, evidence validation, detection guidance, and script improvement recommendations.

However, do not design the AI implementation as a single-purpose Test Review feature only.

Design it as a reusable:

## Morgana AI Mission Engine

Version 1 must implement the first mission:

```text
mission_type = test_review
```

The architecture must also be ready for future missions, especially:

```text
mission_type = cyber_intelligence
```

The future Cyber Intelligence mission will allow Merlino to send TTPs, techniques, sectors or threat profiles to Morgana. Morgana will then use AI agents to collect, analyse, normalise and map OSINT/CTI information back to MITRE ATT&CK and return enriched intelligence to Merlino.

This is not a greenfield project. The implementation must be integrated into the existing production project with minimum disruption, clean modularity, and backward compatibility.

---

# 1. Feature Name

Use the broader architectural name:

## Morgana AI Mission Engine

The first implemented mission is:

## AI Test Review

The original working name for this first mission can remain:

## Morgana AI Test Review Engine

Alternative UI labels:

- AI Test Review
- Morgana Test Intelligence
- AI-Powered Test Evidence Review
- AI Test Result Enrichment

The preferred user-facing label is:

## AI Test Review

Short description:

> Morgana uses AI agents to review each executed test, validate what really happened, identify missing evidence, recommend detection checks, and suggest controlled improvements to the emulation script.

Broader product direction:

> Morgana should use AI agents through a reusable mission-based architecture. Test Review is the first mission. Cyber Intelligence is the next planned mission.

---

# 1.1 AI Mission Engine Concept

Do not hardcode the AI architecture only around test result enrichment.

Implement a reusable AI mission structure where different AI workflows can be added over time.

Initial mission types:

```text
test_review
cyber_intelligence
```

Version 1 must fully implement:

```text
test_review
```

Version 1 should prepare clean extension points for:

```text
cyber_intelligence
```

Suggested high-level structure:

```text
Morgana AI Mission Engine
│
├── Test Review Mission
│   ├── Execution Validator Agent
│   ├── Behaviour Validator Agent
│   ├── Detection Guidance Agent
│   ├── Script Improver Agent
│   ├── MITRE Validator Agent
│   └── Output Formatter Agent
│
└── Cyber Intelligence Mission
    ├── Collection Planner Agent
    ├── OSINT Query Builder Agent
    ├── Source Reliability Agent
    ├── IOC Extractor Agent
    ├── TTP Mapper Agent
    ├── Threat Actor / Campaign Correlator Agent
    └── CTI Output Formatter Agent
```

The Cyber Intelligence agents do not need to be fully implemented in version 1, but the architecture must not prevent them from being added later.

Core design principle:

```text
Mission = purpose-specific workflow
Agent = reusable AI capability
Provider = Ollama/local model runtime
Prompt = configurable per agent
Model = configurable per agent
Output = structured JSON validated by schema
```

---

# 2. Core Objective

At the moment, many test executions can only say something like:

```json
{
  "status": "success",
  "output": "command executed"
}
```

This is not enough.

A successful command execution does not automatically mean:

- the adversary behaviour was actually produced;
- the system state changed as expected;
- telemetry was generated;
- Sentinel, Defender, Wiz, EDR or SIEM detected it;
- the test is good enough to be used as formal evidence;
- the script is realistic, safe, reusable, or properly validated.

The goal is to enrich each Morgana test result with an AI-generated review that clearly explains:

1. what really happened;
2. whether the test execution was technically successful;
3. whether the expected adversary behaviour was validated;
4. whether detection was validated or remains inconclusive;
5. what evidence exists;
6. what evidence is missing;
7. where to check in the detection stack;
8. which KQL or hunting queries may help;
9. how the script could be improved;
10. whether the MITRE ATT&CK mapping looks correct;
11. what defensive or detection engineering actions should follow.

---

# 3. Fundamental Principle

This principle must be enforced everywhere in the implementation:

> **Execution success is not detection success.**

The engine must separate three different concepts:

| Layer | Meaning |
|---|---|
| Execution Result | Did the command/script run correctly? |
| Behaviour Validation | Did the test produce the expected adversary behaviour? |
| Detection Validation | Did Sentinel/Defender/Wiz/EDR/SIEM detect or log the behaviour? |

The AI must never claim that a detection happened unless real detection evidence is provided.

If no telemetry, alert, incident, log, or detection result is available, the output must say:

> Detection validation is inconclusive or not assessed.

Do not let the model hallucinate alerts, Sentinel incidents, Defender evidence, Wiz findings, or SOC outcomes.

---

# 4. Recommended Architecture

Implement this as a modular service inside the existing Morgana codebase.

Suggested logical structure:

```text
morgana_ai_review/
    agents/
        execution_validator.py
        behaviour_validator.py
        detection_guidance.py
        script_improver.py
        mitre_validator.py
        output_formatter.py

    prompts/
        execution_validator.md
        behaviour_validator.md
        detection_guidance.md
        script_improver.md
        mitre_validator.md
        output_formatter.md

    schemas/
        ai_test_review.schema.json
        enriched_test_result.schema.json

    clients/
        ollama_client.py

    orchestrator.py
    review_pipeline.py
    validators.py
    config.py
```

Adapt names and paths to the existing project conventions.

Do not break existing execution flows.

The first version should be introduced as a post-processing step after test execution.

---

# 5. Runtime Recommendation

Use a local LLM runtime as the primary implementation path.

Preferred runtime:

```text
Ollama
```

Preferred model family:

```text
Qwen
```

Initial default model for version 1:

```text
qwen3.5:4b
```

Use `qwen3.5:4b` as the first model for all agents unless the user changes the model in the Morgana AI settings page.

Initial model mapping for version 1:

| Agent | Suggested model |
|---|---|
| Execution Validator | qwen |
| Behaviour Validator | qwen |
| Detection Guidance | qwen |
| Script Improver | qwen-coder |
| MITRE Validator | qwen |
| JSON Formatter | small qwen or same default model |

The implementation should not hardcode the model name. It must be configurable.

Example config:

```json
{
  "ai_review": {
    "enabled": true,
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "default_model": "qwen3.5:4b",
    "coder_model": "qwen3.5:4b",
    "temperature": 0.1,
    "timeout_seconds": 120,
    "max_retries": 2,
    "strict_json": true
  }
}
```

Use the actual config pattern already present in Morgana/Merlino.

---

# 6. Runtime Direction

Use **Ollama** as the local AI runtime for this implementation.

The objective is to develop the Morgana AI Test Review Engine directly inside the existing Morgana/Merlino ecosystem. Do not introduce external coding-agent products or autonomous-agent platforms as part of the runtime design.

The core implementation should be:

```text
Morgana service code + Ollama + configurable models per agent + configurable prompts per agent + strict JSON schema + validation
```

Keep the implementation focused, production-oriented, modular, and easy to maintain.

---

# 7. Integration Point in Existing Flow

Add the AI review after a test or operation completes.

Expected flow:

```text
1. Morgana executes the test
2. Morgana collects raw execution result
3. Result is normalised into a standard object
4. AI Test Review Engine analyses the result
5. Engine returns enriched JSON
6. Morgana stores enriched result
7. Merlino can consume/display the enriched result
```

Pseudo-flow:

```python
raw_result = execute_morgana_test(test_definition)

normalised_result = normalise_test_result(
    test_definition=test_definition,
    raw_result=raw_result
)

if ai_review_enabled:
    ai_review = ai_review_pipeline.review(normalised_result)
else:
    ai_review = None

enriched_result = build_enriched_result(
    test_definition=test_definition,
    execution_result=normalised_result,
    ai_review=ai_review
)

save_result(enriched_result)
return enriched_result
```

---

# 8. Minimum Input Object

The AI review engine should receive a normalised input object.

Minimum required fields:

```json
{
  "test_id": "T1059_001_PS_001",
  "test_name": "Suspicious PowerShell Execution",
  "description": "Execute suspicious PowerShell command",
  "source": "Morgana",
  "platform": "windows",
  "executor": "powershell",
  "mitre_techniques": ["T1059.001"],
  "command": "powershell.exe -ExecutionPolicy Bypass ...",
  "start_time": "2026-05-10T22:10:00Z",
  "end_time": "2026-05-10T22:10:06Z",
  "exit_code": 0,
  "stdout": "...",
  "stderr": "...",
  "artifacts_created": [],
  "artifacts_removed": [],
  "validation_output": null,
  "cleanup_output": null,
  "detection_evidence": null
}
```

Do not assume all fields are always available. The engine must handle missing fields gracefully.

---

# 9. Detection Evidence Object

For version 1, detection evidence may be null.

Later, when Morgana integrates with Sentinel, Defender, Wiz or other platforms, detection evidence can be passed as structured data.

Suggested future object:

```json
{
  "detection_evidence": {
    "sentinel": {
      "incidents": [],
      "analytics_rule_matches": [],
      "kql_results": []
    },
    "defender": {
      "advanced_hunting_results": [],
      "alerts": []
    },
    "wiz": {
      "findings": []
    },
    "sysmon": {
      "events": []
    },
    "other": []
  }
}
```

Important logic:

- If `detection_evidence` is null or empty, detection status must be `Not Assessed` or `Inconclusive`.
- If telemetry exists but no alert exists, detection status may be `Telemetry Observed / No Alert Evidence`.
- If alert evidence exists, detection status may be `Detected`.
- If evidence is partial, use `Partially Detected`.

---

# 10. Required Output Object

The AI review engine must return strict JSON.

Minimum output:

```json
{
  "overall_result": "Partial Success",
  "confidence_score": 78,
  "execution_assessment": {
    "status": "Success",
    "comment": "The command completed with exit code 0."
  },
  "behaviour_assessment": {
    "status": "Partially Validated",
    "comment": "The script executed, but there is no post-condition evidence confirming the full adversary behaviour."
  },
  "detection_assessment": {
    "status": "Not Assessed",
    "comment": "No Sentinel, Defender, EDR, Wiz or SIEM telemetry was provided."
  },
  "evidence_observed": [
    "Exit code 0",
    "No stderr output"
  ],
  "evidence_missing": [
    "No process telemetry",
    "No Sentinel incident reference",
    "No post-execution validation"
  ],
  "detection_sources_to_check": [
    "Microsoft Defender DeviceProcessEvents",
    "Microsoft Sentinel SecurityEvent",
    "Windows PowerShell Operational Log",
    "Sysmon Event ID 1"
  ],
  "suggested_kql_queries": [
    {
      "name": "PowerShell process execution check",
      "query": "DeviceProcessEvents | where Timestamp > ago(24h) | where FileName =~ 'powershell.exe' | project Timestamp, DeviceName, InitiatingProcessAccountName, FileName, ProcessCommandLine"
    }
  ],
  "script_quality": {
    "rating": "Needs Improvement",
    "comments": [
      "The script returns plain text output and does not validate the expected behaviour."
    ],
    "recommended_improvements": [
      "Return structured JSON output.",
      "Add a post-execution validation step.",
      "Capture hostname, username, process ID and timestamp.",
      "Add cleanup logic."
    ]
  },
  "mitre_mapping_validation": {
    "declared_techniques": ["T1059.001"],
    "mapping_assessment": "Consistent",
    "confidence_score": 90,
    "additional_possible_techniques": [],
    "comment": "The test is consistent with PowerShell command execution."
  },
  "defensive_recommendations": [
    "Validate that PowerShell command-line logging is enabled.",
    "Confirm that Defender for Endpoint telemetry is ingested into Sentinel.",
    "Create or tune analytic rules for suspicious PowerShell usage."
  ],
  "final_comment": "The test executed successfully, but it cannot be used as complete detection evidence without telemetry validation."
}
```

---

# 11. Controlled Status Values

Use controlled values where possible.

## Execution status

Allowed values:

```text
Success
Failed
Partial Success
Inconclusive
Not Assessed
```

## Behaviour status

Allowed values:

```text
Validated
Partially Validated
Not Validated
Inconclusive
Not Assessed
```

## Detection status

Allowed values:

```text
Detected
Partially Detected
Telemetry Observed
No Alert Evidence
Not Detected
Inconclusive
Not Assessed
```

## Script quality rating

Allowed values:

```text
Good
Needs Improvement
Poor
Unsafe
Inconclusive
```

## MITRE mapping assessment

Allowed values:

```text
Consistent
Partially Consistent
Possibly Incorrect
Incorrect
Inconclusive
```

The schema validator should reject or normalise unexpected values.

---

# 12. Agent Design

Use a controlled multi-agent design, but keep implementation simple.

The agents do not need to be autonomous. They can be sequential prompt calls orchestrated by code.

## 12.1 Execution Validator Agent

Purpose:

> Determine whether the script/command executed successfully.

Inputs:

- command
- executor
- platform
- exit code
- stdout
- stderr
- timestamps
- raw result

Must answer:

- Did the command run?
- Did it return an error?
- Was the result successful, failed, partial, or inconclusive?
- What evidence supports this?

Output fragment:

```json
{
  "execution_assessment": {
    "status": "Success",
    "comment": "The command completed with exit code 0 and no stderr output."
  },
  "evidence_observed": [],
  "evidence_missing": []
}
```

Prompt file:

```text
prompts/execution_validator.md
```

---

## 12.2 Behaviour Validator Agent

Purpose:

> Determine whether the expected adversary behaviour was actually produced.

Inputs:

- test description
- MITRE techniques
- command
- stdout/stderr
- validation output
- artifacts created/removed
- expected behaviour if available

Must be conservative.

If no post-check exists, say behaviour is only partially validated or inconclusive.

Output fragment:

```json
{
  "behaviour_assessment": {
    "status": "Partially Validated",
    "comment": "Execution occurred, but the script does not confirm the expected system state change."
  }
}
```

Prompt file:

```text
prompts/behaviour_validator.md
```

---

## 12.3 Detection Guidance Agent

Purpose:

> Recommend what detection data sources, logs, alerts, or hunting queries should be checked.

This agent must not claim detection happened unless detection evidence is passed in.

Inputs:

- platform
- executor
- command
- MITRE techniques
- detection evidence if available
- security tools configured if available

Outputs:

- detection assessment
- data sources to check
- expected telemetry
- suggested KQL
- SOC validation steps

Output fragment:

```json
{
  "detection_assessment": {
    "status": "Not Assessed",
    "comment": "No detection telemetry was provided."
  },
  "detection_sources_to_check": [],
  "suggested_kql_queries": []
}
```

Prompt file:

```text
prompts/detection_guidance.md
```

---

## 12.4 Script Improver Agent

Purpose:

> Review the test script/command and suggest improvements.

Focus on:

- pre-checks;
- post-checks;
- structured JSON output;
- telemetry-friendly execution;
- cleanup;
- safety;
- idempotency;
- logging;
- timestamps;
- error handling;
- realistic adversary behaviour;
- avoiding brittle hardcoded values.

Do not automatically modify production scripts in version 1.

Output fragment:

```json
{
  "script_quality": {
    "rating": "Needs Improvement",
    "comments": [],
    "recommended_improvements": []
  }
}
```

Prompt file:

```text
prompts/script_improver.md
```

---

## 12.5 MITRE Validator Agent

Purpose:

> Validate whether the declared MITRE ATT&CK technique mapping matches the observed command and behaviour.

Inputs:

- declared techniques;
- test description;
- command;
- behaviour evidence;
- output.

Output fragment:

```json
{
  "mitre_mapping_validation": {
    "declared_techniques": ["T1059.001"],
    "mapping_assessment": "Consistent",
    "confidence_score": 90,
    "additional_possible_techniques": [],
    "comment": "The test is consistent with PowerShell command execution."
  }
}
```

Prompt file:

```text
prompts/mitre_validator.md
```

---

## 12.6 Output Formatter / Schema Checker Agent

Purpose:

> Merge all agent outputs into one strict JSON object and fix malformed model output if needed.

This can be implemented either as:

- a final LLM call;
- deterministic Python validation and repair;
- or both.

Use JSON schema validation after every model response.

Do not allow free-form final output.

Prompt file:

```text
prompts/output_formatter.md
```

---

# 13. Prompt Rules

Every prompt must include these rules:

```text
You are analysing Morgana adversary emulation test results.

Be evidence-based and conservative.

Do not invent telemetry, alerts, incidents, users, hostnames, detection results, file paths, or system changes.

If evidence is missing, explicitly say it is missing.

Separate execution success, behaviour validation, and detection validation.

Return only strict JSON. Do not include markdown. Do not include explanations outside JSON.
```

For detection prompts, add:

```text
Never claim that Sentinel, Defender, Wiz, EDR, SIEM, or SOC detected the test unless detection evidence is provided in the input.
```

---

# 14. Suggested Main Prompt

Use this as the initial base for the main reviewer/orchestrator prompt:

```text
You are an AI Purple Team Test Reviewer integrated into Morgana.

Your task is to analyse the result of an adversary emulation test executed by Morgana.

You must assess the result across three separate dimensions:

1. Execution Result:
Did the script or command run successfully?

2. Behaviour Validation:
Did the test produce the expected adversary behaviour?

3. Detection Validation:
Is there evidence that the security tools detected or logged the behaviour?

You must be conservative and evidence-based.

Do not assume a detection occurred unless detection telemetry, alert, incident, or hunting result evidence is provided.

If detection evidence is not provided, detection_assessment.status must be "Not Assessed" or "Inconclusive".

Return a strict JSON object using the required schema.
```

---

# 15. KQL Guidance

The system should generate KQL suggestions only when relevant.

The KQL does not need to be perfect in version 1, but it must be useful and safe.

Example for PowerShell:

```kql
DeviceProcessEvents
| where Timestamp > ago(24h)
| where FileName =~ "powershell.exe"
| project Timestamp, DeviceName, InitiatingProcessAccountName, FileName, ProcessCommandLine
```

Example for registry persistence:

```kql
DeviceRegistryEvents
| where Timestamp > ago(24h)
| where RegistryKey has_any (
    @"Software\Microsoft\Windows\CurrentVersion\Run",
    @"Software\Microsoft\Windows\CurrentVersion\RunOnce"
)
| project Timestamp, DeviceName, InitiatingProcessAccountName, RegistryKey, RegistryValueName, RegistryValueData
```

Example for Windows Security Events:

```kql
SecurityEvent
| where TimeGenerated > ago(24h)
| where EventID in (4688, 4689)
| project TimeGenerated, Computer, Account, EventID, NewProcessName, CommandLine
```

If the test does not map cleanly to a known telemetry table, the model should say that the query is indicative and should be adapted to the environment.

---

# 16. Script Improvement Requirements

The AI should regularly recommend that Morgana tests move towards this structure:

```text
pre_check
execute
validate
collect_evidence
cleanup
return_json
```

Every mature Morgana script should ideally:

- validate prerequisites;
- execute the behaviour;
- confirm whether the expected condition occurred;
- collect basic evidence;
- clean up where safe;
- return structured JSON;
- include timestamps;
- include host/user context;
- include exit codes;
- include clear error messages.

Example PowerShell output structure:

```powershell
$result = @{
    test_id = "T1059_001_PS_001"
    technique = "T1059.001"
    action = "PowerShell suspicious execution"
    status = "completed"
    evidence = @{
        process = "powershell.exe"
        command_line = $MyInvocation.Line
        user = $env:USERNAME
        hostname = $env:COMPUTERNAME
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
    }
    validation = @{
        expected_behavior = "PowerShell process executed with suspicious arguments"
        behavior_confirmed = $true
    }
}

$result | ConvertTo-Json -Depth 5
```

The AI may suggest improved code snippets, but production script changes must not be applied automatically in version 1.

---

# 17. Storage

Store the enriched review with the existing test result.

Suggested structure:

```json
{
  "test": {},
  "execution": {},
  "ai_review": {},
  "metadata": {
    "ai_review_version": "1.0",
    "provider": "ollama",
    "model": "qwen3.5:4b",
    "review_timestamp": "2026-05-10T22:15:00Z"
  }
}
```

Add fields to the existing result model only where necessary.

Do not break old result consumers.

If existing result files are JSON, add `ai_review` as an optional property.

If existing result storage is database-backed, introduce nullable fields or a separate review table depending on the existing architecture.

---

# 18. Merlino UI / Excel Consumption

Merlino should eventually consume these fields:

| AI Review Field | Merlino Usage |
|---|---|
| overall_result | Test result summary |
| confidence_score | Score / confidence indicator |
| execution_assessment | Technical execution comment |
| behaviour_assessment | Behaviour validation comment |
| detection_assessment | Detection validation comment |
| evidence_observed | Evidence section |
| evidence_missing | Gap section |
| detection_sources_to_check | Detection engineering checklist |
| suggested_kql_queries | Hunting/query suggestions |
| script_quality | Morgana script improvement section |
| mitre_mapping_validation | ATT&CK validation |
| defensive_recommendations | Remediation recommendations |
| final_comment | Human-readable final note |

In the first version, it is acceptable to expose only:

- overall result;
- confidence score;
- final comment;
- detection assessment;
- evidence missing;
- script improvements;
- suggested KQL.

---

# 19. Error Handling

The AI review must never block normal Morgana execution.

If AI review fails:

```json
{
  "ai_review": {
    "status": "failed",
    "error": "AI review failed or timed out",
    "fallback_comment": "The test executed, but AI enrichment was not available."
  }
}
```

Required handling:

- Ollama unavailable;
- model not installed;
- timeout;
- malformed JSON;
- schema validation failure;
- prompt failure;
- empty response;
- partial response;
- model hallucinated invalid status;
- detection evidence missing.

Retry rules:

- retry malformed JSON once or twice;
- use a repair prompt if needed;
- if still invalid, return safe fallback object.

---

# 20. JSON Validation

Implement schema validation.

No final AI review should be stored unless it passes validation or is converted to a safe fallback.

Validation should check:

- required fields exist;
- controlled statuses are valid;
- confidence score is numeric and between 0 and 100;
- arrays are arrays;
- KQL query objects have name/query;
- no top-level free text;
- no markdown wrapper.

Pseudo-code:

```python
review = call_model(prompt, input_data)

parsed = parse_json(review)

if not parsed:
    repaired = repair_json_with_model(review)
    parsed = parse_json(repaired)

validated = validate_against_schema(parsed)

if not validated:
    return build_safe_ai_review_failure()

return parsed
```

---

# 21. Security and Safety

The AI engine must not automatically execute generated code.

The AI can recommend script improvements, but it must not update production abilities/tests without explicit human approval.

Add clear separation:

```text
suggested_script_improvement != applied_script_change
```

Any future auto-improvement workflow must include:

1. AI suggestion;
2. diff generation;
3. human review;
4. approval;
5. versioned update;
6. rollback option.

For version 1, only generate recommendations.

---

# 22. Configuration Flags

Add config options similar to the structure below. The important point is that global defaults exist, but each agent can override the model, prompt and runtime settings.

```json
{
  "ai_review": {
    "enabled": true,
    "mode": "local",
    "provider": "ollama",
    "ollama_base_url": "http://localhost:11434",
    "global_defaults": {
      "model": "qwen3.5:4b",
      "temperature": 0.1,
      "timeout_seconds": 120,
      "max_retries": 2
    },
    "strict_json": true,
    "store_prompt_input": false,
    "store_raw_model_output": true,
    "allow_script_suggestions": true,
    "allow_auto_script_update": false,
    "agents": {
      "execution_validator": {
        "enabled": true,
        "model": "qwen3.5:4b",
        "prompt": "custom or default prompt"
      },
      "script_improver": {
        "enabled": true,
        "model": "qwen3.5:4b",
        "prompt": "custom or default prompt"
      }
    }
  }
}
```

Important:

```json
"allow_auto_script_update": false
```

must remain false for version 1.

---

# 23. Logging

Add useful debug logs without leaking sensitive data unnecessarily.

Recommended logs:

```text
AI review started for test_id
AI review provider/model selected
AI review completed
AI review failed with reason
Schema validation failed
JSON repair attempted
Fallback review generated
```

Avoid logging full command output by default unless debug mode is enabled.

---

# 24. Version 1 Scope

Implement version 1 with this scope:

## Must Have

- Post-test AI review pipeline.
- Ollama client.
- Dedicated Morgana AI page in the left menu above Admin.
- Reusable AI Mission Engine structure.
- `test_review` mission implemented in version 1.
- `cyber_intelligence` mission extension point prepared for future use.
- Configurable model per agent.
- Configurable prompt per agent.
- Normalised test result input.
- Strict JSON output.
- Execution assessment.
- Behaviour assessment.
- Detection assessment.
- Evidence observed/missing.
- Detection sources to check.
- Basic KQL suggestions.
- Script improvement recommendations.
- MITRE mapping validation.
- Safe fallback on failure.
- Optional `ai_review` field stored with test result.

## Should Have

- JSON repair retry.
- Prompt files externalised as markdown.
- Unit tests for schema validation.
- Example test fixtures.
- UI/consumer-ready output structure.

## Not In Version 1

- Automatic script modification.
- Direct Sentinel querying.
- Direct Defender querying.
- Direct Wiz querying.
- Persistent self-learning agents.

---

# 24A. Future Mission: Cyber Intelligence

Version 1 should not fully implement Cyber Intelligence collection, but the AI architecture must be ready for it.

This is a planned mission:

```text
mission_type = cyber_intelligence
```

Expected future workflow:

```text
1. Merlino sends TTPs, techniques, sector, region or threat profile to Morgana
2. Morgana starts a Cyber Intelligence mission
3. Morgana AI agents build a collection plan
4. Morgana collects or prepares OSINT/CTI queries from approved sources
5. AI agents normalise and analyse the collected information
6. AI agents map intelligence back to MITRE ATT&CK
7. Morgana returns a structured CTI enrichment package to Merlino
8. Merlino displays the CTI context, TTP mapping, recommended tests and report content
```

## Cyber Intelligence Mission Inputs

Suggested input object:

```json
{
  "mission_type": "cyber_intelligence",
  "input_type": "mitre_techniques",
  "techniques": ["T1566.002", "T1059.001", "T1105"],
  "sector": "energy",
  "region": "UK/EU",
  "objective": "Find relevant public threat intelligence and map it to the selected TTPs"
}
```

## Future Cyber Intelligence Agents

Prepare extension points for agents such as:

| Agent | Purpose |
|---|---|
| Collection Planner Agent | Defines what intelligence should be collected |
| OSINT Query Builder Agent | Builds safe OSINT and Google dork style queries |
| Source Reliability Agent | Scores source reliability and relevance |
| Telegram Source Agent | Reads approved public Telegram intelligence sources only |
| IOC Extractor Agent | Extracts hashes, domains, IPs, URLs and emails from collected data |
| TTP Mapper Agent | Maps collected intelligence to MITRE ATT&CK |
| Threat Actor / Campaign Correlator Agent | Correlates actors, campaigns, tools and malware |
| CTI Output Formatter Agent | Produces structured JSON for Merlino |

## Safe OSINT / Google Dork Use

The system may later support Google dork style query generation, but only for safe OSINT and CTI purposes.

Allowed intent:

```text
Find public reports, advisories, write-ups, indicators, campaign descriptions, malware references and MITRE mappings.
```

Do not design this as an offensive data exposure search feature.

The query builder should produce safe and explainable queries, for example:

```text
site:cisa.gov "T1059.001" "PowerShell"
site:mandiant.com "T1105" "campaign"
site:unit42.paloaltonetworks.com "T1566.002"
"MITRE ATT&CK" "T1071.001" "ransomware"
```

Each generated query should include:

```json
{
  "query": "site:cisa.gov \"T1059.001\" \"PowerShell\"",
  "purpose": "Find authoritative advisory references for PowerShell execution",
  "risk": "safe"
}
```

## Telegram Guardrails

If Telegram support is added later, it must be passive, read-only and controlled.

Requirements:

```text
- approved public channels only;
- configured manually by the user;
- no interaction with threat actors;
- no buying or selling;
- no requests for illegal material;
- no automated engagement;
- no downloads unless explicitly reviewed and allowed by policy;
- source logging must be clear;
- collection must remain defensive CTI oriented.
```

Suggested config:

```json
{
  "telegram_intelligence": {
    "enabled": false,
    "mode": "read_only",
    "approved_channels_only": true,
    "allow_interaction": false,
    "allow_downloads": false,
    "source_list": []
  }
}
```

## Cyber Intelligence Output Contract

Future output should be structured so Merlino can consume it without free-text parsing.

Example:

```json
{
  "cti_mission_id": "cti-2026-001",
  "input_techniques": ["T1566.002", "T1059.001", "T1105"],
  "summary": "Public reporting links these behaviours to phishing-led intrusion chains followed by PowerShell execution and tool transfer.",
  "confidence_score": 78,
  "related_threat_actors": [],
  "related_campaigns": [],
  "related_malware_tools": [],
  "related_cves": [],
  "mapped_ttps": [
    {
      "technique_id": "T1059.001",
      "relevance": "High",
      "reason": "Multiple sources describe PowerShell execution in the intrusion chain."
    }
  ],
  "iocs": {
    "domains": [],
    "ips": [],
    "hashes": [],
    "urls": [],
    "emails": []
  },
  "recommended_morgana_tests": [
    {
      "technique_id": "T1059.001",
      "test_type": "PowerShell execution validation",
      "priority": "High"
    }
  ],
  "recommended_detections": [],
  "sources": [
    {
      "source_name": "Example Source",
      "url": "source reference",
      "reliability": "High",
      "date": "YYYY-MM-DD",
      "notes": "Relevant public reporting"
    }
  ]
}
```

## Product Relationship

The future Cyber Intelligence mission must follow the same product relationship:

```text
Morgana = AI execution, collection support, enrichment and mapping
Merlino = analysis, correlation, visibility and reporting
```

Merlino should be able to use Cyber Intelligence output to enrich:

- technique views;
- coverage analysis;
- recommended Morgana tests;
- detection engineering recommendations;
- Operational Report sections;
- CTI context for selected TTPs.

---

# 25. Version 2 Scope

After version 1 works, add real detection validation.

Potential integrations:

- Microsoft Sentinel Log Analytics query API;
- Defender XDR Advanced Hunting API;
- Wiz findings API;
- local Sysmon/Windows Event collection;
- Splunk/Elastic optional integrations.

At that stage, detection assessment can become evidence-based:

```text
Detected
Partially Detected
Telemetry Observed
No Alert Evidence
Not Detected
Inconclusive
```

Do not implement this in version 1 unless the existing codebase already has those connectors available.

---

# 26. Version 3 Scope

Controlled AI-assisted script improvement.

Flow:

```text
AI suggests improvement
Generate candidate diff
Human reviews
Human approves
Morgana stores new candidate version
Rollback available
```

Never silently overwrite existing scripts.

---

# 27. Example End-to-End Output

Example enriched result:

```json
{
  "test_id": "T1059_001_PS_001",
  "test_name": "Suspicious PowerShell Execution",
  "mitre_techniques": ["T1059.001"],
  "execution": {
    "status": "completed",
    "exit_code": 0,
    "stdout": "Command executed",
    "stderr": ""
  },
  "ai_review": {
    "overall_result": "Partial Success",
    "confidence_score": 76,
    "execution_assessment": {
      "status": "Success",
      "comment": "The command executed successfully with exit code 0 and no stderr output."
    },
    "behaviour_assessment": {
      "status": "Partially Validated",
      "comment": "PowerShell execution occurred, but there is no post-execution validation confirming the intended adversary behaviour beyond process execution."
    },
    "detection_assessment": {
      "status": "Not Assessed",
      "comment": "No Sentinel, Defender, EDR, Wiz, SIEM or SOC telemetry was provided, so detection cannot be confirmed or denied."
    },
    "evidence_observed": [
      "Exit code 0",
      "No stderr output",
      "PowerShell command was launched"
    ],
    "evidence_missing": [
      "No Defender DeviceProcessEvents evidence",
      "No Sentinel incident or analytic rule match",
      "No Sysmon Event ID 1 evidence",
      "No post-execution validation output"
    ],
    "detection_sources_to_check": [
      "Microsoft Defender DeviceProcessEvents",
      "Microsoft Sentinel SecurityEvent",
      "Windows PowerShell Operational Log",
      "Sysmon Event ID 1"
    ],
    "suggested_kql_queries": [
      {
        "name": "PowerShell process execution",
        "query": "DeviceProcessEvents | where Timestamp > ago(24h) | where FileName =~ 'powershell.exe' | project Timestamp, DeviceName, InitiatingProcessAccountName, FileName, ProcessCommandLine"
      }
    ],
    "script_quality": {
      "rating": "Needs Improvement",
      "comments": [
        "The script is useful for execution testing, but it does not provide enough evidence to validate the behaviour or detection outcome."
      ],
      "recommended_improvements": [
        "Add structured JSON output.",
        "Add post-execution validation.",
        "Capture hostname, username, timestamp and process information.",
        "Add cleanup logic where appropriate."
      ]
    },
    "mitre_mapping_validation": {
      "declared_techniques": ["T1059.001"],
      "mapping_assessment": "Consistent",
      "confidence_score": 90,
      "additional_possible_techniques": [],
      "comment": "The command is consistent with PowerShell command execution under T1059.001."
    },
    "defensive_recommendations": [
      "Validate PowerShell command-line logging.",
      "Confirm Defender for Endpoint telemetry ingestion into Sentinel.",
      "Tune analytic rules for suspicious PowerShell execution patterns."
    ],
    "final_comment": "The test executed successfully, but it cannot be considered complete detection evidence until telemetry or alert data is correlated."
  }
}
```

---

# 28. Acceptance Criteria

The implementation is acceptable when:

1. Existing Morgana test execution still works without AI enabled.
2. AI review can be enabled or disabled by configuration.
3. A completed test can be enriched with an `ai_review` object.
4. The review separates execution, behaviour, and detection.
5. The model does not claim detection when no detection evidence exists.
6. Output is strict JSON and schema validated.
7. AI failure does not break the test execution.
8. Results are stored in a way that Merlino can consume later.
9. Script improvement is recommendation-only.
10. The implementation is modular and easy to extend with real Sentinel/Defender/Wiz telemetry later.

---

# 29. Development Approach

Please implement incrementally.

Recommended order:

1. Add config section for AI review.
2. Add Ollama client.
3. Add normalised input model.
4. Add schema for AI review output.
5. Add prompt files.
6. Implement single-pass AI reviewer first.
7. Add schema validation.
8. Add JSON repair/fallback.
9. Split into multiple agents if needed.
10. Add result storage.
11. Add tests/fixtures.
12. Prepare Merlino consumption fields.

Do not over-engineer the first implementation.

The most important thing is to create a reliable, controlled, evidence-based enrichment pipeline.

---

# 30. Final Product Message

The feature should support this product-level statement:

> Morgana does not simply execute adversary emulation tests. It reviews the outcome, explains what really happened, identifies missing evidence, guides detection validation, and recommends improvements to both the test script and the defensive detection logic.

This is the core value of the AI Test Review Engine.
