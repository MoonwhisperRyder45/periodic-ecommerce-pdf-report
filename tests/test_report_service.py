from datetime import date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src.report_service import InfraiPdfClient, Order, InfraiError, render_periodic_report, report_markdown


def test_report_marks_fulfillment_and_totals():
    orders = [Order("A-1", "Ada", "shipped", 1000), Order("A-2", "Bo", "processing", 250)]
    text = report_markdown(date(2026, 1, 2), orders)
    assert "Shipped: 1" in text
    assert "Gross: $12.50" in text
    assert "| A-2 | Bo | processing |" in text


def test_empty_period_is_rejected_before_api_call():
    with pytest.raises(ValueError):
        render_periodic_report(date(2026, 1, 2), [], "reports", InfraiPdfClient.__new__(InfraiPdfClient))


@pytest.mark.parametrize("store", [None, "reports"])
def test_generate_only_sends_store_when_provided(store):
    client = InfraiPdfClient.__new__(InfraiPdfClient)
    requests = []
    client._request = lambda method, path, body: requests.append((method, path, body)) or {}

    client.generate("# Report", store)

    assert requests == [("POST", "/v1/pdf/generate", {
        "markdown": "# Report", "page_size": "A4", "orientation": "portrait",
        **({"store": store} if store is not None else {}),
    })]
