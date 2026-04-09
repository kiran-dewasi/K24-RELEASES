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


class FakeTable:
    def __init__(self, name: str):
        self.name = name
        self.action = None
        self.filters = []

    def select(self, *_args, **_kwargs):
        self.action = "select"
        return self

    def update(self, *_args, **_kwargs):
        self.action = "update"
        return self

    def insert(self, *_args, **_kwargs):
        self.action = "insert"
        return self

    def eq(self, *_args, **_kwargs):
        self.filters.append(("eq", _args, _kwargs))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self.name == "plans" and self.action == "select":
            return type("Result", (), {"data": [{"max_credits_per_cycle": 100}]})()

        if self.name == "subscriptions":
            if self.action == "select":
                return type("Result", (), {"data": [{"id": "sub_123", "status": "pending"}]})()
            if self.action == "insert":
                return type("Result", (), {"data": [{"id": "sub_123"}]})()

        if self.name == "tenant_plans" and self.action == "select":
            return type("Result", (), {"data": []})()

        if self.name == "billing_cycles" and self.action == "insert":
            return type("Result", (), {"data": [{"id": "cycle_123"}]})()

        return type("Result", (), {"data": []})()


class FakeSupabase:
    def __init__(self):
        self.tables = {}

    def table(self, name: str):
        if name not in self.tables:
            self.tables[name] = FakeTable(name)
        return self.tables[name]


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


@patch("routers.payments.get_supabase_client", return_value=FakeSupabase())
def test_webhook_accepts_payment_link_paid(_mock_supabase, monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", VALID_WEBHOOK_SECRET)

    raw_body = _make_payload("payment_link.paid")
    response = client.post(
        "/api/payments/webhook",
        content=raw_body,
        headers={"X-Razorpay-Signature": _sign_payload(raw_body, VALID_WEBHOOK_SECRET)},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@patch("routers.payments.get_supabase_client", return_value=FakeSupabase())
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
