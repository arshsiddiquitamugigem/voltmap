# Reduced 4a and local app — build report

This build replaces the earlier phased implementation as the active demo. Previous artifacts are untouched. No 4b or 4c work was performed.

## Delivered

Four tables; 15 vehicle configurations; all 13 linked battery rows; 37 sources; 15 research links. Three pending battery templates are excluded separately. There are 11 low-voltage rows and two retained traction rows. The latter participate in coverage checks but are not consumer results.

The app has three screens: vehicle selection, findings, and recorded specifications with evidence. The RAV4 demonstration retains all three alternatives and the 285/286/345 minimum CCA requirements. It does not pick the installed type. The Civic example preserves competing case/group claims. Development labeling, unknowns and NULL confidence tiers remain visible.

The user-facing app is implemented with FastAPI, SQLite and local HTML/CSS/JavaScript. No frontend build tool, remote data service or LLM is required. The database ships preloaded.

## Preservation and provenance

All original battery cells are recoverable from the database: specification strings in `field_provenance`, remaining cells in `record_metadata`. Seventeen focused tests include exact comparison of every reconstructed battery cell against the loader's workbook projection. The workbook itself remains byte-for-byte unchanged.

Source workbook SHA-256:

`92b6959c218151d0cc85a5311eceb720fc6475a30bceb7f895dd2438368c36b0`

Specifications are not copied into vehicle summary fields. The closed key policy keeps the workbook battery field names so loading does not require rewriting or splitting claims. The vehicle key set excludes battery measurements; the only renamed vehicle field is the presence classification `aux_12v_battery_presence`, with its original column retained in provenance.

Every API specification is a validated text-plus-provenance object. Provenance records workbook identity and location, existing source references, association strength, existing basis tags and the recorded row status/date. This does not turn a row-level citation into field verification. Unknown dates and missing tags stay unknown. RAV4 voltage/capacity/CCA references explicitly point to the already-approved S29, OM0R010U p.662; capacity and CCA are minimum requirements.

The API suppresses high-voltage specification fields from low-voltage records. Full original notes remain in SQLite and the unchanged workbook. The UI uses configuration terminology for a legacy phrase while retaining the original stored text. No number or competing claim is resolved by that display wording.

## Focused verification

`python -m pytest -q`: **17 passed**. This is the reduced app's test suite, not a re-report of the earlier implementation's 188 tests.

- Exact row preservation, unchanged workbook hash, table counts, native foreign keys and SQLite integrity.
- Closed vehicle/battery field-name guards reject unapproved keys.
- A specification without provenance cannot be serialized; malformed stored provenance makes the result unavailable.
- RAV4 alternatives retain exact values and source locator; Civic conflicts and unknowns survive.
- High-voltage requests and direct traction-record requests are blocked, including attempted override parameters.
- Removing a required traction link blocks hybrid low-voltage results and direct linked battery details.
- Unknown classification does not enable high-voltage or service advice.
- Empty selections do not substitute another vehicle. Pending research returns an empty result.
- API errors retain development labeling. Static assets are local.

One dependency deprecation warning was emitted by Starlette's test client; it did not affect the results. JavaScript syntax validation also passed. Browser checks also passed in Chromium: all three screens rendered, vehicle/type filters and specification search worked, the Civic conflict stayed visible, and the high-voltage dialog blocked results. No JavaScript page errors occurred. The 390-pixel mobile layout had no horizontal overflow. The five accompanying PNGs show the checked desktop/mobile screens.

## Remaining limitations — complete list for this reduced build

1. Legacy source ID `999` remains on all 15 vehicle rows. It is kept separate from the source register and is not silently replaced.
2. Legacy vehicle identifiers remain placeholders. All three canonical identifier columns are NULL; remapping a source ID will not make them canonical.
3. Mixed-subject text, disagreements, incomplete basis associations and unknown values are preserved, not repaired or certified. Battery `record_kind` is `LEGACY_UNSPLIT`.
4. Row statuses and dates are not per-field validation results. No new evidence-review dates or source reachability claims were invented.
5. `confidence_tier` stays NULL. There is no tier evaluator, generated reason-code evaluation, or implemented hash-based tier invalidation. The approved design is documented as future work.
6. Research links do not establish physical fit, interchange, an installed battery type, or a service recommendation.
7. The supported API is read-only. Native foreign keys and closed-key guards exist; trigger-based JSON source-reference guards, general updates and the full enforcement matrix do not.
8. The importer accepts only the pinned workbook. Applying a different dataset requires reviewing the import; this is not production ingestion.
9. Opening source URLs needs internet. Source content has not been re-researched by this build. Runtime app browsing works offline after dependency setup.
10. The app is a local demonstration, not a published or multi-user service. There is no authentication or hosted deployment.
11. The historical schema document remains a future design. Its prior admission restrictions and phased estimates are superseded; no row-by-row review workflow is active.
12. `quantity_required` is an OEM fact requiring future evidence if introduced; it is absent from this battery-only schema.

## Imported battery records

| Record | Role | Recorded status |
|---|---|---|
| B-CAM-001 | LOW_VOLTAGE | Partially verified |
| B-CIV-001 | LOW_VOLTAGE | Conflicting sources |
| B-CIV-002 | LOW_VOLTAGE | Conflicting sources |
| B-CIV-003 | LOW_VOLTAGE | Conflicting sources |
| B-CIV-004 | LOW_VOLTAGE | Conflicting sources |
| B-CIV-005 | LOW_VOLTAGE | Conflicting sources |
| B-CIV-006 | LOW_VOLTAGE | Conflicting sources |
| B-CIV-007 | LOW_VOLTAGE | Partially verified |
| B-CIV-008 | HV_TRACTION | Partially verified |
| B-RAV-00A | LOW_VOLTAGE | Partially verified |
| B-RAV-00B | LOW_VOLTAGE | Partially verified |
| B-RAV-00C | LOW_VOLTAGE | Partially verified |
| B-RAV-HV-001 | HV_TRACTION | Partially verified |
