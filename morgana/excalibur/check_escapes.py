import json
import glob
import re

for f in sorted(glob.glob('excalibur-*.json')):
    with open(f, encoding='utf-8') as file:
        content = file.read()
    
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        # Look for \ followed by a character that isn't a standard JSON escape
        # Valid escapes: \\, \", \/, \b, \f, \n, \r, \t, \uXXXX
        matches = re.finditer(r'(?<!\\)\\(?!\\|\"|\/|b|f|n|r|t|u)', line)
        for m in matches:
            print(f'{f}:{i}: Unescaped backslash near: {line[max(0,m.start()-20):m.end()+20]}')

print("Check complete.")