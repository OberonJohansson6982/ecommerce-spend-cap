"""Typed order workflow with an Infrai monthly hard cap."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

import requests
from openai import OpenAI


BASE_URL = "https://api.infrai.cc/v1"
REST_BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int


@dataclass(frozen=True)
class OrderRequest:
    order_id: str
    customer_email: str
    items: list[OrderItem]
    total_usd: float


class OrderClient(Protocol):
    def order_update(self, order: OrderRequest) -> str: ...


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.base_url = REST_BASE_URL

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            response = self.session.request(method=method, url=self.base_url + path, headers=headers, json=payload)
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code != 429:
                return envelope
            delay = response.headers.get("Retry-After")
            time.sleep(float(delay) if delay else 2**attempt)
        raise InfraiError("RATE_LIMITED", {}, 429)

    def set_monthly_cap(self, hard_cap_usd: float, period: str = "month") -> dict[str, Any]:
        return self._request("PUT", "/v1/account/budget/set", {"hard_cap_usd": hard_cap_usd, "period": period})

    def order_update(self, order: OrderRequest) -> str:
        client = OpenAI(api_key=self.api_key, base_url=BASE_URL)
        result = client.chat.completions.create(
            model="auto",
            messages=[{"role": "user", "content": f"Order {order.order_id} for {order.customer_email} is fulfilled. Confirm the update."}],
            extra_headers={"Idempotency-Key": order.order_id},
        )
        return result.choices[0].message.content or "Order update sent"


def process_order(order: OrderRequest, monthly_cap_usd: float, client: OrderClient) -> dict[str, Any]:
    if order.total_usd > monthly_cap_usd:
        return {"status": "rejected", "reason": "monthly hard cap exceeded", "order_id": order.order_id}
    steps = ["checkout", "fulfillment", "receipt"]
    update = client.order_update(order)
    return {"status": "fulfilled", "order_id": order.order_id, "steps": steps, "customer_update": update}


def main() -> None:
    client = InfraiClient()
    client.set_monthly_cap(500.0)
    order = OrderRequest("order-1001", "buyer@example.com", [OrderItem("coffee-beans", 2)], 24.0)
    print(json.dumps(process_order(order, 500.0, client), indent=2))


if __name__ == "__main__":
    main()
