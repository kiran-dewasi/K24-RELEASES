# 🚀 K24 Launch Plan - December 1st

**Objective**: Launch a "Local-First" Desktop App MVP by Dec 1st.
**Strategy**: Package the app as a simple installer that runs locally on the user's machine, connecting to their local Tally instance.

---

## ✅ Completed Readiness Tasks (Nov 28)

1.  **Onboarding Wizard**:
    -   New users are greeted with a "Welcome" screen.
    -   They can enter their **Tally URL** (default `localhost:9000`) and **Company Name**.
    -   They can enter their **Gemini API Key** (required for AI).
    -   Configuration is saved to `k24_config.json`.

2.  **Simplified Architecture**:
    -   Removed dependency on **Redis** (Context now uses in-memory fallback).
    -   Removed dependency on **Prefect** (Workflows run directly).
    -   App is now fully self-contained (Python + Node.js).

3.  **One-Click Launcher**:
    -   `install_dependencies.bat`: Installs Python/Node libs.
    -   `start_k24.bat`: Starts Backend & Frontend and opens the browser.

---

## 📅 Timeline (Next 48 Hours)

### **Friday, Nov 29 (Tomorrow)**
1.  **Testing**:
    -   Run the `install_dependencies.bat` on a fresh machine (or simulated env).
    -   Verify the Onboarding Flow end-to-end.
    -   Test "Chat" with a fresh API Key.
2.  **Packaging**:
    -   Create a `K24_Installer.zip` containing:
        -   `backend/`
        -   `frontend/`
        -   `requirements.txt`
        -   `install_dependencies.bat`
        -   `start_k24.bat`
        -   `README.txt` (Instructions)
3.  **Demo Video**:
    -   Record a 60-second video showing: Installation -> Onboarding -> "Show me outstanding bills" -> "Create Receipt".

### **Saturday, Nov 30**
1.  **Beta Distribution**:
    -   Upload Zip to Google Drive / WeTransfer.
    -   Send link to initial testers.

### **Sunday, Dec 1**
1.  **LAUNCH DAY** 🚀
    -   Gather feedback.
    -   Fix immediate bugs.

---

## 📝 User Instructions (Draft for README)

1.  **Prerequisites**:
    -   Install **Python** (3.10+).
    -   Install **Node.js** (18+).
    -   **Tally Prime** must be running with "Enable ODBC" on port 9000.

2.  **Installation**:
    -   Unzip the folder.
    -   Double-click `install_dependencies.bat` (Only once).

3.  **Running K24**:
    -   Double-click `start_k24.bat`.
    -   The app will open in your browser.
    -   Follow the setup wizard to connect Tally.

---

**Status**: READY FOR TESTING.
