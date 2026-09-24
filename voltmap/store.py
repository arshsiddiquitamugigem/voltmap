"""Four tables, original cell text, two closed key sets. No subject splitting."""
import argparse
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit, urlunsplit

from .legacy_loader import load_workbook, LAYOUT
from .models import FIELDS, Specification

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT/'data/voltmap_dev.sqlite'
WORKBOOK = ROOT/'data/VOLTMAP_Sample_Dataset.xlsx'
INPUT_SHA = '92b6959c218151d0cc85a5311eceb720fc6475a30bceb7f895dd2438368c36b0'
V, B, S = '01_vehicles','02_battery_specifications','01b_sources'
LINK = 'linked_vcdb_vehicle_ids (Sheet 1)'


def encoded(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False)


def connect(path=DATABASE, readonly=True):
    path = Path(path).resolve()
    conn = sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) if readonly else sqlite3.connect(path)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def schema():
    # These INSERT/UPDATE guards only enforce closed field names, not JSON source references.
    base = '''
    PRAGMA foreign_keys=ON;
    PRAGMA user_version=1;
    CREATE TABLE sources(source_id INTEGER PRIMARY KEY, metadata TEXT NOT NULL CHECK(json_valid(metadata)), partition TEXT NOT NULL CHECK(partition='dev'));
    CREATE TABLE vehicles(vehicle_id TEXT PRIMARY KEY, legacy_vehicle_ref TEXT UNIQUE NOT NULL,
      canonical_vehicle_id INTEGER, canonical_base_vehicle_id INTEGER, canonical_engine_config_id INTEGER,
      legacy_data_source_id INTEGER NOT NULL, year INTEGER NOT NULL, make TEXT NOT NULL, model TEXT NOT NULL,
      submodel TEXT NOT NULL, engine TEXT NOT NULL, drive_type TEXT NOT NULL, status TEXT NOT NULL,
      vehicle_facts TEXT NOT NULL CHECK(json_valid(vehicle_facts)), partition TEXT NOT NULL CHECK(partition='dev'));
    CREATE TABLE batteries(battery_id TEXT PRIMARY KEY, record_kind TEXT NOT NULL CHECK(record_kind='LEGACY_UNSPLIT'),
      role TEXT NOT NULL CHECK(role IN ('LOW_VOLTAGE','HV_TRACTION','UNRESOLVED')),
      application TEXT NOT NULL, designation TEXT NOT NULL, verification_status TEXT NOT NULL,
      field_provenance TEXT NOT NULL CHECK(json_valid(field_provenance)),
      record_metadata TEXT NOT NULL CHECK(json_valid(record_metadata)), partition TEXT NOT NULL CHECK(partition='dev'));
    CREATE TABLE fitment_links(vehicle_id TEXT NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE RESTRICT,
      battery_id TEXT NOT NULL REFERENCES batteries(battery_id) ON DELETE RESTRICT,
      confidence_tier TEXT CHECK(confidence_tier IS NULL), partition TEXT NOT NULL CHECK(partition='dev'),
      PRIMARY KEY(vehicle_id,battery_id));
    '''
    for table,column,keys in [('vehicles','vehicle_facts',FIELDS['vehicle']),('batteries','field_provenance',FIELDS['battery'])]:
        allowed=','.join("'"+x+"'" for x in keys)
        for event in ('INSERT','UPDATE'):
            base+=f'''CREATE TRIGGER {table}_{event.lower()}_keys BEFORE {event} ON {table} BEGIN
              SELECT CASE WHEN json_type(NEW.{column})<>'object' OR EXISTS
              (SELECT 1 FROM json_each(NEW.{column}) WHERE key NOT IN ({allowed}))
              THEN RAISE(ABORT,'closed specification key set') END;
              SELECT CASE WHEN EXISTS(SELECT key FROM json_each(NEW.{column}) GROUP BY key HAVING count(*)>1)
              THEN RAISE(ABORT,'duplicate specification key') END;
            END;'''
    return base


def url_key(url):
    u=urlsplit(url)
    return urlunsplit((u.scheme.lower(),u.netloc.lower(),u.path.rstrip('/'),u.query,''))


def source_ids(text):
    return sorted(set(re.findall(r'\bS\d+\b',text)))


