# K24 Intelligent ERP - Quick Start Guide

## 🚀 Installation Options

### Option 1: Docker (Recommended - Easiest)

**Prerequisites**:
- Docker Desktop installed ([Download](https://www.docker.com/products/docker-desktop))
- Tally running on your machine (Port 9000)

**Steps**:
```bash
# 1. Extract K24 folder
# 2. Open terminal in K24 folder
# 3. Copy environment file
cp .env.example .env

# 4. Edit .env file with your details
notepad .env

# 5. Start K24
docker-compose up -d

# 6. Access K24
# Open browser: http://localhost:3000
```

**To Stop**:
```bash
docker-compose down
```

**To Update**:
```bash
docker-compose pull
docker-compose up -d
```

---

### Option 2: Manual Installation

**Prerequisites**:
- Python 3.11+ ([Download](https://www.python.org/downloads/))
- Node.js 20+ ([Download](https://nodejs.org/))
- Tally running (Port 9000)

**Backend Setup**:
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
notepad .env

# 3. Initialize database
python -c "from backend.database import init_db; init_db()"

# 4. Start backend
uvicorn backend.api:app --reload --port 8001
```

**Frontend Setup** (New terminal):
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start frontend
npm run dev
```

**Access**: http://localhost:3000

---

## ⚙️ Configuration

### Tally Setup

1. **Enable HTTP Server**:
   - Open Tally
   - Press `F1` (Help)
   - Type "Configuration"
   - Go to: Connectivity → Client/Server Configuration
   - Set: `Enable Server` = Yes
   - Set: `Port` = 9000
   - Save

2. **Load Your Company**:
   - Open your company in Tally
   - Keep Tally running while using K24

### Environment Variables (`.env`)

```env
# Tally Configuration
TALLY_URL=http://localhost:9000
TALLY_COMPANY=YOUR COMPANY NAME
TALLY_EDU_MODE=false  # Set to 'true' if using Tally Educational

# AI Features (Optional)
GOOGLE_API_KEY=your_gemini_api_key_here

# System
TALLY_LIVE_UPDATE_ENABLED=true
```

**Get Google API Key** (for AI chat):
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key
3. Copy to `.env`

---

## 🎯 First Steps

### 1. Create Your First Receipt

**Method A: Using Chat**
```
Type: "Create receipt from ABC Corp for ₹50,000"
```

**Method B: Using Form**
1. Click "New Receipt"
2. Fill details
3. Click "Create"

### 2. View Transactions
- Click "Daybook" in sidebar
- See all transactions
- Click any transaction to view details
- Download PDF

### 3. Check Tally Sync
- Open Tally
- Go to Daybook (Alt+F1)
- Verify transaction appears

---

## 📱 Features Overview

### ✅ Core Features
- **Receipt Vouchers**: Cash/Bank receipts
- **Payment Vouchers**: Cash/Bank payments
- **Sales Invoices**: GST-compliant invoices
- **Daybook**: View all transactions
- **PDF Export**: Professional invoices
- **Tally Sync**: Real-time synchronization

### ✅ Advanced Features
- **AI Chat**: Natural language commands
- **Audit Trail**: MCA-compliant logging
- **Outstanding Reports**: Receivables/Payables
- **Contact Management**: Customer/Vendor database
- **GST Validation**: GSTIN verification

---

## 🔧 Troubleshooting

### Issue: "Cannot connect to Tally"

**Solution**:
1. Check Tally is running
2. Verify HTTP server is enabled (Port 9000)
3. Check `.env` has correct `TALLY_URL`
4. Test: Open browser → `http://localhost:9000`

### Issue: "Frontend not loading"

**Solution**:
1. Check backend is running (Port 8001)
2. Check frontend is running (Port 3000)
3. Clear browser cache
4. Try: `http://127.0.0.1:3000`

### Issue: "Transactions not syncing to Tally"

**Solution**:
1. Check company name matches exactly
2. Verify Tally company is open
3. Check backend logs for errors
4. Ensure `TALLY_LIVE_UPDATE_ENABLED=true`

### Issue: "AI chat not working"

**Solution**:
1. Check `GOOGLE_API_KEY` is set in `.env`
2. Verify API key is valid
3. Check internet connection
4. Restart backend

---

## 📞 Support

### Get Help
- **Email**: support@k24.app
- **WhatsApp**: +91-XXXXXXXXXX
- **Discord**: [K24 Community](https://discord.gg/k24)
- **Documentation**: [docs.k24.app](https://docs.k24.app)

### Report Bugs
- **GitHub Issues**: [github.com/k24/issues](https://github.com/k24/issues)
- **Email**: bugs@k24.app

### Feature Requests
- **Email**: features@k24.app
- **Discord**: #feature-requests channel

---

## 🔄 Updates

### Check for Updates
```bash
# Docker
docker-compose pull
docker-compose up -d

# Manual
git pull origin main
pip install -r requirements.txt
cd frontend && npm install
```

### Changelog
See `CHANGELOG.md` for version history

---

## 📚 Next Steps

1. **Watch Tutorial Videos**: [youtube.com/k24tutorials](https://youtube.com)
2. **Read Full Documentation**: [docs.k24.app](https://docs.k24.app)
3. **Join Community**: [discord.gg/k24](https://discord.gg/k24)
4. **Explore Features**: Try all voucher types
5. **Customize**: Set up your company details

---

## 🎉 Welcome to K24!

You're now ready to experience accounting at the speed of thought.

**Pro Tips**:
- Use AI chat for quick entries
- Download PDFs for client records
- Check Audit Dashboard weekly
- Enable notifications for sync errors

Happy accounting! 🚀

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**License**: Proprietary
