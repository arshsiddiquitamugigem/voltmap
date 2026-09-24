"""Read-only, local FastAPI demo. No ranking, tier engine or remote calls."""
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import store
from .models import (Battery, BatteryDetail, BatteryList, Source, SourceDetail,
                     Specification, Vehicle, VehicleDetail, VehicleList, FIELDS)


def hv_gate(conn, row):
    """Check current flag AND current links; a missing traction row never clears HV."""
    facts=json.loads(row['vehicle_facts'])
    raw=facts.get('has_hv_traction_system',{}).get('text','').strip().upper()
    counts=dict(conn.execute('SELECT b.role,count(*) FROM batteries b JOIN fitment_links f USING(battery_id) WHERE f.vehicle_id=? GROUP BY b.role',(row['vehicle_id'],)).fetchall())
    positive=raw=='TRUE' or bool(counts.get('HV_TRACTION'))
    contradictory=raw=='FALSE' and bool(counts.get('HV_TRACTION'))
    complete=bool(counts.get('LOW_VOLTAGE')) and bool(counts.get('HV_TRACTION'))
    blocked=positive and (not complete or contradictory)
    return {'recorded_hv_flag':raw if raw in {'TRUE','FALSE'} else 'UNKNOWN',
            'coverage':'blocked' if blocked else ('both_roles_present' if positive else 'no_hv_coverage_established'),
            'coverage_blocked':blocked,'consumer_hv_suppressed':True,'service_advice_allowed':False,
            'traction_records':counts.get('HV_TRACTION',0),'low_voltage_records':counts.get('LOW_VOLTAGE',0),
            'message':('Hybrid battery coverage is incomplete or contradictory. Results are blocked.' if blocked else
                       'High-voltage components and service instructions are outside this demo. Record presence is not fitment approval.')}