def build(workbook=WORKBOOK, output=DATABASE):
    output=Path(output)
    if output.exists():raise ValueError('Choose a new database path; the importer does not overwrite files.')
    loaded=load_workbook(workbook,'dev')
    if loaded['sha256']!=INPUT_SHA:raise ValueError('Workbook changed; review the import before using a different dataset.')
    if not loaded['ok'] or loaded['quarantined']:raise ValueError('Loader rejected records; see loader findings.')
    rows=[r for part in ('research_candidates','synthetic_candidates') for group in loaded[part].values() for r in group]
    groups={s:[r for r in rows if r['sheet']==s] for s in (V,B,S)}
    src={r['values']['id']:r['values'] for r in groups[S]}
    urls={url_key(r['URL']):sid for sid,r in src.items() if r['URL'].startswith(('http://','https://'))}
    output.parent.mkdir(parents=True,exist_ok=True)
    conn=connect(output,False)
    try:
        conn.executescript(schema())
        with conn:
            for sid,value in src.items():conn.execute('INSERT INTO sources VALUES (?,?,?)',(int(sid[1:]),encoded(value),'dev'))
            for sheet in (V,B):
                for rec in groups[sheet]:
                    values=rec['values']; key=values[LAYOUT['sheets'][sheet]['key']]
                    notes=values.get('verification_notes',values.get('electrical_verification_notes',''))
                    context=source_ids(notes+' '+values.get('electrical_source_refs',''))
                    for url in re.findall(r'https?://[^\s]+',values.get('source_links','')):
                        if url_key(url) in urls:context.append(urls[url_key(url)])
                    context=sorted(set(context)&src.keys())
                    fields={}
                    for field in FIELDS['vehicle' if sheet==V else 'battery']:
                        origin='aux_12v_battery' if field=='aux_12v_battery_presence' else field
                        text=values.get(origin,'')
                        direct=sorted(set(source_ids(text))&src.keys())
                        locator=None
                        # These exact associations were already documented and approved; no new facts.
                        if key in {'B-RAV-00A','B-RAV-00B','B-RAV-00C'} and field in {'nominal_voltage_v','rated_capacity_ah','cold_cranking_amps_cca'}:
                            direct=['S29'];locator='OM0R010U, printed p.662; capacity and CCA are minimum replacement requirements.'
                        prov=dict(workbook_sha256=loaded['sha256'],sheet=sheet,row=rec['row'],column=origin,
                            source_ids=direct or context,association='explicit_field_reference' if direct else ('record_citations_only' if context else 'no_source_recorded'),
                            basis_tags=[x for x in FIELDS['basis_tags'] if x in text],verification_status=values.get('verification_status',values.get('electrical_data_status')),
                            record_review_date=values.get('verification_date') or None,locator=locator)
                        fields[field]=Specification(text=text,provenance=prov).model_dump()
                    if sheet==V:
                        conn.execute('INSERT INTO vehicles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            ('V-'+key,key,None,None,None,int(values['data_source_id']),int(values['year']),values['make'],values['model'],values['submodel'],
                             values['engine_liters']+' L · '+values['engine_code'],values['drive_type'],values['electrical_data_status'],encoded(fields),'dev'))
                    else:
                        application=values['battery_application']
                        role='HV_TRACTION' if 'Traction' in application else ('LOW_VOLTAGE' if application.startswith(('Starting','Auxiliary')) else 'UNRESOLVED')
                        metadata={k:v for k,v in values.items() if k not in FIELDS['battery']}
                        conn.execute('INSERT INTO batteries VALUES (?,?,?,?,?,?,?,?,?)',
                            (key,'LEGACY_UNSPLIT',role,application,values['designation'],values['verification_status'],encoded(fields),encoded(metadata),'dev'))
                        for ref in values[LINK].split(';'):
                            conn.execute('INSERT INTO fitment_links VALUES (?,?,?,?)',('V-'+ref.strip(),key,None,'dev'))
            if conn.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Broken native foreign key')
        counts={t:conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('vehicles','batteries','sources','fitment_links')}
        if counts['batteries']!=13:raise ValueError('Expected all 13 linked battery rows')
        report={'partition':'dev','workbook_sha256':loaded['sha256'],'counts':counts,'excluded_pending_templates':3,
                'vehicle_battery_specs_duplicated':False,'subject_splits_performed':0,'confidence_tiers_assigned':0,
                'source_id_999_and_canonical_placeholders_resolved':False,'loader_findings':loaded['findings']}
        output.with_suffix('.import.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        return report
    except Exception:
        conn.close();output.unlink(missing_ok=True);raise
    finally:conn.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workbook',type=Path,default=WORKBOOK);p.add_argument('--output',type=Path,default=DATABASE)
    args=p.parse_args();print(json.dumps(build(args.workbook,args.output),indent=2))
