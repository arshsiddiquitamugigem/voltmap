"""Focused checks for the reduced demo, not the deferred full enforcement matrix."""
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from voltmap import store
from voltmap.api import create_app
from voltmap.models import Specification


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    path=tmp_path_factory.mktemp('reduced')/'demo.sqlite'
    return path,store.build(output=path)


@pytest.fixture
def client(built,tmp_path):
    path=tmp_path/'isolated.sqlite';path.write_bytes(built[0].read_bytes())
    return TestClient(create_app(path)),path


def test_four_tables_and_expected_counts(built):
    conn=store.connect(built[0]); names={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert names=={'vehicles','batteries','sources','fitment_links'}
    assert built[1]['counts']=={'vehicles':15,'batteries':13,'sources':37,'fitment_links':15}
    assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok';conn.close()


def test_every_battery_cell_and_conflict_retained_exactly(built):
    loaded=store.load_workbook(store.WORKBOOK,'dev'); conn=store.connect(built[0]);count=0
    for part in ('research_candidates','synthetic_candidates'):
        for row in loaded[part].get(store.B,[]):
            original=row['values'];r=conn.execute('SELECT * FROM batteries WHERE battery_id=?',(original['battery_entry_id'],)).fetchone()
            reconstructed=json.loads(r['record_metadata'])
            reconstructed.update({key:val['text'] for key,val in json.loads(r['field_provenance']).items()})
            assert reconstructed==original;count+=1
    assert count==13 and sha256(store.WORKBOOK.read_bytes()).hexdigest()==store.INPUT_SHA
    conn.close()


def test_no_canonical_mapping_or_tier_invented(built):
    conn=store.connect(built[0])
    assert conn.execute('SELECT count(*) FROM vehicles WHERE canonical_vehicle_id IS NOT NULL OR canonical_base_vehicle_id IS NOT NULL OR canonical_engine_config_id IS NOT NULL').fetchone()[0]==0
    assert conn.execute('SELECT count(*) FROM fitment_links WHERE confidence_tier IS NOT NULL').fetchone()[0]==0
    assert conn.execute('SELECT count(*) FROM vehicles WHERE legacy_data_source_id=999').fetchone()[0]==15
    conn.close()


def test_native_fk_and_closed_keys(client):
    _,path=client;conn=store.connect(path,False)
    with pytest.raises(sqlite3.IntegrityError):conn.execute("UPDATE fitment_links SET battery_id='missing'")
    with pytest.raises(sqlite3.IntegrityError):conn.execute("UPDATE vehicles SET vehicle_facts='{\"primary_batt_cca_a\":770}'")
    with pytest.raises(sqlite3.IntegrityError):conn.execute("UPDATE batteries SET field_provenance='{\"made_up\":123}'")
    conn.close()


def test_api_requires_provenance_and_refuses_corrupt_spec(client):
    with pytest.raises(ValidationError):Specification(text='12')
    api,path=client;conn=store.connect(path,False)
    conn.execute("UPDATE batteries SET field_provenance='{\"nominal_voltage_v\":{\"text\":\"12\"}}' WHERE battery_id='B-CAM-001'");conn.commit();conn.close()
    r=api.get('/api/batteries/B-CAM-001');assert r.status_code==503 and r.json()['partition']=='dev'


def test_rav4_all_three_minima_no_installed_type_selected(client):
    api,_=client;r=api.get('/api/vehicles/V-910004/batteries');assert r.status_code==200
    result=r.json();rows=result['batteries'];assert result['partition']=='dev'
    assert len(rows)==3 and not result['fitment_approved']
    assert [x['field_provenance']['cold_cranking_amps_cca']['text'] for x in rows]==['285','286','345']
    for x in rows:
        assert x['confidence_tier'] is None
        p=x['field_provenance']['cold_cranking_amps_cca']['provenance']
        assert p['source_ids']==['S29'] and 'p.662' in p['locator']


@pytest.mark.parametrize('path',[
    '/api/vehicles/V-910004/batteries?category=high_voltage',
    '/api/vehicles/V-910027/batteries?category=high_voltage',
    '/api/vehicles/V-910003/batteries?category=high_voltage',
    '/api/batteries/B-RAV-HV-001?override=true',
    '/api/batteries/B-CIV-008?include_hv=true',
])
def test_hv_gate_has_no_bypass(client,path):
    api,_=client;r=api.get(path);assert r.status_code==403
    assert r.json()['batteries']==[] and not r.json()['service_advice_allowed']
    assert 'field_provenance' not in r.text


def test_missing_traction_blocks_hybrid_and_direct_auxiliary_detail(client):
    api,path=client;conn=store.connect(path,False)
    conn.execute("DELETE FROM fitment_links WHERE battery_id='B-RAV-HV-001'");conn.commit();conn.close()
    for route in ('/api/vehicles/V-910004/batteries','/api/batteries/B-RAV-00A'):
        r=api.get(route);assert r.status_code==403 and r.json()['code']=='HV_COVERAGE_INCOMPLETE'


def test_unknown_hv_flag_cannot_enable_service_or_hv_results(client):
    api,path=client;conn=store.connect(path,False)
    data=json.loads(conn.execute("SELECT vehicle_facts FROM vehicles WHERE vehicle_id='V-910003'").fetchone()[0])
    data['has_hv_traction_system']['text']='Not publicly verified'
    conn.execute('UPDATE vehicles SET vehicle_facts=? WHERE vehicle_id=?',(json.dumps(data),'V-910003'));conn.commit();conn.close()
    result=api.get('/api/vehicles/V-910003').json()
    assert result['hv_gate']['recorded_hv_flag']=='UNKNOWN' and not result['hv_gate']['service_advice_allowed']
    assert api.get('/api/vehicles/V-910003/batteries?category=high_voltage').status_code==403


def test_conflicts_unknowns_and_record_only_citations_are_visible(client):
    api,_=client;b=api.get('/api/batteries/B-CIV-004').json()['battery']
    assert b['verification_status']=='Conflicting sources'
    assert '51R' in b['field_provenance']['battery_group_size']['text']
    assert 'H5' in b['field_provenance']['battery_group_size']['text']
    assert any(s['text'].startswith('Not publicly verified') for s in b['field_provenance'].values())
    assert any(s['provenance']['association']=='record_citations_only' for s in b['field_provenance'].values())
    assert not any(k.startswith('hv_') for k in b['field_provenance'])


def test_empty_selection_and_unresearched_vehicle(client):
    api,_=client;assert api.get('/api/vehicles?make=Missing').json()['vehicles']==[]
    assert api.get('/api/vehicles/V-910003/batteries').json()['batteries']==[]
    assert api.get('/api/vehicles/999999').status_code==404


def test_source_and_error_partition(client):
    api,_=client;r=api.get('/api/sources/S29');assert r.status_code==200 and r.json()['partition']=='dev'
    assert r.json()['source']['url'].endswith('OM0R010U.pdf')
    assert api.get('/api/vehicles?year=oops').json()['partition']=='dev'


def test_static_app_is_local(client):
    api,_=client;page=api.get('/');assert page.status_code==200
    assert 'DEVELOPMENT DATA' in page.text
    assert 'src="http' not in page.text and 'href="https://' not in page.text
    assert api.get('/static/app.js').status_code==200
