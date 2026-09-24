# VOLTMAP — local research demo

A small, usable demonstration of what recorded battery research establishes—and what it leaves unresolved. Four SQLite tables, a read-only FastAPI server, and three screens. No confidence tier is assigned and no fitment is approved.

## Run

Use Python 3.12. Extract this entire folder, open a terminal in it, and run:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

On Windows, use `py -3.12 -m venv .venv` and `.venv\Scripts\activate` for the first two commands. The last two commands are the same.

The browser opens at **http://127.0.0.1:8000**. If it does not, open that address yourself. Stop the server with Ctrl+C. To use another port: `python run.py --port 8001`.

Dependency installation needs internet once. After setup, the app, database, styles and scripts work offline. Opening external citations requires internet. No account, API key or remote service is used. The server binds to this computer only.

For subsequent launches, activate `.venv` and run `python run.py`.

## Three-screen walkthrough

1. **Select a vehicle.** Choose the featured RAV4 or filter the recorded configurations. Empty results stay empty; the app does not substitute a trim.
2. **Read the findings.** The 2019 RAV4 shows Type A / B / C with minimum CCA requirements of 285 / 286 / 345, respectively. All remain visible by default. Selecting a label filters research; it does not establish physical fit. The Civic example preserves the H5 / 51R conflict.
3. **Follow the evidence.** Read original specification text, unknown markers, workbook locations and recorded citations. Row-level citations are explicitly distinguished from field references. Dates and statuses retain their recorded scope.

Use “Why are high-voltage results blocked?” to demonstrate suppression. The API also blocks direct traction-record requests. High-voltage records remain in SQLite for coverage checks; their specification fields are suppressed from consumer results.

## Data and boundaries

| Table | Rows | Meaning |
|---|---:|---|
| vehicles | 15 | Selected configurations, including four pending research configurations |
| batteries | 13 | All linked workbook battery rows, unsplit |
| sources | 37 | Existing source register |
| fitment_links | 15 | Research associations; not approved fitments |

Three pending battery templates are excluded separately. The synthetic parts/fitments sheets do not supply demo records. Battery specifications live only in `batteries`; vehicle summary battery measurements are not duplicated.

All original battery cell text—including notes and conflicting claims—is recoverable from `field_provenance` plus `record_metadata`. The source workbook is unchanged. The UI suppresses high-voltage fields and uses configuration terminology; it does not present every raw workbook note.

Every serialized specification requires provenance with a workbook hash and cell location. This is traceability, **not proof that every field is verified**. Existing field references and row-only citations are identified separately; missing basis tags and unknown review dates remain missing. URLs are recorded links, not freshly checked links.

The development banner remains visible because two independent defects remain open: real vehicle rows still carry legacy source ID `999`, and their legacy vehicle identifiers are placeholders rather than licensed canonical IDs. Canonical IDs and confidence tiers are NULL. Fixing one defect will not resolve the other.

The HV gate reads current vehicle classification and current battery links. Incomplete or contradictory known-HV coverage blocks battery results. Unknown classification cannot enable high-voltage or service advice. This demo provides no service recommendations for any configuration.

## Scope deliberately retained

- Four tables, native foreign keys, and closed field-name guards on `vehicle_facts` and battery `field_provenance`.
- All 13 linked battery records as original text; no claim-subject splits or approval queue.
- Read-only API, required response provenance, and a fail-closed HV gate.
- No JSON source-reference triggers, full enforcement matrix, tier evaluator, general write API, or LLM layer.

This is a pinned demonstration dataset, not a general-purpose production importer. It rejects a changed workbook hash and refuses to overwrite an existing database. Direct third-party database edits are outside the supported workflow; deferred enforcement is not silently claimed to exist.

## Check or rebuild

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m voltmap.store --output data/rebuilt.sqlite
```

The included `data/voltmap_dev.sqlite` is already loaded. The last command creates a separate database and import report without replacing it. Seventeen focused tests cover preservation, database constraints, response provenance, RAV4 ambiguity, Civic conflicts, and HV suppression. See `docs/BUILD_REPORT.md` for the tested scope.

`voltmap/fields.json` is the active closed field policy. `data/voltmap_dev.import.json` contains the full importer findings. The reused loader and workbook layout are included.

## Future design, not current implementation

`docs/TIER_PROVENANCE_ROADMAP.md` preserves the approved rule-artifact/input hashing design. `docs/FULL_PROVENANCE_ROADMAP.md` preserves the earlier complete design with a scope override. Phases 4b and 4c are not being built. `quantity_required`, if introduced later, is an OEM fact requiring evidence, not structural metadata.

Estimate recorded before this build: **4–6 focused hours for reduced 4a, plus 6–9 for the app; 10–15 total**. This is a solo-developer planning estimate, not a measurement of assistant execution time. New research, canonical licensing and productionization are outside it.
