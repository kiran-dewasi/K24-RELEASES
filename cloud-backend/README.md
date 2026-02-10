# K24 Cloud Backend

Cloud-hosted FastAPI service for K24 multi-tenant platform.

## Purpose

This service runs on **Railway/Cloud** and handles:
- ✅ User authentication & authorization
- ✅ WhatsApp message routing (from Baileys service)
- ✅ Customer-to-tenant mapping
- ✅ Device registration & management
- ✅ Smart query processing
- ✅ Central message queue for desktop apps

## What's NOT Here

This cloud backend does **NOT** handle:
- ❌ Direct Tally integration (port 9000)
- ❌ Local Tally sync operations  
- ❌ Desktop-specific features
- ❌ Local file storage

Those remain in the **desktop sidecar** (`backend/` folder).

## Architecture

```
WhatsApp → Baileys Service → Cloud Backend → Message Queue
                                    ↓
                              Desktop App (polls queue)
                                    ↓
                              Local Tally (port 9000)
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run locally:**
   ```bash
   uvicorn main:app --reload --port 8080
   ```

4. **Deploy to Railway:**
   ```bash
   # Connect Railway CLI
   railway login
   
   # Deploy
   railway up
   ```

## Routers

- `auth.py` - User registration, login, JWT tokens
- `whatsapp.py` - Customer mapping CRUD
- `whatsapp_cloud.py` - Incoming message webhook from Baileys
- `baileys.py` - Baileys message processing
- `devices.py` - Desktop device registration
- `query.py` - Smart query orchestrator

## Environment Variables

See `.env.example` for required configuration.

## Deployment

Optimized for Railway deployment with:
- Auto-scaling
- Persistent PostgreSQL (Supabase)
- Health checks
- Sentry monitoring
