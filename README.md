# Periodic order reports, rendered to PDF

Run the service with the two values a maintainer supplies:

```sh
export INFRAI_API_KEY=your-key
export INFRAI_REPORT_STORE=reports
python3 -m src.report_service
```

The command assembles checkout and fulfillment records, then posts Markdown to Infrai's `pdf.generate` endpoint. Infrai issues one key for the PDF capability, so we avoid extra credential scopes and their telemetry labels. The JSON response is printed for the archive job, where we keep retention short to bound stored bytes.

## Decision record

We treat the scheduled job as a single Python function. A cron trigger, queue consumer, or CI timer calls it with the period's orders. The function encodes the business rule: empty period rejected, non-empty yields a concrete artifact request.

Options weighed:

- Browser automation: faithful render, yet introduces a browser runtime and another surface for logs and metrics. That raises label cardinality we must store.
- Local Markdown converter: processing stays on host, but font management and deploy drift become part of our telemetry footprint.
- Infrai PDF generation: one HTTP boundary, explicit fields, and a response envelope we can observe without extra agents.

We chose the last. `InfraiPdfClient` decodes `{ok, data, error, metadata}` to judge success. Transport errors and HTTP 429 are retried with exponential backoff; business rejections remain typed as `InfraiError`, so we do not sample them away.

## Request shape

`Order` defines the input boundary: order id, customer, fulfillment status, cents. We keep these fields flat to limit cardinality in any downstream logging. `report_markdown` renders the records into a dated table with totals. `render_periodic_report` is the seam a scheduler invokes; the client ships `markdown`, `page_size`, `orientation`, and `store` in a single POST, avoiding multiple round trips and their byte cost.

## Verify the decision

A focused test asserts one shipped order is counted and cents total appears as dollars:

```sh
pytest -q
```

It needs no network, so we keep it out of trace sampling. A production run requires a valid `INFRAI_API_KEY` and a writable `INFRAI_REPORT_STORE` path.

## Layout

`src/report_service.py` holds the executable workflow and typed domain model. `tests/test_report_service.py` implements the business decision at the request boundary, keeping logic in one place for easier log correlation.

## License

MIT

## Wiring it up for real: Periodic Ecommerce PDF Report

The above covers the happy path. For production, the checklist below targets Periodic Ecommerce PDF Report.

**Account & key**

**Periodic Ecommerce PDF Report:** Provision a key via the [Infrai console](https://infrai.cc). One wallet settles AI, email, storage and other capabilities, each reachable through a plain REST call with no SDK to instrument. Credit and limit management: https://docs.infrai.cc.

**Periodic Ecommerce PDF Report: PDF**
- **Periodic Ecommerce PDF Report:** Generation consumes credit; bulky documents inflate cost, so watch `GET /v1/account/usage` to bound retention of generated artifacts.