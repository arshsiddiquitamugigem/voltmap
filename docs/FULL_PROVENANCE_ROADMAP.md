> **Historical design / future roadmap.** The reduced build described in `../README.md` and `BUILD_REPORT.md` supersedes all admission, migration, approval and implementation prerequisites in this document. The field boundary is approved. All 13 linked battery rows are loaded unsplit. No 4b/4c work is scheduled; this document is not a claim of implemented enforcement.

# VOLTMAP — increment 4 schema design for review

**Design only. No database, migration, ingestion or app has been created.** The field-keyed provenance validator is implemented separately. The workbook remains byte-for-byte unchanged. The final field-boundary approval is still required before assigning tags or migrating values.

## Decision to approve

Use exactly four application tables: `vehicles`, `batteries`, `sources`, `fitment_links`. Store every authoritative battery measurement or classification in `batteries` only. A vehicle reaches battery records through `fitment_links`; it has no battery-rating columns or permissive JSON container into which those ratings can be copied.

A single `vehicles.battery_id` would be insufficient: a hybrid has auxiliary and traction systems, and the RAV4 auxiliary application has three unresolved alternatives. The relationship must support several battery records without claiming all three alternatives are installed simultaneously.

The four-table limit is appropriate for a battery-focused first release. It does **not** support a general parts catalog. The real DENSO spark-plug record and its fitment must remain in the unchanged workbook and exclusion report, rather than being converted into a battery. General component inventory would require a later schema decision.

## Table contracts

These are proposed columns and invariants, not an executed schema. JSON fields have closed schemas, not arbitrary dictionaries. The future migration must implement the database enforcement described below before any load is allowed.

### 1. vehicles

| Column | Proposed type | Purpose and constraint |
|---|---|---|
| vehicle_id | TEXT primary key | Internal application identity; never presented as a licensed vehicle identifier. |
| legacy_vehicle_ref | TEXT unique, nullable | Preserve `910001` etc. explicitly as legacy local references. |
| canonical_vehicle_id | INTEGER unique, nullable | Only populated after licensed mapping is established; never copied from the sample column. |
| canonical_base_vehicle_id | INTEGER nullable | Same canonical-mapping requirement; local base IDs live in the audit mapping. |
| canonical_engine_config_id | INTEGER nullable | Same separation for the engine placeholder IDs. |
| year, make, model, submodel, region | INTEGER / TEXT | Exact selection identity and market. Display says “Selected vehicle.” |
| engine_liters, engine_cylinders, engine_code, aspiration, drive_type | Typed nullable columns | Selection metadata; not proof that the present identity is canonical. No inheritance between standard and performance trims. |
| generation | TEXT nullable | Descriptive identity metadata; cannot widen evidence scope. |
| origin_source_id | INTEGER nullable, FK sources | Valid source mapping when known. Do not invent a mapping for current 999 rows. |
| identity_state | TEXT enum | `UNMAPPED` or `CANONICAL`; production requires the latter. |
| provenance_state | TEXT enum | `SOURCE_MAPPING_UNRESOLVED`, `PARTIAL`, or `REVIEWED`; separate from identity_state. |
| electrical_status | TEXT controlled enum | Existing five verification statuses. |
| vehicle_facts | JSON object, closed key set | Field-keyed claim envelopes for vehicle-system facts only, enumerated below. **No battery chemistry, group, voltage, CCA, capacity, dimensions or warranty keys.** |
| review_event | JSON nullable, closed shape | Timestamp, review kind, reviewer, and scope. A metadata audit is distinct from an evidence review; no fabricated historical date. |
| reason_codes | JSON array of controlled codes | Missing mappings, evidence gaps and required reviews. No freeform specification values. |

Allowed `vehicle_facts` keys: `powertrain_type`, `electrical_architecture`, `system_voltage_v`, `has_hv_traction_system`, `battery_registration_required`, `aux_12v_battery_presence`, `alternator_rated_a`, `alternator_output_v`, `voltage_regulator_type`, `starter_voltage_v`, `main_fuse_link_rating_a`, `oem_alternator_pn_ref`. Their claim values live only inside the envelopes. `system_voltage_v` is a vehicle-system claim, not an alias of a battery’s nominal voltage. Auxiliary presence records an explicit classification; absence of a fitment row is not evidence of absence.

Alternator, starter and main-fuse facts cannot correctly be normalized into a battery record. They remain bounded vehicle-system facts in this four-table version. If later component-level sharing or multiple alternators is required, introduce a dedicated component model rather than reusing `batteries`.

### 2. batteries

