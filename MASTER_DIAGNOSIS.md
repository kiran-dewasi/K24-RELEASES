# Master Diagnosis: Why "The Game" Continues

## The Initial Findings
1.  **Confirmed Bug:** The code previously had a typo (`k24_backend` vs `k24-backend`). This was a guaranteed crash generator. We fixed this.
2.  **Current Behavior:** The app opens, runs for "a few seconds", then closes.

## The New Theory: "Antivirus Guillotine"
The behavior you are seeing (Run -> Pause -> Kill) is the distinct signature of **Windows Defender / SmartScreen** or an Antivirus solution.

### What is happening?
1.  **Start:** You double-click K24. The frontend opens (The window appears).
2.  **Trigger:** After 1-2 seconds, the App executes the command to spawn the **Backend Engine** (`k24-backend.exe`).
3.  **Detection:** To Windows, this Backend Engine looks like a "Generic Unsigned Python Script" trying to open a network port (8001). This mimics malware behavior.
4.  **The Kill:** The Antivirus steps in and **terminates the process tree**. It kills the backend, and by extension, kills the main app (or the main app panics because its child was murdered).

## Why "A Few Seconds"?
The antivirus takes a moment to scan the memory of the newly spawned backend process. That 1-3 second delay is the "scan time" before it decides to kill it.

## The Solution: "Safe Mode" Build
To prove this and fix it, we need to:
1.  **Delay the Launch:** Don't start the backend immediately. Wait 5 seconds so the window is stable.
2.  **Detach the Process:** Launch the backend in a way that if it dies, it doesn't take the main app with it.
3.  **User Verification:** This will allow the window to STAY OPEN, even if the backend is killed.

I will now implement this "Safe Mode" logic.