def create_app(database=store.DATABASE):
    application=FastAPI(title='VOLTMAP · development research demo',version='0.1.0')
    application.state.database=Path(database)
    static=Path(__file__).with_name('static')
    application.mount('/static',StaticFiles(directory=static),name='static')

    @contextmanager
    def db():
        if not application.state.database.exists():raise HTTPException(503,'Database missing. Run python -m voltmap.store.')
        conn=store.connect(application.state.database)
        try:yield conn
        finally:conn.close()

    def fail(message,code='HV_SERVICE_SUPPRESSED'):
        raise HTTPException(403,{'code':code,'message':message,'batteries':[], 'service_advice_allowed':False})

    def vehicle_row(conn,key):
        row=conn.execute('SELECT * FROM vehicles WHERE vehicle_id=?',(key,)).fetchone()
        if row is None:raise HTTPException(404,'That vehicle is not in this dataset. No nearest match was selected.')
        return row

    def vehicle(conn,row):
        count=conn.execute('SELECT count(*) FROM fitment_links WHERE vehicle_id=?',(row['vehicle_id'],)).fetchone()[0]
        return Vehicle(**{k:row[k] for k in ('vehicle_id','legacy_vehicle_ref','canonical_vehicle_id','year','make','model','submodel','engine','drive_type','status')},battery_records=count)

    def source(conn,code,required=False):
        if not code.startswith('S') or not code[1:].isdigit():raise HTTPException(404,'Unknown source')
        row=conn.execute('SELECT metadata FROM sources WHERE source_id=?',(int(code[1:]),)).fetchone()
        if row is None:raise HTTPException(503 if required else 404,'A source reference cannot be resolved. No citation was substituted.')
        m=json.loads(row['metadata']);url=m['URL'] if m['URL'].startswith(('https://','http://')) else None
        return Source(source_id=code,title=m['source'],source_type=m['type'],quality_tier=m['tier'],url=url,
                      checked_at=m.get('checked_at') or None,url_status='Recorded URL; reachability not checked by this app' if url else 'No URL on record')

    def battery(conn,row):
        if row['role']!='LOW_VOLTAGE':fail('High-voltage and unresolved battery categories are suppressed. No component or service recommendations are available.')
        fields=json.loads(row['field_provenance'])
        if fields.keys()-set(FIELDS['battery']):raise HTTPException(503,'Unexpected stored specification field')
        suppressed=[k for k in fields if k.startswith('hv_')]
        public={k:Specification.model_validate(v) for k,v in fields.items() if k not in suppressed}
        # Required provenance includes an immutable workbook location. Citations
        # from a whole row remain explicitly weaker than a field association.
        codes=sorted({s for spec in public.values() for s in spec.provenance.source_ids})
        return Battery(battery_id=row['battery_id'],application=row['application'],designation=row['designation'],role=row['role'],
                       verification_status=row['verification_status'],confidence_tier=None,tier_note='Not evaluated. Research records do not establish fitment.',
                       field_provenance=public,sources=[source(conn,s,required=True) for s in codes],suppressed_fields=suppressed)

    @application.exception_handler(HTTPException)
    async def http_error(request,exc):
        body=exc.detail if isinstance(exc.detail,dict) else {'message':exc.detail}
        return JSONResponse(status_code=exc.status_code,content={'partition':'dev',**body})

    @application.exception_handler(RequestValidationError)
    async def request_error(request,exc):
        return JSONResponse(status_code=422,content={'partition':'dev','message':'Invalid request. Choose a value offered by this dataset.'})

    @application.exception_handler(ResponseValidationError)
    @application.exception_handler(ValidationError)
    async def response_error(request,exc):
        return JSONResponse(status_code=503,content={'partition':'dev','message':'Stored provenance failed validation. This result is unavailable.'})

    @application.get('/',include_in_schema=False)
    def home():return FileResponse(static/'index.html')

    @application.get('/api/vehicles',response_model=VehicleList)
    def vehicles(make:str|None=None,model:str|None=None,year:int|None=Query(None,ge=1886,le=2200)):
        where=[];args=[]
        for name,value in [('make',make),('model',model),('year',year)]:
            if value is not None:where.append(name+' = ? COLLATE NOCASE');args.append(value)
        with db() as conn:
            rows=conn.execute('SELECT * FROM vehicles'+(' WHERE '+' AND '.join(where) if where else '')+' ORDER BY make,model,year,submodel',args).fetchall()
            return VehicleList(vehicles=[vehicle(conn,r) for r in rows])

    @application.get('/api/vehicles/{key}',response_model=VehicleDetail)
    def vehicle_detail(key:str):
        with db() as conn:
            row=vehicle_row(conn,key);facts=json.loads(row['vehicle_facts'])
            if facts.keys()-set(FIELDS['vehicle']):raise HTTPException(503,'Unexpected vehicle fact field')
            return VehicleDetail(vehicle=vehicle(conn,row),vehicle_facts=facts,hv_gate=hv_gate(conn,row))

    @application.get('/api/vehicles/{key}/batteries',response_model=BatteryList)
    def batteries(key:str,category:Literal['low_voltage','high_voltage']='low_voltage'):
        with db() as conn:
            row=vehicle_row(conn,key)
            if category=='high_voltage':fail('High-voltage systems are suppressed. This demo provides no high-voltage component results or service instructions.')
            gate=hv_gate(conn,row)
            if gate['coverage_blocked']:fail(gate['message'],'HV_COVERAGE_INCOMPLETE')
            rows=conn.execute("SELECT b.* FROM batteries b JOIN fitment_links f USING(battery_id) WHERE f.vehicle_id=? AND b.role='LOW_VOLTAGE' ORDER BY b.battery_id",(key,)).fetchall()
            ambiguity=('The model alone cannot identify which of three auxiliary battery types is installed. Toyota lists all three and does not explain the one-amp difference between Type A and Type B.' if key=='V-910004' else None)
            return BatteryList(vehicle=vehicle(conn,row),batteries=[battery(conn,r) for r in rows],hv_gate=gate,ambiguity=ambiguity)

    @application.get('/api/batteries/{key}',response_model=BatteryDetail)
    def battery_detail(key:str):
        with db() as conn:
            row=conn.execute('SELECT * FROM batteries WHERE battery_id=?',(key,)).fetchone()
            if row is None:raise HTTPException(404,'That battery record is not in this dataset.')
            if row['role']!='LOW_VOLTAGE':fail('High-voltage battery details are suppressed. There is no override in this app.')
            for linked in conn.execute('SELECT vehicle_id FROM fitment_links WHERE battery_id=?',(key,)):
                if hv_gate(conn,vehicle_row(conn,linked['vehicle_id']))['coverage_blocked']:fail('Related hybrid coverage is incomplete. This record is blocked.','HV_COVERAGE_INCOMPLETE')
            return BatteryDetail(battery=battery(conn,row))

    @application.get('/api/sources/{code}',response_model=SourceDetail)
    def source_detail(code:str):
        with db() as conn:return SourceDetail(source=source(conn,code))

    return application


app=create_app()
