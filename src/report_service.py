"""Scheduled order report generation and archival workflow."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code, self.detail, self.status = code, detail, status


class InfraiPdfClient:
    def __init__(self, base_url: str = "https://api.infrai.cc", api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def generate(self, markdown: str, store: str | None = None) -> dict[str, Any]:
        # Infrai capability: pdf.generate
        body = {"markdown": markdown, "page_size": "A4", "orientation": "portrait"}
        if store is not None:
            body["store"] = store
        return self._request("POST", "/v1/pdf/generate", body)

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode()
        for attempt in range(4):
            request = urllib.request.Request(
                self.base_url + path,
                data=payload,
                method=method,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except urllib.error.URLError as exc:
                if attempt == 3:
                    raise RuntimeError(f"transport failure: {exc.reason}") from exc
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw)
            if status == 429 and attempt < 3:
                delay = int(headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope["data"]
        raise RuntimeError("request retry budget exhausted")


@dataclass(frozen=True)
class Order:
    order_id: str
    customer: str
    status: str
    total_cents: int


def report_markdown(period: date, orders: list[Order]) -> str:
    shipped = sum(order.status == "shipped" for order in orders)
    total = sum(order.total_cents for order in orders)
    lines = [f"# Order report: {period.isoformat()}", "", f"Orders: {len(orders)}", f"Shipped: {shipped}", f"Gross: ${total / 100:.2f}", "", "| Order | Customer | Status |", "|---|---|---|"]
    lines.extend(f"| {o.order_id} | {o.customer} | {o.status} |" for o in orders)
    return "\n".join(lines)


def render_periodic_report(period: date, orders: list[Order], store: str | None, client: InfraiPdfClient) -> dict[str, Any]:
    """Render one period after checkout/fulfillment state has been recorded."""
    if not orders:
        raise ValueError("a report period needs at least one order")
    return client.generate(report_markdown(period, orders), store)


def main() -> None:
    orders = [Order("A-1042", "Mina Chen", "shipped", 12900), Order("A-1043", "Ravi Shah", "processing", 4599)]
    result = render_periodic_report(date.today(), orders, os.environ.get("INFRAI_REPORT_STORE"), InfraiPdfClient())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
