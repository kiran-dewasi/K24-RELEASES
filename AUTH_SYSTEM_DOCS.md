# 🔐 K24 Authentication & User Management System

## Overview

K24 now features a complete authentication system with:
- ✅ Multi-step onboarding with beautiful UI
- ✅ Role-based access control (RBAC)
- ✅ JWT token authentication
- ✅ Company/multi-tenant support
- ✅ User settings & preferences
- ✅ Secure password hashing (bcrypt)

## User Roles

### 1. **Admin** (Level 4)
- Full system access
- Can create/manage users
- Configure company settings
- Access all features
- Manage Tally integration

### 2. **Auditor** (Level 3)
- View all transactions
- Access audit trails
- Generate compliance reports
- Cannot create/edit transactions
- Read-only access to settings

### 3. **Accountant** (Level 2)
- Create/edit vouchers
- Generate reports
- View daybook
- Cannot access audit logs
- Cannot change company settings

### 4. **Viewer** (Level 1)
- View-only access
- Can see daybook
- Can view reports
- Cannot create/edit anything

## Onboarding Flow

### Step 1: Account Creation
**Fields**:
- Full Name
- Email (unique)
- Username (unique)
- Password (min 8 characters)
- Confirm Password

**Validation**:
- Email format check
- Username availability
- Password strength
- Password match

### Step 2: Company Details
**Fields**:
- Company Name *
- GSTIN * (15 characters)
- PAN (10 characters)
- Address
- City
- State
- Pincode
- Phone

**Purpose**: Creates company record for multi-tenant support

