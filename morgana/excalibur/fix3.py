"""Fix JSON errors in all Excalibur packs."""
import json
import glob

VALID = set('"\\/ bfnrtu')

# Targeted pre-fixes for unescaped " inside JSON string values (privesc pack)
# These run BEFORE the general backslash scanner
TARGETED_QUOTE_FIXES = {
    'excalibur-privesc-emulation-pack.json': [
        ("-replace '\"',''", "-replace '\\\"',''"),
    ],
}


def fix_backslashes(content):
    """Walk JSON, fix invalid backslash escapes inside string values."""
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


for fname in sorted(glob.glob('excalibur-*.json')):
    with open(fname, encoding='utf-8') as f:
        content = f.read()

    try:
        json.loads(content)
        print('[OK]', fname)
        continue
    except json.JSONDecodeError as e:
        print('[FIXING]', fname, '-', e)

    # Apply targeted quote fixes first if any
    for old, new in TARGETED_QUOTE_FIXES.get(fname, []):
        if old in content:
            content = content.replace(old, new)
            print(f'  quote-fix: {repr(old[:50])}')

    # Apply general backslash fixer
    fixed = fix_backslashes(content)

    try:
        json.loads(fixed)
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(fixed)
        print('[FIXED]', fname)
    except json.JSONDecodeError as e2:
        print('[STILL ERROR]', fname, '-', e2)
        print('  ctx:', repr(fixed[max(0, e2.pos - 60):e2.pos + 60]))
