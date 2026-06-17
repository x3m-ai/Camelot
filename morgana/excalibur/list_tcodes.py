import json

data = json.load(open(r'C:\Users\ninoc\OfficeAddinApps\Camelot\morgana\excalibur\excalibur-reconnaissance-emulation-pack.json'))

parents = [s for s in data['scripts'] if '.' not in s['tcode']]
subs = [s for s in data['scripts'] if '.' in s['tcode']]

print('\n[PARENT TECHNIQUES - {}]'.format(len(parents)))
for s in sorted(parents, key=lambda x: x['tcode']):
    print(f'  {s["tcode"]:<12} {s["technique_name"]}')

print('\n[SUB-TECHNIQUES - {}]'.format(len(subs)))
for s in sorted(subs, key=lambda x: x['tcode']):
    print(f'  {s["tcode"]:<12} {s["technique_name"]}')

print(f'\n[TOTALS]')
print(f'  Scripts: {len(data["scripts"])}')
print(f'  Chains:  {len(data["chains"])}')
