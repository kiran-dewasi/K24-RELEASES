import sqlite3
import json

conn = sqlite3.connect("k24_shadow.db")
cur = conn.cursor()

def get_data(query):
    try:
        cur.execute(query)
        cols = [description[0] for description in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        return str(e)

data = {
    "USERS": get_data("SELECT id, full_name, email, role, tenant_id FROM users"),
    "TENANTS": get_data("SELECT * FROM tenants"),
    "TENANT_CONFIG": get_data("SELECT * FROM tenant_config")
}

with open("audit1_result.json", "w") as f:
    json.dump(data, f, indent=2)

conn.close()
