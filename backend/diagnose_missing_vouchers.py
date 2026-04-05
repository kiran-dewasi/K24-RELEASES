"""
diagnose_missing_vouchers.py
=============================
Standalone diagnostic: compares raw Tally voucher list vs. local DB.

Run from the backend/ directory:
    python diagnose_missing_vouchers.py

Output:
  - Every voucher Tally has (raw)
  - Which ones are missing from DB
  - Which ones are present but soft-deleted/DELETED
  - Any duplicates in DB that might block insertion
"""

import sys, os

# ── ensure imports find local modules ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))          # CWD = backend/

from datetime import datetime, timedelta
from sqlalchemy import create_engine, cast, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import Date

from database import get_db_path, Voucher
from tally_connector import TallyConnector

# ── Config ─────────────────────────────────────────────────────────────────────
TENANT_ID   = "TENANT-2965AF26"          # change if needed
DAYS_BACK   = 30                          # widen if needed

# ── DB setup ───────────────────────────────────────────────────────────────────
db_path = get_db_path()
engine  = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
db      = Session()

# ── Date range ─────────────────────────────────────────────────────────────────
to_date   = datetime.now()
from_date = to_date - timedelta(days=DAYS_BACK)
from_str  = from_date.strftime("%Y%m%d")
to_str    = to_date.strftime("%Y%m%d")

print("=" * 70)
print(f"DIAGNOSTIC: Missing Vouchers")
print(f"Tenant  : {TENANT_ID}")
print(f"Range   : {from_str} → {to_str}  ({DAYS_BACK} days)")
print(f"DB path : {db_path}")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. FETCH FROM TALLY (raw)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1] Fetching from Tally...")
try:
    tc = TallyConnector()
    print(f"    Company detected: {tc.company_name!r}")
    df = tc.fetch_vouchers(from_date=from_str, to_date=to_str)
    tally_rows = df.to_dict("records") if not df.empty else []
    print(f"    Tally returned  : {len(tally_rows)} vouchers")
except Exception as e:
    print(f"    ❌ Tally connection failed: {e}")
    tally_rows = []

