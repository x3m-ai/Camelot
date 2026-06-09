import json
import glob
import sys

for f in sorted(glob.glob('excalibur-*.json')):
    try:
        with open(f, encoding='utf-8') as file:
            data = json.load(file)
        print(f"[OK] {f}")
    except json.JSONDecodeError as e:
        print(f"[ERR] {f}")
        print(f"  Line {e.lineno}, Column {e.colno}: {e.msg}")
        # Print the problematic line
        with open(f, encoding='utf-8') as file:
            lines = file.readlines()
            if e.lineno <= len(lines):
                print(f"  Content: {lines[e.lineno-1].strip()}")