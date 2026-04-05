"""
test_security_fixes.py
======================
QA verification of 3 security fixes applied to the cloud-backend:

  Fix 1 — auth.py : all print() calls that leaked JWT/SECRET_KEY are removed.
  Fix 2 — routers/baileys.py : WhatsApp error responses are generic (no raw exception text).
  Fix 3 — routers/baileys.py : error_traceback.txt is never written to disk on failure.

Run:
    python tests/test_security_fixes.py [--base-url http://localhost:8001]
    python tests/test_security_fixes.py --help

Notes:
  • The script prompts for credentials if none are supplied via --email / --password.
  • Set BAILEYS_SECRET env var (or --baileys-secret) to the value configured on the server.
  • Static checks (grep-style) need the source tree present — run from repo root or cloud-backend/.
"""

import argparse
import getpass
import os
import re
import sys
import time
import pathlib
import json

# ── optional: try importing requests ─────────────────────────────────────────
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ─────────────────────────────────────────────────────────────────────────────
# Colour helpers (work on Windows with ANSI enabled)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def _pass(label: str, detail: str = ""):
    msg = f"{GREEN}[PASS]{RESET} {label}"
    if detail:
        msg += f"\n       {detail}"
    print(msg)

def _fail(label: str, evidence: str = ""):
    msg = f"{RED}[FAIL]{RESET} {label}"
    if evidence:
        msg += f"\n       {YELLOW}Evidence:{RESET} {evidence}"
    print(msg)

def _skip(label: str, reason: str = ""):
    msg = f"{YELLOW}[SKIP]{RESET} {label}"
    if reason:
        msg += f" — {reason}"
    print(msg)

def _section(title: str):
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'─'*60}{RESET}")

# ─────────────────────────────────────────────────────────────────────────────
# Sensitive pattern matchers
# ─────────────────────────────────────────────────────────────────────────────
JWT_PATTERN           = re.compile(r'eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+')
DEBUG_TOKEN_PATTERN   = re.compile(r'\[DEBUG\s*TOKEN\]', re.IGNORECASE)
SECRET_KEY_PATTERN    = re.compile(r'SECRET_KEY\s*(prefix|=|:)', re.IGNORECASE)
GOOGLE_KEY_PATTERN    = re.compile(r'AIza[0-9A-Za-z\-_]{10,}')
TRACEBACK_PATTERN     = re.compile(r'Traceback\s*\(most recent call last\)', re.IGNORECASE)
EXCEPTION_PATTERN     = re.compile(r'(^|\s)Exception:', re.MULTILINE)
FILE_FRAME_PATTERN    = re.compile(r'File ".*\.py",\s*line \d+')
RAW_ERROR_PATTERN     = re.compile(r'(^|\s)Error:\s', re.MULTILINE)

SENSITIVE_RESPONSE_PATTERNS = [
    (JWT_PATTERN,         "JWT token fragment (eyJ...)"),
    (DEBUG_TOKEN_PATTERN, "[DEBUG TOKEN] marker"),
    (SECRET_KEY_PATTERN,  "SECRET_KEY prefix"),
    (GOOGLE_KEY_PATTERN,  "Google API key (AIza...)"),
    (TRACEBACK_PATTERN,   "Python traceback"),
    (FILE_FRAME_PATTERN,  "stack frame (File '...' line N)"),
    (RAW_ERROR_PATTERN,   "raw Error: message"),
]

