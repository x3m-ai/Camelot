"""
Fix JSON errors in Excalibur packs.
Run from the excalibur directory.

Targeted fixes:
- excalibur-collection-emulation-pack.json: invalid \. escape in regex patterns (lines 139, 155)
- excalibur-reconnaissance-emulation-pack.json: unescaped " in PowerShell command (line 167)
"""
import json
import os

FIXES = {
    'excalibur-collection-emulation-pack.json': [
        # Line 139: invalid \. escape -> double the backslash (long extension list)
        ("-imatch '\\.(docx|xlsx|pdf|txt|csv|kdbx|pfx|pem|key|rdp|ps1|bat|config|json|xml)$'",
         "-imatch '\\\\.(docx|xlsx|pdf|txt|csv|kdbx|pfx|pem|key|rdp|ps1|bat|config|json|xml)$'"),
        # Line 155: same pattern, shorter list (already fixed by previous run, but safe to repeat)
        ("-imatch '\\.(docx|xlsx|pdf|txt)$'",
         "-imatch '\\\\.(docx|xlsx|pdf|txt)$'"),
    ],
    'excalibur-reconnaissance-emulation-pack.json': [
        # Unescaped " inside JSON string values in PowerShell command on line 167
        ("EscapeDataString('\"' + $domain + '\" password')",
         "EscapeDataString('\\\"' + $domain + '\\\" password')"),
        ("'site:linkedin.com \"' + $domain + '\"'",
         "'site:linkedin.com \\\"' + $domain + '\\\"'"),
        ("'\"@' + $domain + '\" filetype:xlsx OR filetype:csv'",
         "'\\\"@' + $domain + '\\\" filetype:xlsx OR filetype:csv'"),
    ],
}

for filename, replacements in FIXES.items():
    if not os.path.exists(filename):
        print(f"[SKIP] {filename} not found")
        continue

    with open(filename, encoding='utf-8') as f:
        content = f.read()

    # Check if already valid
    try:
        json.loads(content)
        print(f"[OK] {filename} - already valid, skipping")
        continue
    except json.JSONDecodeError as e:
        print(f"[FIXING] {filename}: {e}")

    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            print(f"  Replaced: {repr(old[:60])}...")
        else:
            print(f"  [WARN] Pattern not found: {repr(old[:60])}...")

    try:
        json.loads(content)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[FIXED] {filename}")
    except json.JSONDecodeError as e2:
        print(f"[STILL ERROR] {filename}: {e2}")
        pos = e2.pos
        print(f"  Context: {repr(content[max(0,pos-80):pos+80])}")


