import json
import glob
import urllib.request
import urllib.error
import ssl

# Bypass SSL verification for localhost
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

api_key = "mrg_2bb4ed2c1751327350f0e76702ae2fefb7290998ba7e85d9a572251beb70c2de"
url = "https://localhost:8888/api/v2/scripts/import-package"

for f in sorted(glob.glob('excalibur-*.json')):
    print(f"\n--- Testing {f} ---")
    with open(f, 'r', encoding='utf-8') as file:
        payload = file.read().encode('utf-8')
    
    req = urllib.request.Request(url, data=payload, method='POST')
    req.add_header('KEY', api_key)
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"[SUCCESS] {f}")
            print(f"  Imported: {result.get('imported', 0)}")
            print(f"  Removed: {result.get('removed', 0)}")
            if result.get('errors'):
                print(f"  Errors: {result['errors']}")
            if result.get('chains_errors'):
                print(f"  Chain Errors: {result['chains_errors']}")
    except urllib.error.HTTPError as e:
        print(f"[HTTP ERROR {e.code}] {f}")
        try:
            error_body = json.loads(e.read().decode('utf-8'))
            print(f"  Detail: {error_body.get('detail', 'Unknown')}")
        except:
            print(f"  Detail: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[ERROR] {f}: {e}")

print("\n--- Import simulation complete ---")