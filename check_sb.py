import urllib.request
import json

url = "https://gxukvnoiyzizienswgni.supabase.co/rest/v1/"
key = "sb_secret_qJuJk2q0_hO144oQLmSYxA_6WB_qtkR"

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

req_get = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req_get) as response:
        spec = json.loads(response.read().decode('utf-8'))
        print("Supabase tenant_config columns:")
        print(json.dumps(spec.get('definitions', {}).get('tenant_config', {}).get('properties', {}), indent=2))
except Exception as e:
    print("GET OpenAPI error:", e)
