"""Small response contract: traceability is mandatory; verification is not invented."""
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

FIELDS = json.loads(Path(__file__).with_name('fields.json').read_text())
Status = Literal['Verified','Partially verified','Conflicting sources','Not publicly verified','Pending']


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Provenance(Model):
    workbook_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    sheet: str = Field(min_length=1)
    row: int = Field(ge=1)
    column: str = Field(min_length=1)
    source_ids: list[str]
    association: Literal['explicit_field_reference','record_citations_only','no_source_recorded']
    basis_tags: list[str]
    verification_status: Status
    status_scope: Literal['record'] = 'record'
    record_review_date: str | None
    locator: str | None = None


class Specification(Model):
    text: str
    provenance: Provenance


class Source(Model):
    source_id: str
    title: str
    source_type: str
    quality_tier: Literal['A','B','C','D']
    url: str | None
    checked_at: str | None
    url_status: str


class Vehicle(Model):
    vehicle_id: str
    legacy_vehicle_ref: str
    canonical_vehicle_id: int | None
    year: int
    make: str
    model: str
    submodel: str
    engine: str
    drive_type: str
    battery_records: int
    status: Status


class Battery(Model):
    battery_id: str
    application: str
    designation: str
    role: str
    verification_status: Status
    confidence_tier: None
    tier_note: str
    field_provenance: dict[str, Specification]
    sources: list[Source]
    suppressed_fields: list[str]


class VehicleList(Model):
    partition: Literal['dev'] = 'dev'
    vehicles: list[Vehicle]


class VehicleDetail(Model):
    partition: Literal['dev'] = 'dev'
    vehicle: Vehicle
    vehicle_facts: dict[str, Specification]
    hv_gate: dict


class BatteryList(Model):
    partition: Literal['dev'] = 'dev'
    vehicle: Vehicle
    batteries: list[Battery]
    hv_gate: dict
    ambiguity: str | None
    fitment_approved: Literal[False] = False


class BatteryDetail(Model):
    partition: Literal['dev'] = 'dev'
    battery: Battery


class SourceDetail(Model):
    partition: Literal['dev'] = 'dev'
    source: Source