| Column | Proposed type | Purpose and constraint |
|---|---|---|
| battery_id | TEXT primary key | Internal record identity. |
| record_kind | TEXT enum | `APPLICATION_REQUIREMENT`, `PRODUCT`, or `TRACTION_PACK_SPECIFICATION`. These are distinct subjects, not interchangeable descriptions of the installed battery. |
| origin_refs | JSON array, unique per origin after review | Workbook battery-entry and/or real-parts keys retained for traceability. Combining origins requires claim-by-claim review, not similar names. |
| application_role | TEXT enum | `AUXILIARY_12V` or `HV_TRACTION`; role is not inferred solely from voltage. |
| designation | TEXT nullable | For example Type A, B or C; does not choose which one is installed. |
| brand_name, part_number | TEXT nullable | Product identity when known. Requirements need not have a part number. Brand-qualified part identity; do not erase punctuation without retaining the original. |
| licensed_brand_id, licensed_part_type_id | TEXT nullable | Missing licensing/mappings stay missing. |
| field_provenance | JSON object, closed canonical field keys | Canonical battery claim envelopes. Each claim contains its sole stored value, unit, qualifier, source references, document locator, scope, review date, status and notes. No second bare scalar copy of the spec is stored. |
| verification_status | TEXT controlled enum | Summarizes retained claims; cannot override a field conflict or unknown. |
| review_event | JSON nullable | Scoped review, not automatic certification. |
| reason_codes | JSON array of controlled codes | Recorded limitations. |

`field_provenance` is keyed by specification name. A field has `state` and `claims`. A conflict retains multiple individually sourced claims; there is no `preferred_value`. An unknown has an explicit state and an empty claim list. A known value without evidence cannot be returned as a specification.

The validator’s sidecar currently includes `raw_value` to bind the proposed provenance to the exact workbook cell. That is a **migration check**, not an additional runtime specification column. After reviewed migration, the original text remains in the preserved workbook/audit artifact; the database stores the reviewed claim values only once.

Do not mechanically convert every workbook battery row into one canonical record. A row may currently combine a vehicle requirement, a service-product rating and an aftermarket alternative. Split those subjects during a reviewed migration, retain their origin references, and reference them independently. Do not declare a final loaded battery count before that review.

Canonical battery fields use the existing 36-field boundary with explicit aliases consolidated: nominal voltage (`nominal_voltage_v` / `hv_nominal_pack_voltage_v`), chemistry (`battery_type_chemistry` / `hv_chemistry`), total energy (`energy_capacity_wh_kwh` / `hv_total_energy_kwh` when the energy meaning agrees), maximum depth of discharge (`max_depth_of_discharge` / `hv_max_depth_of_discharge`), and expected cycle life (`estimated_cycle_life` / `hv_expected_cycle_life`). Alias collapse requires compatible units, meaning and scope; differing claims remain separate claims or block migration. Usable energy remains distinct from total energy. Cell count and module count remain distinguished inside claim units. Parts attributes map to the same canonical battery fields; warranty terms remain product/market scoped.

### 3. sources

| Column | Proposed type | Purpose and constraint |
|---|---|---|
| source_id | INTEGER primary key | Preserve integer source IDs; the display code is derived as `S` plus this integer. Do not store a second independently editable code. |
| title, publisher, source_type | TEXT | Document identity and evidence class. |
| quality_tier | TEXT enum A/B/C/D | Source quality, distinct from fitment confidence. |
| url | TEXT nullable | Exact recorded page/document; NULL with explicit missing-URL state when unrecovered. No guessed homepage. |
| document_identifier, document_version, market | TEXT nullable | Preserve document version and jurisdiction. |
| model_year_start, model_year_end | INTEGER nullable | Document scope when established, not a global scope for every claim it contains. |
| url_state | TEXT enum | `RECORDED`, `NO_URL_ON_RECORD`, or `UNREACHABLE_ON_CHECK`. Recording a URL does not establish reachability. |
| registration_reviewed_at, content_reviewed_at, last_url_check_at | ISO date/time nullable | Separate registry review, evidence review and link check. Unknown historical dates remain NULL. |
| review_notes | TEXT | Limitations and source history; not an API specification source by itself. |

The Canadian Honda ERG Version 1 and American Version 2 remain different source records. No URL-based merge can erase a document-version distinction. Conflicting neutral-shift claims keep the applicable source and market/year scope.

The legacy vehicle origin `999` is an unresolved import defect. Preserve it in the external migration manifest; do not create a fake source citation merely to satisfy a foreign key. These vehicles remain dev-only through explicit provenance and identity states. This does not resolve either source mapping or canonical identity.

### 4. fitment_links

