import requests
import json
import sys
import traceback

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Test the failing query with debug
query = 'How much does Shree Ganesh owe?'
print(f'Testing: "{query}"')

try:
    r = requests.post(
        'http://localhost:8000/api/query/whatsapp',
        json={'query': query, 'context': {}},
        headers={'X-Baileys-Secret': 'k24_baileys_secret'},
        timeout=30
    )
    print(f'Status Code: {r.status_code}')
    print(f'Response: {json.dumps(r.json(), indent=2, ensure_ascii=False)}')
except Exception as e:
    print(f'Error: {e}')
    traceback.print_exc()
