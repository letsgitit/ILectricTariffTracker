# Illinois Electric Tariff Tracker

Tracks ComEd and Ameren Illinois **C&I** regulatory tariff documents, checks
weekly for changes, and exposes current values / history / a change feed
through a small API.

Seeded out of the box with 8 real, currently-live documents covering ComEd
and Ameren Illinois C&I delivery classes — see `config/tracked_documents.yaml`
for the full list and notes on each. Two of them (`comed-nonresidential-line-items`
and `ameren-mapp-delivery-charges`) are configured with tested regex patterns
that pull specific dollar figures (Customer Charge, Distribution Facilities
Charge, etc.) per delivery class; the rest are hash-only (they'll flag "this
document changed" but you'll review the diff by eye).

## Why some documents are hash-only, not fully parsed

Two ComEd tariff documents look like they should be the numeric source but
aren't:
- **Rate RDS** (the tariff itself) *defines* each charge by name and says
  the dollar figure is "listed in the Delivery Service Charges Informational
  Sheets" — it doesn't contain the numbers. The actual numbers live in
  **"Summary of Typical Nonresidential Line Item Charges"**, tracked
  separately and republished each January.
- Ameren's **DS-2/DS-3/DS-4** tariffs are similarly qualitative for most
  provisions; the numbers Ameren republishes on a regular cadence are in
  the **MAP-P Delivery Charges Informational Sheet**.

This was verified by actually fetching and reading each live document while
building this, not assumed — worth knowing before you extend the pattern
list, since it's a real gotcha with how these utilities structure tariffs.

## Quick start (Docker — recommended)

```bash
docker compose up --build
```

This builds the image, starts the API on `http://localhost:8000`, and starts
the in-process weekly scheduler (default: Monday 6:00am server time — change
via `TARIFF_CHECK_DAY` / `TARIFF_CHECK_HOUR` in `docker-compose.yml`).

On first startup the app seeds the database from
`config/tracked_documents.yaml`, but does **not** run a check automatically —
run one manually to populate initial data:

```bash
curl -X POST http://localhost:8000/check-all
```

## Quick start (no Docker)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export TARIFF_DB_PATH=./data/tariff_tracker.db
export TARIFF_CONFIG_PATH=./config/tracked_documents.yaml
uvicorn app.main:app --reload
```

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | liveness check |
| GET | `/documents?utility=ComEd` | list tracked documents, optional utility filter |
| POST | `/documents` | add a new tracked document |
| GET | `/documents/{doc_key}/current` | latest snapshot + parsed line items |
| GET | `/documents/{doc_key}/history` | every snapshot ever taken |
| POST | `/documents/{doc_key}/check-now` | force an immediate fetch of one document |
| POST | `/check-all` | force an immediate fetch of every active document |
| GET | `/changes?since=2026-01-01` | detected changes, optionally filtered by date |

Interactive docs (Swagger UI) are auto-generated at `/docs` once the app is running.

### Example: what a change looks like

```json
{
  "id": 4,
  "tracked_document_id": 2,
  "detected_at": "2027-01-06T06:00:11",
  "change_type": "line_item",
  "summary": "1 tracked line item(s) changed in Summary of Typical Nonresidential Line Item Charges",
  "line_item_diffs": {
    "Medium Load Delivery Class - Customer Charge ($/Mo)": {"old": "34.08", "new": "35.90"}
  }
}
```

## Adding more documents

Edit `config/tracked_documents.yaml` and redeploy (the app upserts by
`id`/`doc_key` on every startup — nothing you added manually via the API gets
deleted), or `POST /documents` directly. If you want automatic parsing
instead of hash-only tracking, add `line_item_patterns` — a regex with one
capture group around the dollar figure, tested against the *actual current*
document text first. Patterns that "look right" from general knowledge of
the doc are a bad idea; fetch the PDF, grep for the text you want, and build
the regex against it, the way `comed-nonresidential-line-items` was built.

## Scheduling: in-process vs. external cron

The Docker setup runs `APScheduler` inside the API process — simplest option
for self-hosting. If you'd rather drive it from your host's crontab or a
cloud scheduler instead:

```bash
# crontab -e
0 6 * * 1 cd /path/to/tariff-tracker && python3 scripts/run_check_now.py >> /var/log/tariff-tracker.log 2>&1
```

and remove the `start_scheduler()` call in `app/main.py`'s startup event so
you're not double-checking.

## Operational notes

- **Rate limiting / courtesy**: the fetcher sets a descriptive User-Agent.
  Weekly is a low, respectful frequency for these public documents — don't
  drop this to hourly/daily without reason.
- **Layout drift**: utility tariff sheets get reformatted occasionally (new
  footnote numbering, reordered columns). A pattern that matched last month
  can silently stop matching — that's why `parsed_line_items` stores `null`
  for a pattern that didn't match a given fetch rather than silently
  omitting it, so you can see it failed. Check `/documents/{doc_key}/history`
  periodically for `null` line items even without a `change_event`.
- **Not legal advice / not the official record**: like ComEd's own site says
  about its posted tariffs, treat this as a monitoring tool, not the
  authoritative filing — always confirm against the ICC docket or the
  utility's official tariff for anything contractual.
