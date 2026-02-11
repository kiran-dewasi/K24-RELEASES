# KITTU AI Agent Specifications

## 🧠 The Brain: Gemini 2.0 Flash
KITTU is powered by **Google's Gemini 2.0 Flash**, a state-of-the-art multimodal model designed for speed and efficiency.

### **Why Flash?**
- **Speed**: Sub-second response times for instant voice interactions.
- **Cost**: Extremely efficient, allowing for high-volume usage without breaking the bank.
- **Reasoning**: Sufficiently powerful to understand complex accounting intents ("Create a receipt for Sharma but date it yesterday").

---

## ⚡ Capabilities

### **1. Intent Recognition**
The agent classifies your natural language into **9 specific accounting actions**:
- `CREATE_RECEIPT` ("Received money from...")
- `CREATE_PAYMENT` ("Paid electricity bill...")
- `CREATE_SALE` ("Bill to Sharma...")
- `CREATE_PURCHASE` ("Bought goods from...")
- `QUERY_DATA` ("Show me outstanding bills")
- `GENERATE_REPORT` ("Give me the P&L")
- `RECONCILE_INVOICES` ("Match these payments")
- `UPDATE_GSTIN` ("Update GST for ABC")
- `UPDATE_LEDGER` ("Change address for XYZ")

### **2. Smart Entity Extraction**
It doesn't just understand *what* you want, but *details*:
- **Party Names**: Extracts "Sharma Traders" from "Sharma".
- **Amounts**: Understands "5k", "5000", "5 thousand".
- **Dates**: "Yesterday", "Last Friday", "25th Oct".

### **3. Context Awareness**
The agent knows **where you are** in the app:
- If you are on the **Cash Book** page and ask "What is the balance?", it answers about *Cash*.
- If you are on **Sharma's Contact** page, it answers about *Sharma*.

### **4. Navigation Director**
It acts as a "Director", routing you to the exact screen you need:
- "Create receipt" → Opens `/vouchers/new/receipt`
- "Show daybook" → Opens `/daybook`

---

## 🚧 Limitations & Constraints

### **1. Domain Restriction**
- **Scope**: The agent is strictly prompted to act as an **Accounting Assistant**.
- **Limit**: It will refuse or be confused by non-accounting queries (e.g., "Write a poem", "What is the capital of France"). This is a feature, not a bug, to prevent hallucinations.

### **2. Data Dependency**
- **Tally**: The agent is **blind** without Tally. It cannot "guess" your ledger names. It *must* query Tally to confirm if "Sharma" exists.
- **Offline**: If the backend cannot reach Tally, the agent's "Smart Lookup" features will fail (though basic chat might work).

### **3. Context Window**
- **Session Memory**: The agent remembers your current session's conversation (stored in Redis).
- **Limit**: It generally looks back at the last **10-20 turns** of conversation. It won't remember what you said 3 days ago unless it was saved to the database.

### **4. Rate Limits**
- **API Quotas**: Dependent on the Google Gemini API key used.
- **Typical Limit**: ~60 requests per minute (RPM) for the free tier, much higher for paid.
- **User Limit**: For a single user, you can chat continuously without hitting limits under normal use.

---

## 📊 Technical Specs

| Component | Specification |
|-----------|---------------|
| **Model** | `gemini-2.0-flash-exp` |
| **Temperature** | `0.1` (Low creativity, high precision) |
| **Max Tokens** | `500` (Concise responses) |
| **Latency** | ~800ms - 1.2s (End-to-end) |
| **Memory** | Redis-backed Session History |
| **Framework** | LangChain + FastAPI |

---

## 💡 Pro Tips for Best Results

1.  **Be Specific**: "Receipt from Sharma 5000" is better than just "Receipt".
2.  **Use Natural Language**: You don't need robot speak. "I got 5k from Sharma today" works perfectly.
3.  **Correction**: If it gets it wrong, just say "No, make it 6000". The agent supports **Draft Editing**.
