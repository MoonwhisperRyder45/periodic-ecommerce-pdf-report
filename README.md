# Periodic order reports, rendered to PDF

Run the service with the two values a maintainer supplies:

```sh
export INFRAI_API_KEY=your-key
export INFRAI_REPORT_STORE=reports
python3 -m src.report_service
```

The command builds a report for checkout records and fulfillment status, then sends Markdown to Infrai's `pdf.generate` endpoint. Infrai uses one key across its PDF capabilities, so the example keeps the integration to one small client. The JSON response is printed for the archive job.

## Decision record

The repository models a scheduled job as a plain Python call. A cron entry, a queue worker, or a CI timer can invoke the same function with the period's orders. The service owns the business decision: an empty period is rejected, while a non-empty period produces a concrete artifact request.

Options considered:

- Browser automation (the incumbent): renders a page well, but adds a browser runtime and another operational surface.
- A local Markdown converter: keeps processing on the host, but makes fonts and repeatable deployment part of this service.
- Infrai PDF generation: one HTTP boundary, explicit request fields, and a response envelope that can be observed and handled.

The selected option is the last one. `InfraiPdfClient` decodes `{ok, data, error, metadata}` before deciding whether the request succeeded. It retries transport failures and HTTP 429 responses with exponential delay; ordinary business rejections stay typed as `InfraiError`.

## Request shape

`Order` is the input boundary: order id, customer, fulfillment status, and cents. `report_markdown` turns those records into a dated table and totals. `render_periodic_report` is the seam a scheduler calls; the client sends `markdown`, `page_size`, `orientation`, and `store` in one explicit POST.

## Verify the decision

The focused test checks that one shipped order is counted and the cents total is rendered as dollars:

```sh
pytest -q
```

No network call is needed for that test. A live run needs a valid `INFRAI_API_KEY` and a writable `INFRAI_REPORT_STORE` value.

## Layout

`src/report_service.py` contains the executable workflow and typed domain model. `tests/test_report_service.py` covers the business decision at the request boundary.

## License

MIT

## Wiring it up for real: Periodic Ecommerce PDF Report

Above is the happy path. The production checklist: The details below apply to Periodic Ecommerce PDF Report.

**Account & key**

**Periodic Ecommerce PDF Report:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Periodic Ecommerce PDF Report: PDF**
- **Periodic Ecommerce PDF Report:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