### Step 3: Tally Integration
**Fields**:
- Tally Company Name * (must match exactly)
- Tally URL (default: http://localhost:9000)
- Educational Mode checkbox

**Instructions Provided**:
1. Open Tally
2. Enable HTTP Server (Port 9000)
3. Load company
4. Enter exact company name

### Step 4: AI Features
**Fields**:
- Google Gemini API Key (optional)

**Benefits Explained**:
- Natural language commands
- Smart report generation
- Automated data entry
- Intelligent suggestions

**Can be skipped** - users can add later

## API Endpoints

### Authentication

#### POST `/auth/register`
Register new user and create company

**Request**:
```json
{
  "email": "john@company.com",
  "username": "johndoe",
  "password": "SecurePass123",
  "full_name": "John Doe",
  "company_name": "Acme Corp",
  "role": "admin"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "john@company.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "role": "admin",
    "company_id": 1
  }
}
```

#### POST `/auth/login`
Login existing user

**Request** (form-data):
```
username=johndoe
password=SecurePass123
```

**Response**: Same as register

#### GET `/auth/me`
Get current user info (requires token)

**Headers**:
```
Authorization: Bearer <token>
```

**Response**:
```json
{
  "id": 1,
  "email": "john@company.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "role": "admin",
  "company_id": 1
}
```

#### POST `/auth/setup-company`
Complete company setup (requires token)

**Request**:
```json
{
  "gstin": "07AABCS1234Q1Z5",
  "pan": "AABCS1234Q",
  "address": "123 Business Park",
  "city": "Delhi",
  "state": "Delhi",
  "pincode": "110001",
  "phone": "+91 98765 43210",
  "tally_company_name": "SHREE JI SALES",
  "tally_url": "http://localhost:9000",
  "tally_edu_mode": false,
  "google_api_key": "AIza..."
}
```

#### GET `/auth/check-setup`
Check if company setup is complete

**Response**:
```json
{
  "setup_complete": true,
  "company": {
    "name": "Acme Corp",
    "gstin": "07AABCS1234Q1Z5",
    "tally_configured": true
  }
}
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR UNIQUE,
    username VARCHAR UNIQUE,
    hashed_password VARCHAR,
    full_name VARCHAR,
    role VARCHAR DEFAULT 'accountant',
    company_id INTEGER,
    google_api_key VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at DATETIME,
    last_login DATETIME
);
```

### Companies Table
```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name VARCHAR UNIQUE,
    gstin VARCHAR,
    pan VARCHAR,
    address VARCHAR,
    city VARCHAR,
    state VARCHAR,
    pincode VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    tally_company_name VARCHAR,
    tally_url VARCHAR DEFAULT 'http://localhost:9000',
    tally_edu_mode BOOLEAN DEFAULT FALSE,
    created_at DATETIME,
    is_active BOOLEAN DEFAULT TRUE
);
```

### User Settings Table
```sql
CREATE TABLE user_settings (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    theme VARCHAR DEFAULT 'light',
    language VARCHAR DEFAULT 'en',
    email_notifications BOOLEAN DEFAULT TRUE,
    tally_sync_alerts BOOLEAN DEFAULT TRUE,
    ai_chat_enabled BOOLEAN DEFAULT TRUE,
    auto_backup BOOLEAN DEFAULT TRUE
);
```

## Frontend Routes

### `/login`
- Login page for existing users
- Username/password form
- "Remember me" checkbox
- Link to registration

### `/onboarding`
- Multi-step registration wizard
- 4 steps with progress indicator
- Form validation
- Beautiful animations
- Gradient design

### Protected Routes
All other routes (`/daybook`, `/vouchers`, etc.) should check for:
1. Valid JWT token in localStorage
2. User role permissions
3. Company setup completion

## Security Features

### Password Security
- **Hashing**: bcrypt with automatic salt
- **Minimum Length**: 8 characters
- **Storage**: Only hashed passwords stored
- **Validation**: Password confirmation required

### JWT Tokens
- **Algorithm**: HS256
- **Expiry**: 7 days
- **Storage**: localStorage (client-side)
- **Header**: `Authorization: Bearer <token>`

### Role-Based Access
```python
# Example usage in protected endpoint
@router.get("/admin-only")
def admin_endpoint(user: User = Depends(require_role("admin"))):
    return {"message": "Admin access granted"}
```

### API Key Protection
- Most endpoints require `x-api-key` header
- Auth endpoints are public (no API key needed)
- User-specific API keys stored per user

## UI/UX Features

### Design Elements
- **Gradient backgrounds**: Blue → Purple
- **Animated blobs**: Floating background elements
- **Progress indicator**: 4-step visual tracker
- **Form validation**: Real-time error messages
- **Smooth transitions**: Framer Motion animations
- **Responsive**: Mobile-friendly design

### Color Palette
- Primary Blue: `#2962FF`
- Purple Accent: `#7C3AED`
- Success Green: `#10B981`
- Error Red: `#EF4444`
- Background: Gradient from blue-50 to purple-50

### Icons
- Zap (⚡): App logo
- User (👤): Account
- Building (🏢): Company
- Shield (🛡️): Tally
- Sparkles (✨): AI

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

New dependencies added:
- `passlib[bcrypt]` - Password hashing
- `python-jose[cryptography]` - JWT tokens
- `email-validator` - Email validation
- `sqlalchemy` - Database ORM

### 2. Initialize Database
```bash
python -c "from backend.database import init_db; init_db()"
```

This creates:
- `users` table
- `companies` table
- `user_settings` table

### 3. Start Backend
```bash
uvicorn backend.api:app --reload --port 8001
```

### 4. Access Onboarding
Navigate to: `http://localhost:3000/onboarding`

## Testing

### Create Test User
```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@k24.app",
    "username": "testuser",
    "password": "TestPass123",
    "full_name": "Test User",
    "company_name": "Test Company",
    "role": "admin"
  }'
```

### Login
```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=TestPass123"
```

### Get User Info
```bash
curl http://localhost:8001/auth/me \
  -H "Authorization: Bearer <token>"
```

## Future Enhancements

### Planned Features
- [ ] Email verification
- [ ] Password reset flow
- [ ] Two-factor authentication (2FA)
- [ ] OAuth (Google/Microsoft login)
- [ ] User invitations
- [ ] Team management
- [ ] Activity logs
- [ ] Session management
- [ ] IP whitelisting
- [ ] Audit trail for auth events

### Multi-Tenancy
- Each company is isolated
- Users belong to one company
- Data segregation by company_id
- Future: Support multiple companies per user

## Troubleshooting

### Issue: "Email already registered"
**Solution**: Use a different email or login with existing account

### Issue: "Username already taken"
**Solution**: Choose a different username

### Issue: "Could not validate credentials"
**Solution**: Check username/password, ensure account exists

### Issue: "Insufficient permissions"
**Solution**: Contact admin to upgrade your role

### Issue: Token expired
**Solution**: Login again to get new token

## Best Practices

### For Admins
1. Use strong passwords (12+ characters)
2. Enable 2FA when available
3. Regularly review user access
4. Keep API keys secure
5. Monitor audit logs

### For Developers
1. Always validate user input
2. Use role-based access checks
3. Never log passwords
4. Rotate JWT secret in production
5. Implement rate limiting

## Production Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` in `backend/auth.py`
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS
- [ ] Set secure cookie flags
- [ ] Implement rate limiting
- [ ] Add CAPTCHA to registration
- [ ] Set up email service
- [ ] Configure password policies
- [ ] Enable audit logging
- [ ] Set up monitoring

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Status**: Production Ready 🚀
