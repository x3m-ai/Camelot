# ANSSI FuzzySully — Deep OPC UA Fuzzing

**Provider:** ANSSI FuzzySully  
**Source:** [ANSSI-FR/fuzzysully](https://github.com/ANSSI-FR/fuzzysully)  
**Commit:** `50a0631178331d2cc39b6ed554b9b68050580f92`  
**Version:** 0.1.1  
**License:** LGPL-2.1  
**Category:** OT / ICS Fuzzing / OPC UA  
**Scripts:** 73  
**Packages:** 4  

---

## What this is

FuzzySully is a deep OPC UA protocol fuzzing engine built by ANSSI-FR (Quarkslab) on top of Fuzzowski
and an enhanced opcua-asyncio stack. It supports fuzzing of OPC UA servers, Global Discovery Servers
(GDS), and reverse-client connections.

This Morgana integration exposes every upstream fuzzing function as a real Morgana Script profile,
uses a non-interactive runner wrapper, supports bounded execution, and returns structured results
through the normal Morgana Agent / Test / Detection Fabric pipeline.

---

## Packages

| Package | Scripts | Mode | Policy |
|---|---|---|---|
| `fuzzysully-server-none-v1` | 20 | server | None |
| `fuzzysully-server-basic256sha256-v1` | 34 | server | Basic256Sha256 (Sign + SignEncrypt) |
| `fuzzysully-gds-v1` | 18 | gds | Basic256Sha256 (Sign + SignEncrypt) |
| `fuzzysully-reverse-v1` | 1 | reverse | None |

---

## Available modes and functions

### SERVER / None (20 scripts)
All 20 upstream server functions in no-security mode.

### SERVER / Basic256Sha256 (34 scripts — 17 Sign + 17 SignEncrypt)
Excludes `hello`, `secure_channel`, `session` per upstream restrictions.

### GDS (18 scripts — 9 Sign + 9 SignEncrypt)
- `get_trust_list`, `get_certificate_groups`, `get_certificate_status`, `revoke_certificate`
- `start_signing_request`, `start_new_key_pair_request`, `finish_request`
- `finish_request_start_signing_request`, `finish_request_start_new_key_pair_request`

### REVERSE (1 script)
- `reverse_hello`

---

## Runtime scale

Each Script is a fuzz profile. FuzzySully generates test cases dynamically at runtime.
Typical campaign sizes: 11,000 – 66,000+ cases per function. Operator controls case count and duration.

---

## Runtime requirements

- Linux Morgana Agent with **Python 3.10+**
- FuzzySully package installed: `pip install fuzzysully==0.1.1`
- For Basic256Sha256: client certificate and private key in PEM format on the agent
- For GDS: running Global Discovery Server accessible from the agent

---

## Known limitations

- GDS runtime smoke test: NOT RUN — requires a dedicated Global Discovery Server.
- Reverse mode runtime smoke: NOT RUN — requires a compatible OPC UA reverse-client endpoint.
- Windows execution: not supported (Linux Agent required).
- GDS node discovery requires live GDS connection during script init; agent must reach the GDS before fuzzing begins.
