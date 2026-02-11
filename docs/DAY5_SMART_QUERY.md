# Day 5 Implementation: Smart Query Orchestrator

**Status: ✅ COMPLETE**  
**Date: January 28, 2026**

## Overview

Day 5 focused on building the **Smart Query Orchestrator** - an intelligent system that:
1. Understands natural language queries from users (WhatsApp or Web)
2. Pulls ONLY relevant data from Tally/SQLite
3. Returns concise, actionable responses
4. Generates Tally Prime-style PDF/Excel files when requested

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Query (WhatsApp/Web)                   │
│                "How much does ABC Corp owe?"                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Query Orchestrator                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. Parse Query → Detect Intent + Extract Entities      │    │
│  │     Intent: OUTSTANDING, Entities: {party: "ABC Corp"}  │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  2. Route to Handler → Pull ONLY Relevant Data          │    │
│  │     Query Bills table for ABC Corp pending amount       │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  3. Format Response → Concise, WhatsApp-Ready           │    │
│  │     📊 ABC Corp - Outstanding Summary                   │    │
│  │     💰 Total Due: ₹45,000                               │    │
│  │     📋 Top Bills: ...                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Response to User                            │
│  Text + Optional PDF/Excel File                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Files Created/Modified

### New Files
| File | Purpose |
|------|---------|
| `backend/services/query_orchestrator.py` | Main orchestration logic with intent detection and handlers |
| `backend/services/export_service.py` | PDF and Excel generation for invoices, statements, reports |
| `backend/routers/query.py` | API endpoints for web and WhatsApp queries |

### Modified Files
| File | Changes |
|------|---------|
| `backend/services/__init__.py` | Export new services |
| `backend/routers/__init__.py` | Export query router |
| `backend/api.py` | Register query router |
| `requirements.txt` | Add reportlab, openpyxl |

## Supported Query Types

### 1. Outstanding & Payments
```
"How much does ABC Corp owe?"
"Outstanding from XYZ Industries"
"ABC Corp payment history this month"
"Show overall outstanding"
```

### 2. Stock & Inventory
```
"Stock of Product A"
"What's the rate of Product B?"
"Inventory summary"
```

### 3. Sales & Purchases
```
"January sales summary"
"This month's sales"
"Top 10 customers"
"Best selling items"
```

### 4. Reports & Exports
```
"Export January sales to Excel"
"Send invoice INV-001 as PDF"
"ABC Corp statement PDF"
"Stock report Excel"
```

### 5. Invoices & Vouchers
```
"Show invoice INV-001"
"Last 5 sales"
"Recent purchase vouchers"
```

### 6. Cash & Balance
```
"Cash balance today"
"Cash book status"
```

## API Endpoints

### POST /api/query/ask
Main query endpoint for web interface.

**Request:**
```json
{
  "query": "How much does ABC Corp owe?",
  "format": "text"
}
```

**Response:**
```json
{
  "success": true,
  "intent": "outstanding",
  "confidence": 0.95,
  "response_text": "📊 **ABC Corp** - Outstanding Summary\n...",
  "data": {...},
  "has_file": false,
  "suggestions": ["Payment history of ABC Corp", "Send ABC Corp statement as PDF"]
}
```

### POST /api/query/whatsapp
Optimized endpoint for WhatsApp (via Baileys).

**Request:**
```json
{
  "query": "Export sales to Excel"
}
```

**Response:**
```json
{
  "success": true,
  "message": "📊 Sales Register Excel generated!\n\n📁 File: Sales_Register_20260128.xlsx",
  "has_file": true,
  "file": {
    "path": "/exports/Sales_Register_20260128.xlsx",
    "filename": "Sales_Register_20260128.xlsx",
    "type": "excel"
  }
}
```

### GET /api/query/download/{filename}
Download exported files.

### GET /api/query/supported
Get list of supported query types with examples.

## Export Service Features

### PDF Generation
- **Invoice PDF**: Professional invoice matching Tally format
- **Statement PDF**: Outstanding statement for a party with aging

### Excel Generation
- **Sales Register**: Date-range filtered sales with totals
- **Purchase Register**: Date-range filtered purchases
- **Outstanding Report**: Receivables or Payables with balance
- **Stock Report**: All items with stock and rates

## Integration with Baileys (WhatsApp)

The Baileys listener should call `/api/query/whatsapp` for natural language queries:

```javascript
// In baileys-listener/listener.js

async function handleNaturalLanguageQuery(message) {
  const response = await fetch('http://localhost:8000/api/query/whatsapp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: message.text })
  });
  
  const result = await response.json();
  
  // Send text response
  await sock.sendMessage(sender, { text: result.message });
  
  // If file was generated, send it
  if (result.has_file) {
    await sock.sendMessage(sender, {
      document: { url: result.file.path },
      fileName: result.file.filename,
      mimetype: result.file.type === 'pdf' 
        ? 'application/pdf' 
        : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });
  }
}
```

## Key Design Decisions

1. **Concise Responses**: Show top 3 items, not all 100
2. **Smart Entity Extraction**: Regex patterns for party names, items, dates
3. **Date Range Parsing**: Understands "January", "this month", "last month"
4. **Follow-up Suggestions**: After each response, suggest related queries
5. **Local File Generation**: PDF/Excel saved locally (desktop app)

## Testing

```bash
# Test query parsing
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "How much does ABC Corp owe?"}'

# Test Excel export
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Export January sales to Excel"}'

# Get supported queries
curl http://localhost:8000/api/query/supported
```

## Next Steps

1. **Enhance PDF Templates**: Match Tally invoice blueprints
2. **Add Voice Processing**: Convert voice to text query
3. **Improve Entity Extraction**: Use AI for fuzzy matching
4. **Add Caching**: Cache frequent queries
5. **Multi-language Support**: Hindi query support
