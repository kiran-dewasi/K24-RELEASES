# K24 Baileys WhatsApp Listener

Node.js service using Baileys library for WhatsApp integration.

## Purpose

This service:
- ✅ Maintains WhatsApp Web connection (like WhatsApp Web API)
- ✅ Receives incoming WhatsApp messages 24/7
- ✅ Routes messages to cloud backend webhook
- ✅ Sends replies back to customers
- ✅ Handles multi-session support (optional)

## Architecture

```
WhatsApp Servers ← Baileys (this service) → Cloud Backend API
                         ↓
                   Auth State Storage
                   (persistent volume)
```

## Files

- `listener.js` - Main WhatsApp event handler
- `batch-handler.js` - Smart message batching for bulk images
- `package.json` - Node dependencies
- `auth/` - WhatsApp session credentials (encrypted)

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment:**
   ```bash
   # Create .env file
   BACKEND_URL=https://api.k24.ai
   BAILEYS_SECRET=k24_baileys_secret_change_me
   NODE_ENV=production
   ```

3. **Run locally:**
   ```bash
   node listener.js
   ```
   - Scan QR code with WhatsApp to authenticate
   - QR code appears in terminal on first run

4. **Deploy to cloud:**
   - Requires persistent volume for `auth/` folder
   - Use Railway, DigitalOcean, or similar with file storage

## Deployment Checklist

- [ ] Set `BACKEND_URL` to cloud API endpoint
- [ ] Set `BAILEYS_SECRET` to match cloud backend
- [ ] Mount persistent volume at `/app/auth`
- [ ] Keep service running 24/7
- [ ] Monitor logs for disconnections

## Multi-Tenant Setup (Future)

For multiple WhatsApp numbers:
- Create separate Baileys instances per tenant
- Store auth in `auth/{tenant_id}/` folders
- Load sessions dynamically based on tenant

## Security

- ⚠️ **Auth folder is sensitive** - contains WhatsApp credentials
- Must be encrypted at rest
- Never commit `auth/` to git
- Use environment variables for all secrets