SENSITIVE_LOG_PATTERNS = [
    (DEBUG_TOKEN_PATTERN, "[DEBUG TOKEN] marker"),
    (SECRET_KEY_PATTERN,  "SECRET_KEY prefix"),
    (JWT_PATTERN,         "JWT fragment"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Locate source files
# ─────────────────────────────────────────────────────────────────────────────

def locate_source_files(base_dir: pathlib.Path):
    """Return (auth_py, baileys_py) or None if not found."""
    candidates = [
        base_dir,
        base_dir / "cloud-backend",
        base_dir.parent / "cloud-backend",
    ]
    for root in candidates:
        auth_py    = root / "auth.py"
        baileys_py = root / "routers" / "baileys.py"
        if auth_py.exists() and baileys_py.exists():
            return auth_py, baileys_py
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Locate backend log file
# ─────────────────────────────────────────────────────────────────────────────

def find_log_file() -> pathlib.Path | None:
    candidates = [
        pathlib.Path(os.getenv("APPDATA", ""), "k24", "logs", "backend.log"),
        pathlib.Path(os.getenv("LOCALAPPDATA", ""), "k24", "logs", "backend.log"),
        pathlib.Path.home() / ".k24" / "logs" / "backend.log",
        # uvicorn default in cloud-backend dir
        pathlib.Path(__file__).parent.parent / "backend.log",
        pathlib.Path(__file__).parent.parent / "logs" / "backend.log",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Result tracker
# ─────────────────────────────────────────────────────────────────────────────

class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def ok(self, label, detail=""):
        _pass(label, detail)
        self.passed += 1

    def fail(self, label, evidence=""):
        _fail(label, evidence)
        self.failed += 1

    def skip(self, label, reason=""):
        _skip(label, reason)
        self.skipped += 1

    def summary(self):
        total  = self.passed + self.failed
        skipped_note = f"  {self.skipped} skipped." if self.skipped else ""
        color  = GREEN if self.failed == 0 else RED
        print(f"\n{BOLD}{color}Results: {self.passed}/{total} passed. "
              f"{self.failed} failed.{RESET}{skipped_note}")


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC CHECKS (no running server required)
# ═══════════════════════════════════════════════════════════════════════════════

def run_static_checks(results: Results, auth_py: pathlib.Path, baileys_py: pathlib.Path):
    _section("STATIC SOURCE SCANS")

    # ── Static 1: auth.py — no sensitive print() calls ──────────────────────
    label = "Static 1 — auth.py has no sensitive print() calls"
    SENSITIVE_PRINT = re.compile(
        r'\bprint\s*\(.*?(token|key|secret|SECRET|JWT|eyJ)',
        re.IGNORECASE
    )
    hits = []
    for lineno, line in enumerate(auth_py.read_text(encoding="utf-8").splitlines(), 1):
        if SENSITIVE_PRINT.search(line):
            hits.append(f"L{lineno}: {line.strip()}")

    if not hits:
        results.ok(label)
    else:
        results.fail(label, "\n       ".join(hits))

    # ── Static 2: baileys.py — str(e) not returned in response dict ──────────
    label = "Static 2 — baileys.py does not expose str(e) in response"
    # Pattern: str(e) inside a dict that is returned / in reply_message value
    STR_E_IN_RETURN = re.compile(r'(reply_message|"error"|return).*?\bstr\(e\)', re.IGNORECASE)
    hits = []
    for lineno, line in enumerate(baileys_py.read_text(encoding="utf-8").splitlines(), 1):
        if STR_E_IN_RETURN.search(line):
            hits.append(f"L{lineno}: {line.strip()}")

    if not hits:
        results.ok(label)
    else:
        results.fail(label, "\n       ".join(hits))

    # ── Static 3: baileys.py — no error_traceback.txt file writes ────────────
    label = "Static 3 — baileys.py does not write error_traceback.txt"
    TRACEBACK_FILE = re.compile(r'open\s*\(.*?error_traceback', re.IGNORECASE)
    hits_tb = []
    for lineno, line in enumerate(baileys_py.read_text(encoding="utf-8").splitlines(), 1):
        if TRACEBACK_FILE.search(line):
            hits_tb.append(f"L{lineno}: {line.strip()}")

    if not hits_tb:
        results.ok(label)
    else:
        results.fail(label, "\n       ".join(hits_tb))

    # ── Static 4: baileys.py — user-facing exception paths use exc_info=True ──
    label = "Static 4 — baileys.py user-facing error paths use logger.error(exc_info=True)"
    # Strategy: parse each except block's *own* body (lines at deeper indent).
    # Only flag if the block body itself returns {"status":...,"reply_message":...}
    # AND lacks exc_info=True. Internal blocks (cleanup, DB infra) are exempt.
    content = baileys_py.read_text(encoding="utf-8")
    lines   = content.splitlines()
    logger_error_exc   = re.compile(r'logger\.error\(.*exc_info\s*=\s*True')
    user_facing_return = re.compile(r'return\s*\{[^}]*(status|reply_message)')

    missing = []
    for m in re.finditer(r'except Exception', content):
        char_pos   = m.start()
        except_ln  = content[:char_pos].count('\n')  # 0-indexed line of 'except'
        except_indent = len(lines[except_ln]) - len(lines[except_ln].lstrip())

        # Collect only the lines that belong to this except body (deeper indent)
        body_lines = []
        for ln in lines[except_ln + 1: except_ln + 20]:
            stripped = ln.lstrip()
            if not stripped:           # blank lines are ok inside block
                continue
            cur_indent = len(ln) - len(stripped)
            if cur_indent <= except_indent:
                break                  # back to same or shallower indent — block ended
            body_lines.append(ln)

        body_text = "\n".join(body_lines)
        is_user_facing = bool(user_facing_return.search(body_text))
        has_exc_info   = bool(logger_error_exc.search(body_text))

        if is_user_facing and not has_exc_info:
            missing.append(f"L{except_ln+1}: {lines[except_ln].strip()}")

    if not missing:
        results.ok(label, "All user-facing error handlers use exc_info=True.")
    else:
        results.fail(label,
            f"{len(missing)} user-facing except block(s) missing logger.error(exc_info=True):\n       "
            + "\n       ".join(missing))


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE TESTS (require running backend)
# ═══════════════════════════════════════════════════════════════════════════════

def check_server_alive(base_url: str) -> bool:
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def run_live_tests(
    results: Results,
    base_url: str,
    email: str,
    password: str,
    baileys_secret: str,
):
    _section("LIVE HTTP TESTS")

    if not HAS_REQUESTS:
        results.skip("Live tests", "requests library not installed — run: pip install requests")
        return

    if not check_server_alive(base_url):
        results.skip("Live tests", f"Backend not reachable at {base_url}")
        return

    # ── figure out log file snapshot BEFORE login ─────────────────────────────
    log_file   = find_log_file()
    log_before = None
    if log_file:
        print(f"  ℹ Log file found: {log_file}")
        try:
            log_before = log_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    else:
        print("  ⚠ Backend log file not found — log content check will be skipped.")

    # ────────────────────────────────────────────────────────────────────────
    # Live Test 1 — JWT / SECRET_KEY not in logs during login
    # ────────────────────────────────────────────────────────────────────────
    label_t1 = "Live 1 — No JWT/SECRET_KEY leak in backend logs during login"

    login_ok   = False
    login_resp = None
    try:
        login_resp = requests.post(
            f"{base_url}/api/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )
        login_ok = login_resp.status_code == 200
        if login_ok:
            print(f"  ✔ Login HTTP {login_resp.status_code}")
        else:
            print(f"  ⚠ Login returned HTTP {login_resp.status_code} — {login_resp.text[:200]}")
    except Exception as exc:
        print(f"  ✖ Login request failed: {exc}")

    if log_file and log_before is not None:
        try:
            time.sleep(0.5)  # let logger flush
            log_after = log_file.read_text(encoding="utf-8", errors="replace")
            new_lines  = log_after[len(log_before):]

            bad_hits = []
            for pat, desc in SENSITIVE_LOG_PATTERNS:
                for m in pat.finditer(new_lines):
                    # Get surrounding context (up to 120 chars)
                    start = max(0, m.start() - 20)
                    snippet = new_lines[start: m.end() + 40].replace('\n', ' ')
                    bad_hits.append(f"{desc}: ...{snippet}...")

            if bad_hits:
                results.fail(label_t1, "\n       ".join(bad_hits))
            else:
                results.ok(label_t1, "No sensitive patterns in new log lines.")
        except Exception as exc:
            results.skip(label_t1, f"Could not read log file after request: {exc}")
    else:
        results.skip(label_t1, "No log file found — cannot verify log content.")

    # ────────────────────────────────────────────────────────────────────────
    # Live Test 2 — WhatsApp error response is generic (no raw exception)
    # ────────────────────────────────────────────────────────────────────────
    label_t2 = "Live 2 — WhatsApp /process returns generic error (no raw exception)"

    # We trigger a deliberate failure by omitting 'sender_phone' (validation error)
    # and also by sending an invalid payload that should reach the exception path.
    # We send with correct secret so it gets past auth, but bad data to cause an error.
    try:
        trigger_payload = {
            "sender_phone": "BAD_TRIGGER_TEST_" + str(int(time.time())),
            "message_text": "__SECURITY_TEST_TRIGGER__",
        }
        headers = {"X-Baileys-Secret": baileys_secret}
        resp_t2 = requests.post(
            f"{base_url}/api/baileys/process",
            json=trigger_payload,
            headers=headers,
            timeout=20,
        )
        body_text = resp_t2.text

        # Try to parse JSON for structured check
        try:
            body_json = resp_t2.json()
        except Exception:
            body_json = {}

        reply       = body_json.get("reply_message", body_text)
        error_field = body_json.get("error", "")

        bad_fields = []
        for pat, desc in SENSITIVE_RESPONSE_PATTERNS:
            for field_name, field_val in [("reply_message", reply), ("error", error_field), ("body", body_text)]:
                if pat.search(str(field_val)):
                    snippet = str(field_val)[:300]
                    bad_fields.append(f"{desc} in '{field_name}': {snippet!r}")

        # Also explicitly check for "Exception" keyword in reply
        if "Exception" in reply:
            bad_fields.append(f"'Exception' keyword in reply_message: {reply[:300]!r}")

        if bad_fields:
            results.fail(label_t2, "\n       ".join(bad_fields))
        else:
            # Positive check: should contain "went wrong" or "ref:" in some error path
            safe_phrase_ok = (
                "went wrong" in reply.lower()
                or "ref:" in reply.lower()
                or resp_t2.status_code in (401, 403)  # rejected at auth level is also safe
                or body_json.get("status") in ("success", "error")  # normal flow
            )
            detail = f"HTTP {resp_t2.status_code} | reply: {reply[:120]!r}"
            if safe_phrase_ok:
                results.ok(label_t2, detail)
            else:
                results.fail(label_t2,
                    f"Response lacks expected safe phrase ('went wrong'/'ref:'): {detail}")
    except Exception as exc:
        results.skip(label_t2, f"Request failed: {exc}")

    # ────────────────────────────────────────────────────────────────────────
    # Live Test 3 — error_traceback.txt NOT created/modified on failure
    # ────────────────────────────────────────────────────────────────────────
    label_t3 = "Live 3 — error_traceback.txt not created/modified on failure"

    # Common locations the old code might have written this
    TRACEBACK_FILE_CANDIDATES = [
        pathlib.Path.cwd() / "error_traceback.txt",
        pathlib.Path(__file__).parent.parent / "error_traceback.txt",
        pathlib.Path(__file__).parent / "error_traceback.txt",
    ]

    snapshot_before: dict[str, float] = {}
    for p in TRACEBACK_FILE_CANDIDATES:
        if p.exists():
            snapshot_before[str(p)] = p.stat().st_mtime

    # Trigger failure (same as test 2 but explicitly stress-test the error path)
    try:
        headers = {"X-Baileys-Secret": baileys_secret}
        requests.post(
            f"{base_url}/api/baileys/process",
            json={
                "sender_phone": "ERROR_PATH_TEST_" + str(int(time.time())),
                "message_text": "__FORCE_ERROR_PATH__",
            },
            headers=headers,
            timeout=20,
        )
        time.sleep(0.5)  # let any async file write flush
    except Exception:
        pass

    created_or_modified = []
    for p in TRACEBACK_FILE_CANDIDATES:
        if p.exists():
            prev_mtime = snapshot_before.get(str(p))
            cur_mtime  = p.stat().st_mtime
            if prev_mtime is None:
                created_or_modified.append(f"CREATED: {p} (at {cur_mtime})")
            elif cur_mtime != prev_mtime:
                created_or_modified.append(f"MODIFIED: {p} (before={prev_mtime}, after={cur_mtime})")

    if created_or_modified:
        results.fail(label_t3, "\n       ".join(created_or_modified))
    else:
        results.ok(label_t3, "error_traceback.txt was not created or modified.")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Security fix QA tests for cloud-backend"
    )
    parser.add_argument("--base-url",      default="http://localhost:8001",
                        help="Backend base URL (default: http://localhost:8001)")
    parser.add_argument("--email",         default="",
                        help="Login email for Test 1 (prompted if omitted)")
    parser.add_argument("--password",      default="",
                        help="Login password for Test 1 (prompted if omitted)")
    parser.add_argument("--baileys-secret",
                        default=os.getenv("BAILEYS_SECRET", "k24_baileys_secret"),
                        help="X-Baileys-Secret header value (default: k24_baileys_secret)")
    parser.add_argument("--static-only",   action="store_true",
                        help="Run only static source checks (no server needed)")
    parser.add_argument("--source-dir",    default="",
                        help="Path to cloud-backend/ directory (auto-detected if omitted)")
    args = parser.parse_args()

    print(f"\n{BOLD}K24 Security Fix QA — {time.strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"  Backend: {args.base_url}")
    print(f"  Static-only: {args.static_only}")

    results = Results()

    # ── Locate source files ───────────────────────────────────────────────────
    here = pathlib.Path(args.source_dir) if args.source_dir else pathlib.Path(__file__).parent.parent
    auth_py, baileys_py = locate_source_files(here)

    if auth_py and baileys_py:
        print(f"  auth.py    : {auth_py}")
        print(f"  baileys.py : {baileys_py}")
        run_static_checks(results, auth_py, baileys_py)
    else:
        _section("STATIC SOURCE SCANS")
        results.skip("All static checks", f"Source files not found under {here}")

    # ── Live tests ────────────────────────────────────────────────────────────
    if not args.static_only:
        email    = args.email    or input("\n  Login Email: ").strip()
        password = args.password or getpass.getpass("  Login Password: ")
        run_live_tests(
            results,
            base_url=args.base_url,
            email=email,
            password=password,
            baileys_secret=args.baileys_secret,
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    results.summary()
    sys.exit(0 if results.failed == 0 else 1)


if __name__ == "__main__":
    main()
