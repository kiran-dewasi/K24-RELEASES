import hashlib
import hmac
import json
import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)

VALID_WEBHOOK_SECRET = "test_razorpay_webhook_secret_12345"
INVALID_WEBHOOK_SECRET = "wrong_secret"


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeTable:
    def __init__(self, client, name: str):
        self.client = client
        self.name = name
        self.action = None
        self.payload = None
        self.filters = []

    def select(self, *args, **_kwargs):
        self.action = "select"
        self.payload = args[0] if args else "*"
        return self

    def update(self, payload=None, *_args, **_kwargs):
        self.action = "update"
        self.payload = payload or {}
        return self

    def insert(self, payload=None, *_args, **_kwargs):
        self.action = "insert"
        self.payload = payload or {}
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def _matches(self, row):
        return all(row.get(field) == value for field, value in self.filters)

    def execute(self):
        rows = self.client.state.setdefault(self.name, [])

        if self.action == "select":
            return FakeResult([row.copy() for row in rows if self._matches(row)])

        if self.action == "update":
            updated = []
            for row in rows:
                if self._matches(row):
                    row.update(self.payload)
                    updated.append(row.copy())
            return FakeResult(updated)

        if self.action == "insert":
            new_row = self.payload.copy()
            if "id" not in new_row:
                new_row["id"] = self.client.next_id(self.name)
            rows.append(new_row)
            return FakeResult([new_row.copy()])

        return FakeResult([])


class FakeSupabase:
    def __init__(self, state=None):
        self.state = state or {}
        self._id_counters = {}

    def next_id(self, table_name: str) -> str:
        self._id_counters[table_name] = self._id_counters.get(table_name, 0) + 1
        return f"{table_name}_{self._id_counters[table_name]}"

    def table(self, name: str):
        return FakeTable(self, name)

    def table_rows(self, name: str):
        return self.state.setdefault(name, [])


def _sign_payload(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def _make_payload(event: str) -> bytes:
    payload = {
        "event": event,
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_123",
                    "notes": {
                        "tenant_id": "tenant_123",
                        "plan_id": "plan_123",
                        "subscription_id": "sub_123",
                    },
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_123",
                    "notes": {
                        "tenant_id": "tenant_123",
                        "plan_id": "plan_123",
                        "subscription_id": "sub_123",
                    },
                }
            },
            "order": {
                "entity": {
                    "id": "order_123",
                    "notes": {
                        "tenant_id": "tenant_123",
                        "plan_id": "plan_123",
                        "subscription_id": "sub_123",
                    },
                }
            },
        },
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _base_state(subscription_status="pending", tenant_status="trial", include_cycle=False, include_summary=False):
    state = {
        "plans": [
            {
                "id": "plan_123",
                "max_credits_per_cycle": 100,
            }
        ],
        "subscriptions": [
            {
                "id": "sub_123",
                "tenant_id": "tenant_123",
                "plan": "plan_123",
                "status": subscription_status,
            }
        ],
        "tenant_config": [
            {
                "tenant_id": "tenant_123",
                "subscription_status": tenant_status,
                "subscription_ends_at": None,
                "trial_ends_at": "2026-04-12T00:00:00+00:00",
            }
        ],
        "tenant_plans": [],
        "billing_cycles": [],
        "tenant_usage_summary": [],
    }
    if include_cycle:
        cycle = {
            "id": "cycle_123",
            "tenant_id": "tenant_123",
            "plan_id": "plan_123",
            "status": "active",
            "max_credits": 100,
            "cycle_start": "2026-04-09T00:00:00+00:00",
            "cycle_end": "2027-04-09T00:00:00+00:00",
        }
        state["billing_cycles"].append(cycle)
        if include_summary:
            state["tenant_usage_summary"].append({
                "id": "summary_123",
                "tenant_id": "tenant_123",
                "billing_cycle_id": "cycle_123",
                "credits_used_total": 0,
                "credits_used_voucher": 0,
                "credits_used_document": 0,
                "credits_used_message": 0,
                "events_count_total": 0,
                "events_count_voucher": 0,
                "events_count_document": 0,
                "events_count_message": 0,
            })
    return state


def test_webhook_rejects_bad_signature(monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", VALID_WEBHOOK_SECRET)

    raw_body = _make_payload("payment_link.paid")
    response = client.post(
        "/api/payments/webhook",
        content=raw_body,
        headers={"X-Razorpay-Signature": _sign_payload(raw_body, INVALID_WEBHOOK_SECRET)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid signature"


def test_webhook_accepts_payment_link_paid(monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", VALID_WEBHOOK_SECRET)

    fake = FakeSupabase(_base_state())
    with patch("routers.payments.get_supabase_client", return_value=fake):
        raw_body = _make_payload("payment_link.paid")
        response = client.post(
            "/api/payments/webhook",
            content=raw_body,
            headers={"X-Razorpay-Signature": _sign_payload(raw_body, VALID_WEBHOOK_SECRET)},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fake.table_rows("subscriptions")[0]["status"] == "paid"
    assert fake.table_rows("tenant_config")[0]["subscription_status"] == "active"
    assert len(fake.table_rows("tenant_plans")) == 1
    assert len(fake.table_rows("billing_cycles")) == 1
    assert len(fake.table_rows("tenant_usage_summary")) == 1


@patch("routers.payments.get_supabase_client", return_value=FakeSupabase(_base_state()))
def test_webhook_accepts_payment_captured(_mock_supabase, monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", VALID_WEBHOOK_SECRET)

    raw_body = _make_payload("payment.captured")
    response = client.post(
        "/api/payments/webhook",
        content=raw_body,
        headers={"X-Razorpay-Signature": _sign_payload(raw_body, VALID_WEBHOOK_SECRET)},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@patch("routers.payments.get_supabase_client")
def test_webhook_is_idempotent_after_full_activation(mock_supabase, monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", VALID_WEBHOOK_SECRET)
    fake = FakeSupabase(_base_state(subscription_status="paid", tenant_status="active", include_cycle=True, include_summary=True))
    mock_supabase.return_value = fake

    raw_body = _make_payload("payment_link.paid")
    headers = {"X-Razorpay-Signature": _sign_payload(raw_body, VALID_WEBHOOK_SECRET)}

    first = client.post("/api/payments/webhook", content=raw_body, headers=headers)
    second = client.post("/api/payments/webhook", content=raw_body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(fake.table_rows("billing_cycles")) == 1
    assert len(fake.table_rows("tenant_usage_summary")) == 1
    assert fake.table_rows("subscriptions")[0]["status"] == "paid"
