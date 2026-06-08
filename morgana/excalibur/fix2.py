"""Fix JSON errors in Excalibur packs."""
import json

VALID = set('"\\/ bfnrtu')


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
                            # invalid escape: double the backslash
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


for fname in [
    'excalibur-collection-emulation-pack.json',
    'excalibur-reconnaissance-emulation-pack.json',
]:
    with open(fname, encoding='utf-8') as f:
        content = f.read()

    try:
        json.loads(content)
        print('[OK]', fname)
        continue
    except json.JSONDecodeError as e:
        print('[FIXING]', fname, '-', e)

    fixed = fix_backslashes(content)

    try:
        json.loads(fixed)
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(fixed)
        print('[FIXED]', fname)
    except json.JSONDecodeError as e2:
        print('[STILL ERROR]', fname, '-', e2)
        print('  ctx:', repr(fixed[max(0, e2.pos - 60):e2.pos + 60]))