| Column | Proposed type | Purpose and constraint |
|---|---|---|
| fitment_link_id | TEXT primary key | Application relationship identity. |
| vehicle_id | TEXT not null, FK vehicles | Exact selected local or approved canonical vehicle record. |
| battery_id | TEXT not null, FK batteries | Requirement, product candidate or traction specification being associated. |
| relationship_kind | TEXT enum | `DOCUMENTED_REQUIREMENT`, `CANDIDATE_PRODUCT`, `DOCUMENTED_TRACTION_SYSTEM`. None means physically inspected installation. |
| application_role | TEXT enum | Must agree with the linked battery record. |
| alternative_group | TEXT nullable | Groups Type A/B/C auxiliary alternatives; traction is a separate role. |
| qualifier | JSON, closed keys | Market, exact year bounds, trim/configuration selectors and installed-type resolution state. **No battery ratings or copied minimums.** Quantitative constraints reference an APPLICATION_REQUIREMENT record. |
| requirement_battery_id | TEXT nullable, FK batteries | Optional reference to the applicable requirement record, rather than a copied CCA/Ah threshold. |
| evidence | JSON array of source references and locators | Evidence for the association itself, separate from product specifications. |
| confidence_tier | TEXT nullable, enum A/B/C/D | Deterministic policy result only; source tier is not copied here. |
| verification_status | TEXT controlled enum | Preserves partial/conflicting/unknown status. |
| workflow_status | TEXT enum | Staged, reviewed or approved as supported by future rules. Existing rows remain staged. |
| verified_by, reviewed_at | TEXT nullable | Named reviewer and scoped review. Tier A requires named technician evidence; no automatic promotion. |
| reason_codes | JSON array of controlled codes | Unmapped IDs, unresolved installed type, missing source, missing physical review, etc. |
| legacy_fitment_ref | TEXT nullable | Preserve F-STAGE keys for existing product candidates. |

If a product candidate could relate to more than one requirement, use separate links keyed by vehicle, battery, relationship, role, requirement and qualifier. The shared product rating remains one claim in one battery record. None of these links selects the installed RAV4 type remotely.

## Every current vehicle column: destination

| Workbook column(s) | Destination / handling |
|---|---|
| vcdb_vehicle_id | vehicles.legacy_vehicle_ref; never automatically canonical_vehicle_id. |
| vcdb_base_vehicle_id, vcdb_engine_config_id | External origin mapping as placeholders; canonical columns remain NULL until licensed mapping. |
| year, make, model, submodel, region | vehicles selection columns. |
| engine_liters, engine_cylinders, engine_code, aspiration, drive_type, generation | vehicles selection metadata. |
| model_year_range | Per-claim evidence scope and fitment qualifier after review; never broadens the selected model year. PENDING remains unresolved. |
| powertrain_type, electrical_architecture, system_voltage_v | vehicles.vehicle_facts, with approved basis and actual evidence/rules. |
| has_hv_traction_system | vehicles.vehicle_facts; explicit tri-state claim, plus required auxiliary/traction presence checks. |
| battery_registration_required | vehicles.vehicle_facts; configuration-specific service requirement, not a battery product rating. |
| primary_batt_group_bci | batteries.field_provenance.battery_group_size via auxiliary link. |
| primary_batt_chemistry | batteries.field_provenance.chemistry via auxiliary link. |
| primary_batt_terminal | batteries.field_provenance.terminal_type_and_orientation via auxiliary link. |
| primary_batt_nominal_v | batteries.field_provenance.nominal_voltage_v via auxiliary link. |
| primary_batt_cca_a | batteries.field_provenance.cold_cranking_amps_cca via auxiliary link; separate OEM/service/aftermarket/minimum subjects. |
| primary_batt_reserve_min | batteries.field_provenance.reserve_capacity_min via auxiliary link. |
| aux_12v_battery | Presence classification in vehicle_facts. Any embedded battery rating is split into the corresponding battery claim, never retained as a second active value. |
| hv_batt_chemistry, hv_batt_nominal_v, hv_batt_capacity_kwh | Traction battery chemistry, nominal voltage and total-energy fields, subject to scope/unit review. |
| alternator_rated_a, alternator_output_v, voltage_regulator_type | vehicles.vehicle_facts. **Not battery facts.** |
| starter_voltage_v, main_fuse_link_rating_a | vehicles.vehicle_facts. **Not battery facts.** |
| charging_system_notes, electrical_compat_notes | Preserve original narrative in audit artifact; review and split any actionable claims into closed vehicle/battery fields or fitment qualifiers. No unsourced narrative becomes a specification in the API. |
| oem_alternator_pn_ref | vehicles.vehicle_facts as a sourced component-reference claim; no battery mapping. |
| data_source_id | Preserve raw 999 in migration audit; vehicles.origin_source_id remains unresolved and blocks production until mapped. |
| mvp_platform | Build/demo selection configuration, outside specification tables. |
| electrical_source_refs | Resolve to claim evidence and, where justified, origin_source_id; no blanket row-level provenance assignment. |
| electrical_data_status | vehicles.electrical_status; derived summary cannot erase field conflicts. |
| electrical_verification_notes | Original audit artifact plus explicit review-event scope/reason codes and claim notes after manual decomposition. |

