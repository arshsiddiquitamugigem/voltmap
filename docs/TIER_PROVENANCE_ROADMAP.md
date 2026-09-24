# Tier provenance — approved future design

**Documented, not implemented in this demo.** Rule-artifact hashing and per-input hashing remain the approved approach for a future tier engine. The earlier 64–110-hour phased plan is superseded by the reduced 10–15-hour database-and-app scope. No reviewed row migration or approval queue is required.

Keep confidence_tier and reason_codes as deterministic outputs, with one evaluation_provenance object on their owning record. They do not receive OEM/aftermarket basis tags. A result cannot be accepted independently of the exact rule and input snapshot that produced it.

Proposed shape (placeholders below are a contract illustration, not an evaluation):

```json
{
  "state": "evaluated",
  "rule_version": "phase4a-eligibility/1.0.0",
  "rule_sha256": "<SHA-256 of the bundled rule artifact>",
  "input_claim_refs": [
    {"table": "batteries", "record_id": "<id>", "field": "<specification>", "claim_id": "<id>", "sha256": "<canonical claim hash>"}
  ],
  "input_state_refs": [
    {"table": "vehicles", "record_id": "<id>", "field": "identity_state", "sha256": "<canonical value hash>"}
  ],
  "input_sha256": "<hash of the ordered input reference arrays>",
  "evaluated_at": "<UTC RFC3339 evaluation timestamp>",
  "outputs": {"confidence_tier": null, "reason_codes": ["TIER_NOT_EVALUATED"]},
  "output_sha256": "<canonical output hash>"
}
```

- Input references resolve to exact record/field/claim IDs. Each referenced value is hashed. Structural inputs have their own input_state_refs: do not disguise a canonical-ID mapping state as a sourced specification.
- Rule versions are immutable. A rule-content hash identifies the bundled artifact; version string alone is insufficient. Include the rule file with each database export.
- Canonical JSON uses sorted keys, compact separators, UTF-8, finite numbers only. Sort reference lists by table, record, field and claim ID. Missing references, changed content or a different rule hash invalidate the evaluation.
- The evaluation timestamp records rule execution, not factual verification. Unknown historical evidence-review dates remain unknown.
- Both outputs belong to the same evaluation. Their stored values must match the provenance outputs. On reads, re-resolve and check input hashes before treating any cached evaluation as current.
- The reduced demo does not execute this evaluator or emit evaluation provenance. Its confidence tier remains NULL. Its HV gate is separate from confidence grading.
- Evaluation provenance applies to reason_codes on vehicles and batteries as well as fitment links. Legacy unversioned reason codes remain in the import audit; they are not silently relabeled as new rule outputs.
- Mutation invalidation, cached evaluation validation and full confidence grading are future work. Phases 4b and 4c are not scheduled at this dataset size.

Future correction: quantity_required is an OEM-sourced application fact, not structural workflow metadata. It is absent from the battery-only schema and must require field-level OEM evidence when a later component schema introduces it. The historical boundary list remains an audit artifact; this amendment overrides its quantity_required line.

