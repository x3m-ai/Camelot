"""Fix c2 pack: invalid \\s escape + unescaped double-quotes in browser UA headers."""
import json

VALID = set('"\\/ bfnrtu')

# Pre-fix: escape the literal " chars inside PowerShell single-quoted strings
# that sit inside JSON string values. These come from Sec-Ch-Ua browser headers.
QUOTE_FIXES = [
    (
        """'Sec-Ch-Ua' = '"Chromium";v="120", "Not(A:Brand";v="24"'""",
        """'Sec-Ch-Ua' = '\\"Chromium\\";v=\\"120\\", \\"Not(A:Brand\\";v=\\"24\\"'""",
    ),
    (
        """'Sec-Ch-Ua-Platform' = '"Windows"'""",
        """'Sec-Ch-Ua-Platform' = '\\"Windows\\"'""",
    ),
]


def fix_backslashes(content):
    result = []
    i = 0
    n = len(content)
    while i < n:
        ch = content[i]
        if ch == '"':
            result.append('"')
            i += 1
            while i < n:
                c = content[i]
                if c == '\\':
                    if i + 1 < n:
                        nc = content[i + 1]
                        if nc in VALID:
                            result.append('\\')
                            result.append(nc)
                            i += 2
                            if nc == 'u':
                                result.append(content[i:i + 4])
                                i += 4
                        else:
                            result.append('\\\\')
                            i += 1
                    else:
                        result.append('\\\\')
                        i += 1
                elif c == '"':
                    result.append('"')
                    i += 1
                    break
                else:
                    result.append(c)
                    i += 1
        else:
            result.append(ch)
            i += 1
    return ''.join(result)


fname = 'excalibur-c2-emulation-pack.json'
with open(fname, encoding='utf-8') as f:
    content = f.read()

try:
    json.loads(content)
    print('[OK] already valid')
    exit(0)
except json.JSONDecodeError as e:
    print(f'[FIXING] {e}')

# Step 1: targeted quote fixes
for old, new in QUOTE_FIXES:
    if old in content:
        content = content.replace(old, new)
        print(f'  quote-fixed: {repr(old[:60])}')
    else:
        print(f'  [WARN] not found: {repr(old[:60])}')

# Step 2: general backslash fixer
fixed = fix_backslashes(content)

try:
    json.loads(fixed)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(fixed)
    print(f'[FIXED] {fname}')
except json.JSONDecodeError as e2:
    print(f'[STILL ERROR] {e2}')
    print(f'  ctx: {repr(fixed[max(0, e2.pos-80):e2.pos+80])}')
