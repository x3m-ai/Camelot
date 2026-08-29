import json
import os
import sys

catalog_path = '../catalog.json'
with open(catalog_path, 'r', encoding='utf-8') as f:
    catalog = json.load(f)

packs = catalog.get('packs', [])
print(f"Total packs in catalog: {len(packs)}")

mismatches = []
missing_files = []
provider_counts = {}
category_counts = {}

# We need to verify each pack:
# URL: https://raw.githubusercontent.com/x3m-ai/Camelot/main/morgana/excalibur/category/filename.json
# Local path should map to camelot/morgana/excalibur/category/filename.json
# Since our script is running in tools, the parent directory contains categories as directories (art, general, technology, stockpile, ot, etc.)

for p in packs:
    package_id = p.get('package_id')
    provider = p.get('provider')
    category = p.get('category')
    url = p.get('url')
    
    # Counts
    provider_counts[provider] = provider_counts.get(provider, 0) + 1
    category_counts[category] = category_counts.get(category, 0) + 1
    
    # Get local path
    # Find excalibur in the URL path
    parts = url.replace('\\', '/').split('/')
    try:
        ex_idx = parts.index('excalibur')
        rel_parts = parts[ex_idx:] # ['excalibur', 'category', 'file.json']
        # Local dir from tools is ../<category>/<file.json>
        local_path = os.path.join('..', *rel_parts[1:])
    except ValueError:
        print(f"Error parsing URL for {package_id}: {url}")
        continue
        
    if not os.path.exists(local_path):
        missing_files.append((package_id, local_path))
        continue
        
    # Load local JSON file
    try:
        with open(local_path, 'r', encoding='utf-8') as lf:
            local_data = json.load(lf)
    except Exception as e:
        mismatches.append((package_id, f"Failed to load/parse {local_path}: {e}"))
        continue
        
    # Check fields: package_id, description, provider, capabilities, use_cases, prerequisites, safety_notes
    # For list fields, they should match either as a list or string content
    fields_to_check = ['package_id', 'description', 'provider', 'capabilities', 'use_cases', 'prerequisites', 'safety_notes']
    for field in fields_to_check:
        cat_val = p.get(field)
        loc_val = local_data.get(field)
        
        # If it's a list, let's normalize or compare elements
        if isinstance(cat_val, list) or isinstance(loc_val, list):
            # Convert both to list of strings or list
            c_list = cat_val if isinstance(cat_val, list) else ([cat_val] if cat_val is not None else [])
            l_list = loc_val if isinstance(loc_val, list) else ([loc_val] if loc_val is not None else [])
            if c_list != l_list:
                mismatches.append((package_id, field, c_list, l_list))
        else:
            if cat_val != loc_val:
                mismatches.append((package_id, field, cat_val, loc_val))

print(f"\nMissing Files Count: {len(missing_files)}")
for pid, path in missing_files:
    print(f"  Missing: {pid} at {path}")

print(f"\nMismatches Count: {len(mismatches)}")
for item in mismatches:
    if len(item) == 2:
        print(f"  {item[0]}: {item[1]}")
    else:
        print(f"  {item[0]} mismatch in '{item[1]}':\n    Catalog: {item[2]}\n    Local:   {item[3]}")

print("\n--- Provider Counts ---")
for prov, count in sorted(provider_counts.items()):
    print(f"  {prov}: {count}")

print("\n--- Category Counts ---")
for cat, count in sorted(category_counts.items()):
    print(f"  {cat}: {count}")
    