# Print every tally voucher (most recent 20 + first 5 to bound output)
print(f"\n    ── ALL {len(tally_rows)} RAW TALLY VOUCHERS ──")
for i, v in enumerate(tally_rows, 1):
    vnum   = v.get("voucher_number") or v.get("VOUCHERNUMBER", "")
    vtype  = v.get("voucher_type")   or v.get("VOUCHERTYPENAME", "")
    vdate  = v.get("date")           or v.get("DATE", "")
    party  = v.get("party_name")     or v.get("PARTYLEDGERNAME", "")
    amount = v.get("amount")         or v.get("AMOUNT", "")
    guid   = v.get("guid")           or v.get("GUID", "")
    print(f"    [{i:>3}] {vdate:<12} {vtype:<20} #{vnum:<12} {party:<25} ₹{amount}  guid={guid!r}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. FETCH FROM DB
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[2] Fetching from local DB (tenant={TENANT_ID})...")
db_vouchers = db.query(Voucher).filter(
    Voucher.tenant_id == TENANT_ID,
    Voucher.date >= from_date,
    Voucher.date <= to_date,
).order_by(Voucher.date.desc()).all()

print(f"    DB returned: {len(db_vouchers)} vouchers (including soft-deleted)\n")
print(f"    ── ALL DB VOUCHERS IN RANGE ──")
for v in db_vouchers:
    deleted_flag = "🗑️ DELETED(soft)" if v.is_deleted else (
                   "⚠️ DELETED(sync)" if v.sync_status == "DELETED" else "✅ active")
    print(
        f"    {deleted_flag:<22} {str(v.date.date()):<12} {v.voucher_type:<20} "
        f"#{v.voucher_number or '':<12} {v.party_name or '':<25} "
        f"₹{v.amount}  guid={v.guid!r}"
    )

# ═══════════════════════════════════════════════════════════════════════════════
# 3. DIFF: Which Tally vouchers are NOT in DB?
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[3] Diffing Tally vs DB...")

db_guids        = {v.guid for v in db_vouchers if v.guid}
db_composites   = {
    f"{v.voucher_number}|{v.voucher_type}|{v.date.date()}"
    for v in db_vouchers if v.voucher_number
}

missing = []
for v in tally_rows:
    vnum  = v.get("voucher_number") or v.get("VOUCHERNUMBER", "") or ""
    vtype = v.get("voucher_type")   or v.get("VOUCHERTYPENAME", "") or ""
    vdate_raw = str(v.get("date") or v.get("DATE", "") or "").strip()
    guid  = v.get("guid")           or v.get("GUID", "") or ""

    try:
        if len(vdate_raw) == 8 and vdate_raw.isdigit():
            vd = datetime.strptime(vdate_raw, "%Y%m%d").date()
        elif len(vdate_raw) == 10 and "-" in vdate_raw:
            vd = datetime.strptime(vdate_raw, "%Y-%m-%d").date()
        else:
            vd = None
    except Exception:
        vd = None

    in_db_by_guid      = guid and guid in db_guids
    composite           = f"{vnum}|{vtype}|{vd}" if vd else None
    in_db_by_composite  = composite and composite in db_composites

    if not in_db_by_guid and not in_db_by_composite:
        missing.append(v)

if missing:
    print(f"\n    🚨 {len(missing)} Tally vouchers NOT found in DB:")
    for v in missing:
        print(f"       • date={v.get('date') or v.get('DATE')}  type={v.get('voucher_type') or v.get('VOUCHERTYPENAME')}  "
              f"num={v.get('voucher_number') or v.get('VOUCHERNUMBER')}  "
              f"party={v.get('party_name') or v.get('PARTYLEDGERNAME')}  "
              f"guid={v.get('guid') or v.get('GUID')!r}")
else:
    print("    ✅ All Tally vouchers found in DB — issue may be in API query (filter/tenant mismatch)")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. Check for soft-deleted versions of the missing ones
# ═══════════════════════════════════════════════════════════════════════════════
if missing:
    print(f"\n[4] Checking if missing vouchers exist as soft-deleted rows...")
    for v in missing:
        vnum  = v.get("voucher_number") or v.get("VOUCHERNUMBER", "") or ""
        vtype = v.get("voucher_type")   or v.get("VOUCHERTYPENAME", "") or ""
        guid  = v.get("guid")           or v.get("GUID", "") or ""

        # Check all rows for this tenant (ignoring date / is_deleted)
        candidates = db.query(Voucher).filter(Voucher.tenant_id == TENANT_ID)
        if guid:
            candidates = candidates.filter(Voucher.guid == guid)
        elif vnum:
            candidates = candidates.filter(
                Voucher.voucher_number == vnum,
                Voucher.voucher_type == vtype,
            )
        rows = candidates.all()

        if rows:
            for r in rows:
                print(
                    f"    ⚠️  Found a row for #{vnum} but "
                    f"is_deleted={r.is_deleted}, sync_status={r.sync_status!r}, "
                    f"date={r.date}, guid={r.guid!r}"
                )
        else:
            print(f"    ❌ #{vnum} ({vtype}) GUID={guid!r} — zero rows in DB for this tenant")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. Unique-constraint collision check: duplicate GUIDs in DB
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n[5] Checking for GUID collision in DB (uq_voucher_tenant_guid)...")
dup_check = db.execute(text("""
    SELECT guid, COUNT(*) as cnt
    FROM vouchers
    WHERE tenant_id = :tid AND guid IS NOT NULL AND guid != ''
    GROUP BY guid
    HAVING cnt > 1
    ORDER BY cnt DESC
    LIMIT 20
"""), {"tid": TENANT_ID}).fetchall()

if dup_check:
    print(f"    🚨 {len(dup_check)} GUIDs with duplicates (should be 0, unique constraint):")
    for row in dup_check:
        print(f"       guid={row[0]!r}  count={row[1]}")
else:
    print("    ✅ No duplicate GUIDs found")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. "SYNC-" fallback GUIDs that may collide
# ═══════════════════════════════════════════════════════════════════════════════
sync_guids = db.execute(text("""
    SELECT guid, voucher_number, voucher_type, date
    FROM vouchers
    WHERE tenant_id = :tid AND guid LIKE 'SYNC-%'
    ORDER BY date DESC
    LIMIT 20
"""), {"tid": TENANT_ID}).fetchall()

if sync_guids:
    print(f"\n[6] Found {len(sync_guids)} vouchers with fallback SYNC- GUIDs:")
    for row in sync_guids:
        print(f"       guid={row[0]!r}  num={row[1]}  type={row[2]}  date={row[3]}")
else:
    print(f"\n[6] No SYNC- fallback GUIDs in DB (good)")

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
db.close()