This accounts for all 43 current vehicle columns. No vehicle battery-spec column survives as a second authoritative storage location.

## Required enforcement before loading

1. Enable SQLite foreign keys on every connection. Use restricted deletes for referenced vehicles, batteries and sources. References inside JSON arrays are **not** native foreign keys; implement source-existence/source-delete guards in triggers and validate them in the application transaction. Four tables avoid extra joins at the cost of explicit JSON reference validation.
2. Database insert/update guards enforce closed JSON key sets for `vehicle_facts`, battery `field_provenance` and fitment `qualifier`, with type checks and enum checks. Reject all battery-spec keys in vehicles and fitment qualifiers. Do not include an unrestricted vehicle attributes/notes blob as an escape hatch. The application serializer exposes only the validated envelope, never the audit artifact.
3. Enforce compatible battery record kinds, application roles, requirement references, exact configuration/year scopes and non-widening source claims. Insert/update/delete validation must be atomic for a complete import; never leave a partially loaded hybrid accepted.
4. A TRUE or unresolved high-voltage classification must fail closed for service advice. TRUE requires both auxiliary and traction records to satisfy the coverage gate. A missing traction record cannot disable suppression. Existence of a record is not approval of service instructions.
5. Store real research in a dedicated dev database with conspicuous `Development data — source and canonical ID mapping incomplete` labeling. Keep wholly synthetic fixture sheets in a different database/test artifact, never alongside research rows in a table or response. The flawed 999 tag on researched rows is retained as a defect, not taken as permission to load unrelated synthetic examples. Production is a separately validated build. No database is created in this increment.
6. Provenance and confidence gates are separate: a source citation is necessary but does not prove applicability. Unknown, partial and conflicting claims must stay visible. Field-boundary approval does not make evidence complete. No LLM layer is included.
7. Before generating a migration, tests must exercise rejected duplicate battery keys, source deletion, unresolved IDs, malformed provenance, stale hashes, conflict preservation, role mismatches, missing traction coverage, year widening and transaction rollback. These database tests are **future work**, because this delivery stops at design review.

The design prevents a second active battery specification from being represented in the vehicle or fitment schema. It does not eliminate disagreement between sources, product/requirement scope differences, or incomplete evidence. Those remain reviewable claims in the one authoritative table.

## Dataset-specific disposition

- Preserve all 15 vehicle records for dev review; source mapping and placeholder IDs remain distinct production blockers.
- Preserve all 13 linked battery research rows as migration inputs. Split mixed subjects only during an approved, audited migration. Keep the three unlinked pending templates excluded separately.
- Six of the seven real parts are battery products. Their ratings belong in PRODUCT records in `batteries`, with reviewed origin matching to existing battery-sheet claims. The Interstate item is a product candidate, not proof of vehicle compatibility.
- Preserve P-REAL-007 / DENSO FC16HR-Q8 and F-STAGE-006 in the workbook and exclusion manifest as `OUT_OF_BATTERY_SCHEMA_SCOPE`. No deletion and no invented battery conversion. Five current real fitments are battery-product candidates; battery research links add a separate relationship category, so the eventual fitment count is not simply six.
- Keep the RAV4 Type A/B/C requirement alternatives (285/286/345 CCA as recorded against S29, OM0R010U p.662) distinct from service-product ratings. This delivery relies on the existing workbook citation; it does not claim a new source-content check. Installed type remains unresolved; do not infer a rationale for the one-amp difference.
- Keep Civic performance configurations isolated. Standard-trim measurements cannot fill Si/Type R unknowns. Retain the H5/51R conflict as multiple claims with sources and scope.

## Review checkpoints

Approve the accompanying plain boundary list before applying its proposed tag assignments. Review this four-table design before generating a migration or loading any data. The outstanding 26 date and four source-reference findings are listed individually in the metadata audit; none was falsely closed. After approval, perform the reviewed provenance migration, re-run all three validators, then implement and test the database constraints and transaction loader against the dev partition.
