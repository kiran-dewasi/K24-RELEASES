"""Check current users in database and test login."""
import sys
sys.path.insert(0, '.')

from backend.database import get_db, User, Company

# Get database session
db = next(get_db())

# Check users
users = db.query(User).all()
print(f"\n=== USERS IN DATABASE ({len(users)}) ===")
for u in users:
    print(f"  - Email: {u.email}")
    print(f"    Username: {u.username}")
    print(f"    Full Name: {u.full_name}")
    print(f"    Tenant ID: {u.tenant_id}")
    print(f"    Company ID: {u.company_id}")
    print()

# Check companies
companies = db.query(Company).all()
print(f"=== COMPANIES IN DATABASE ({len(companies)}) ===")
for c in companies:
    print(f"  - {c.name} (ID: {c.id})")

# Test password verification
if users:
    user = users[0]
    from backend.auth import verify_password
    test_passwords = ['password123', 'kittu123', 'admin123', 'password', 'test123']
    print(f"\n=== TESTING PASSWORDS FOR {user.email} ===")
    for pwd in test_passwords:
        result = verify_password(pwd, user.hashed_password)
        print(f"  '{pwd}': {'CORRECT' if result else 'Wrong'}")
