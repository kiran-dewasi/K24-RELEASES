# K24 Vercel Deployment Guide

## 🎯 What Gets Deployed to Vercel

| Component | Vercel? | Notes |
|-----------|---------|-------|
| Frontend (Next.js) | ✅ Yes | Main web app |
| Cloud API Routes | ✅ Yes | Auth, WhatsApp routing |
| Backend (FastAPI) | ❌ No | Runs locally on user's machine |
| Supabase | ☁️ Separate | Already cloud-hosted |

---

## 📦 Frontend Deployment (Next.js)

### Step 1: Push to GitHub
```bash
cd c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare
git add .
git commit -m "Prepare for Vercel deployment"
git push origin main
```

### Step 2: Connect to Vercel
1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Import your GitHub repository
4. Set these settings:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: Leave empty (auto-detected)

### Step 3: Set Environment Variables
In Vercel Dashboard → Project → Settings → Environment Variables:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://gxukvnoiyzizienswgni.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_IdvVP3vXN7sudoADapfHtQ_BamNI22t
```

**Important:** `NEXT_PUBLIC_API_URL` should be:
- `http://localhost:8000` for desktop app (backend runs locally)
- OR your cloud backend URL if you deploy backend too

### Step 4: Deploy
Click "Deploy" and wait ~2 minutes.

Your app will be live at: `https://your-project.vercel.app`

---

## 🖥️ Desktop App Configuration

After Vercel deployment, update Tauri to load from your Vercel URL:

### Update `frontend/src-tauri/tauri.conf.json`:
```json
{
  "build": {
    "devUrl": "http://localhost:3000",
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": ""
  }
}
```

For production, you can either:
1. Keep loading from Vercel URL (requires internet)
2. Build static files and bundle them (offline UI)

---

## 🔐 Backend API Routes on Vercel

For cloud-only features (auth routing, WhatsApp tenant detection), create API routes:

### Create `frontend/app/api/auth/route.ts`:
```typescript
// Handles cloud authentication
export async function POST(request: Request) {
  // Your auth logic here
}
```

### Create `frontend/app/api/whatsapp/route/route.ts`:
```typescript
// Routes WhatsApp messages to correct tenant
export async function POST(request: Request) {
  const { sender_phone, message } = await request.json();
  
  // Look up tenant_id from Supabase
  // Return the tenant's local backend URL or queue message
}
```

---

## ⚠️ Important Notes

### API URL Configuration

The frontend needs to know where the backend is:

1. **For Desktop App Users:**
   - Backend runs locally at `http://localhost:8000`
   - Set `NEXT_PUBLIC_API_URL=http://localhost:8000`

2. **For Web-Only Users (if any):**
   - Would need cloud backend
   - Currently not supported in your architecture

### The Hybrid Approach

Your architecture is:
```
Web App (Vercel) → UI only
                 → Auth via Supabase
                 → API calls go to → User's local backend (port 8000)
```

This means:
- ✅ Users access the UI from anywhere
- ✅ Data stays local (privacy)
- ⚠️ Users must have local backend running for full functionality

---

## 🚀 Quick Deploy Checklist

- [ ] Code pushed to GitHub
- [ ] Connected to Vercel
- [ ] Environment variables set
- [ ] Build successful
- [ ] Test login works
- [ ] Test dashboard loads (with local backend running)

---

## 📞 Troubleshooting

### "API calls fail"
- Check if local backend is running: `http://localhost:8000/docs`
- Check browser console for CORS errors

### "Login doesn't work"
- Verify Supabase credentials in Vercel env vars
- Check Supabase dashboard for auth logs

### "Build fails on Vercel"
- Check build logs in Vercel dashboard
- Common issue: missing environment variables

---

*Created: January 29, 2026*
