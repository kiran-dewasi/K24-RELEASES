# Tally AI Agent Backend (MVP)

## Overview
This project provides a backend-only MVP AI agent system for interacting with, auditing, and modifying Tally accounting data via natural language. It uses FastAPI, Gemini (LangChain), and Pandas, and works with Tally CSV/XLSX exports.

### Features
- Load Tally ledger/voucher exports with Pandas
- Conversational audit/question answering with Gemini (LangChain)
- CRUD operations and modification logging with undo support
- REST API endpoints for audit and modification
- **Live Tally sync integration** - Automatically sync ledger updates to TallyPrime via HTTP XML API
- Secure XML escaping and error handling
- Dry-run mode for testing without affecting Tally

## Directory Structure
- `/backend` — All Python logic, modularized

## Quickstart
1. **Install dependencies:**
   ```sh
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   pip install --upgrade pip
   pip install fastapi uvicorn pandas langchain-google-genai requests
   ```
2. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   TALLY_COMPANY=Your Company Name
   TALLY_URL=http://localhost:9000
   TALLY_LIVE_UPDATE_ENABLED=false  # Set to "true" to enable actual sync to Tally
   ```
3. **Run the API server:**
   ```sh
   uvicorn backend.api:app --reload
   ```
4. Use tools like Postman/curl to POST to `/audit` and `/modify` endpoints.

## Tally Live Update Integration

The backend includes secure integration with TallyPrime's HTTP XML API for live synchronization of ledger updates.

### Configuration

Set the following environment variables in your `.env` file:

- `TALLY_LIVE_UPDATE_ENABLED`: Set to `"true"` to enable actual sync to Tally, or `"false"` for dry-run mode (default)
- `TALLY_COMPANY`: Name of your Tally company
- `TALLY_URL`: Tally server URL (default: `http://localhost:9000`)

### Features

- **Automatic sync**: After successful ledger modifications via API, changes are automatically synced to Tally
- **Secure**: All user inputs are escaped to prevent XML injection
- **Robust error handling**: Proper logging and error reporting
- **Dry-run mode**: Test without affecting Tally by setting `TALLY_LIVE_UPDATE_ENABLED=false`
- **Extensible**: Easy to extend for vouchers and other entity types

### Testing

Run the test script to verify the integration:

```sh
python test_tally_live_update.py
```

This will:
1. Import sample XML data
2. Update a ledger entry
3. Verify the sync status (dry-run or actual sync)
4. Confirm the update in the dataframe

### Usage

When you update a ledger via the `/modify` endpoint, the response includes a `tally_sync` field showing the sync status:

```json
{
  "status": "success",
  "tally_sync": {
    "status": "skipped",
    "reason": "dry_run_mode",
    "message": "Tally live update is disabled"
  }
}
```

In dry-run mode, all sync attempts are logged but not executed. This allows you to test the integration safely before enabling actual sync.

## Development
Backend code is modularized in `/backend`. Add sample Tally CSV/XLSX data and extend logic as needed.

---
For detailed instructions, consult documentation (WIP).
