"""
Generate Supabase API Keys from JWT Secret
"""
import jwt
import time

# Your JWT Secret (from Legacy JWT Secret in Supabase Dashboard)
JWT_SECRET = "ED4K0zgO0crCHJFJcwx+naNv5SXcqgrQcNYHRLKTgdNqYHs0oDyev81LWQMRBZZdLE/Dh+9Sn7VLMDJdRq1qCg=="

# Your Project Reference ID
PROJECT_REF = "gxukvnoiyzizienswgni"

# Timestamps
iat = int(time.time())  # Issued at: now
exp = iat + (10 * 365 * 24 * 60 * 60)  # Expires: 10 years from now

# Anon Key Payload
anon_payload = {
    "iss": "supabase",
    "ref": PROJECT_REF,
    "role": "anon",
    "iat": iat,
    "exp": exp
}

# Service Role Key Payload
service_role_payload = {
    "iss": "supabase",
    "ref": PROJECT_REF,
    "role": "service_role",
    "iat": iat,
    "exp": exp
}

# Generate Keys
import base64
secret_bytes = base64.b64decode(JWT_SECRET)

anon_key = jwt.encode(anon_payload, secret_bytes, algorithm="HS256")
service_role_key = jwt.encode(service_role_payload, secret_bytes, algorithm="HS256")

print("=" * 70)
print("GENERATED SUPABASE API KEYS")
print("=" * 70)
print()
print("SUPABASE_ANON_KEY (for .env):")
print(anon_key)
print()
print("SUPABASE_SERVICE_ROLE_KEY (for .env):")
print(service_role_key)
print()
print("=" * 70)
