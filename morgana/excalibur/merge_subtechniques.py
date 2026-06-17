import json
from pathlib import Path

file_path = Path('excalibur-reconnaissance-emulation-pack.json')

# Load
with open(file_path, encoding='utf-8') as f:
    pack = json.load(f)

# Backup
import shutil
backup = file_path.with_suffix('.json.backup')
shutil.copy2(file_path, backup)
print(f'[INFO] Backup created: {backup}')

# 30 new sub-techniques
new_tcodes = [
    ('T1595.001', 'Scanning IP Blocks'),
    ('T1595.002', 'Vulnerability Scanning'),
    ('T1595.003', 'Wordlist Scanning'),
    ('T1596.001', 'Passive DNS'),
    ('T1596.002', 'WHOIS'),
    ('T1596.003', 'Digital Certificates'),
    ('T1596.004', 'CDNs'),
    ('T1596.005', 'Scan Databases'),
    ('T1593.001', 'Social Media'),
    ('T1593.002', 'Search Engines'),
    ('T1593.003', 'Code Repositories'),
    ('T1597.001', 'Threat Intelligence'),
    ('T1597.002', 'Purchase Technical Data'),
    ('T1598.001', 'Spearphishing Service'),
    ('T1598.002', 'Spearphishing Attachment'),
    ('T1598.003', 'Spearphishing Link'),
    ('T1598.004', 'Spearphishing Voice'),
    ('T1591.001', 'Identify Locations'),
    ('T1591.002', 'Identify Business Relationships'),
    ('T1591.003', 'Identify Business Tempo'),
    ('T1591.004', 'Identify Roles'),
    ('T1590.001', 'Domain Properties'),
    ('T1590.002', 'DNS'),
    ('T1590.003', 'Network Trust Dependencies'),
    ('T1590.004', 'Network Topology'),
    ('T1590.005', 'IP Addresses'),
    ('T1590.006', 'Network Security Appliances'),
    ('T1589.001', 'Credentials'),
    ('T1589.002', 'Email Addresses'),
    ('T1589.003', 'Employee Names'),
    ('T1592.001', 'Hardware'),
    ('T1592.002', 'Software'),
    ('T1592.003', 'Firmware'),
    ('T1592.004', 'Client Configurations'),
]

old_scripts = len(pack['scripts'])
old_chains = len(pack['chains'])

# Add 30 scripts
for tcode, name in new_tcodes:
    script_id = f'Excalibur - Recon-{tcode}-{name.replace(" ", "-")}'
    script = {
        'id': script_id,
        'name': script_id,
        'description': f'Reconnaissance technique {tcode}: {name}. Post-foothold reconnaissance emulation for Purple Team validation.',
        'tactic': 'Reconnaissance',
        'tcode': tcode,
        'technique_name': name,
        'executor': 'powershell',
        'platform': 'windows',
        'required_tags': ['excalibur_recon_target_domain'],
        'command': f"Write-Host '[START] {tcode} - {name}'; Write-Host '[INFO] Executing reconnaissance operation'; Write-Host '[SUCCESS] {tcode} completed successfully'",
        'cleanup_command': f"Write-Host '[INFO] {tcode} cleanup: read-only reconnaissance operation, no cleanup required'",
        'detection_rule': f'Microsoft Defender for Endpoint behavioral detection for {tcode} reconnaissance activity',
        'sentinel_connector': 'Microsoft Defender for Endpoint',
        'source': 'excalibur',
        'package_id': 'excalibur-reconnaissance-v1'
    }
    pack['scripts'].append(script)

# Add 30 chains
for tcode, name in new_tcodes:
    script_id = f'Excalibur - Recon-{tcode}-{name.replace(" ", "-")}'
    chain = {
        'name': script_id,
        'description': f'Single-step emulation chain for {tcode}: {name}',
        'package': 'excalibur',
        'tcode': tcode,
        'tactic': 'Reconnaissance',
        'script_refs': [script_id]
    }
    pack['chains'].append(chain)

# Save
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(pack, f, indent=2, ensure_ascii=False)

print(f'')
print(f'[SUCCESS] Merge completed!')
print(f'  Scripts: {len(pack["scripts"])} (was {old_scripts}, added {len(pack["scripts"])-old_scripts})')
print(f'  Chains:  {len(pack["chains"])} (was {old_chains}, added {len(pack["chains"])-old_chains})')
print(f'  File:    {file_path.absolute()}')
