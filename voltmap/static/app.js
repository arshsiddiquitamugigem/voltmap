/* Plain local UI. No external libraries, analytics, generated data or tier grading. */
const root=document.getElementById('app');
const state={vehicles:[],selected:null,filters:{year:'',make:'',model:'',submodel:''},request:0};
const human=s=>String(s??'').replace(/VIN-specific/g,'configuration-specific');
const h=s=>human(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const href=s=>encodeURIComponent(s);
const field=(b,k)=>b.field_provenance[k]?.text??'Not publicly verified';
const clean=s=>human(s).replace(/\s*\[(?:OEM|aftermarket|BCI|calculated|inferred)[^\]]*\]/g,'').trim();
const badge=s=>`<span class="pill ${s==='Conflicting sources'?'conflict':s==='Pending'?'pending':''}">${h(s)}</span>`;
const labels={cold_cranking_amps_cca:'Cold cranking amps (CCA)',rated_capacity_ah:'Rated capacity (Ah)',nominal_voltage_v:'Nominal voltage (V)',battery_group_size:'Battery group / case',battery_type_chemistry:'Chemistry',cranking_amps_ca:'Cranking amps (CA)',reserve_capacity_min:'Reserve capacity (minutes)',energy_capacity_wh_kwh:'Energy capacity',battery_dimensions_lxwxh:'Dimensions · L × W × H',battery_weight:'Weight',terminal_type_and_orientation:'Terminals and orientation',warranty:'Warranty'};
const label=k=>labels[k]||k.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());

async function api(path){const r=await fetch(path);const data=await r.json();if(!r.ok){const e=new Error(data.message||'The record is unavailable.');e.data=data;throw e;}return data;}
function nav(step,vehicle=null,battery=null){
 document.getElementById('breadcrumb').textContent=['Research / Vehicle selection','Research / Selected vehicle','Research / Recorded specification'][step];
 ['select','results','evidence'].forEach((n,i)=>document.getElementById('nav-'+n).classList.toggle('active',i===step));
 const results=document.getElementById('nav-results'),evidence=document.getElementById('nav-evidence');
 results.href=vehicle?'#/vehicle/'+href(vehicle):'#/';results.setAttribute('aria-disabled',String(!vehicle));
 evidence.href=battery?'#/battery/'+href(battery)+'/'+href(vehicle):'#/';evidence.setAttribute('aria-disabled',String(!battery));
}
document.querySelectorAll('nav a').forEach(a=>a.addEventListener('click',e=>{if(a.getAttribute('aria-disabled')==='true')e.preventDefault();}));
document.getElementById('close-dialog').onclick=()=>document.getElementById('safety-dialog').close();

function picker(){
 nav(0);const opts=(key,title)=>`<label>${title}<select id="filter-${key}"><option value="">All ${title.toLowerCase()}s</option>${[...new Set(state.vehicles.map(v=>v[key]))].sort((a,b)=>String(a).localeCompare(String(b),undefined,{numeric:true})).map(x=>`<option value="${h(x)}" ${String(x)===state.filters[key]?'selected':''}>${h(x)}</option>`).join('')}</select></label>`;
 root.innerHTML=`<div class="hero-line"><div><p class="eyebrow">A DEMO OF WHAT WE CAN — AND CAN’T — KNOW</p><h1>See the evidence.<br>Keep the uncertainty.</h1><p class="intro">Explore recorded battery specifications, the sources behind them, and the details a vehicle model alone can’t resolve.</p></div><div class="hero-counter"><strong>13</strong><span>battery research records<br>Honda + Toyota</span></div></div>
 <div class="demo-cards"><article class="demo-card featured"><p class="eyebrow">START WITH THE HONESTY DEMO</p><h3>One RAV4. Three battery types.</h3><p>The manual lists all three. The model alone can’t tell us which one is installed.</p><a class="text-link" href="#/vehicle/V-910004">Explore the ambiguity <span class="arrow">↗</span></a><div class="battery-symbol" aria-hidden="true"><span>?</span></div></article>
 <article class="demo-card"><p class="eyebrow">A SECOND KIND OF UNCERTAINTY</p><h3>When the sources disagree.</h3><p>The Civic’s H5 / 51R findings stay visible, with no winner selected.</p><a class="text-link" href="#/vehicle/V-910023">Read the Civic findings <span class="arrow">↗</span></a></article></div>
 <div class="section-title"><h2>Or select a recorded vehicle</h2><span class="small-note">${state.vehicles.length} configurations · limited research coverage</span></div><div class="picker">${opts('year','Year')}${opts('make','Make')}${opts('model','Model')}${opts('submodel','Trim')}</div><div class="section-title" style="margin-top:18px"><span class="small-note" id="filter-count"></span><button class="secondary" id="clear-filters">Clear filters</button></div><div class="vehicle-list" id="vehicle-list"></div>`;
 for(const key of Object.keys(state.filters))document.getElementById('filter-'+key).onchange=e=>{state.filters[key]=e.target.value;drawVehicles();};
 document.getElementById('clear-filters').onclick=()=>{for(const k of Object.keys(state.filters)){state.filters[k]='';document.getElementById('filter-'+k).value='';}drawVehicles();};drawVehicles();
}
function drawVehicles(){
 const rows=state.vehicles.filter(v=>Object.entries(state.filters).every(([k,x])=>!x||String(v[k])===x));
 document.getElementById('filter-count').textContent=`${rows.length} matching configuration${rows.length===1?'':'s'} · no nearest-match guessing`;
 document.getElementById('vehicle-list').innerHTML=rows.length?rows.map(v=>`<a class="vehicle-row" href="#/vehicle/${href(v.vehicle_id)}"><div><div class="vehicle-name">${h(v.year)} ${h(v.make)} ${h(v.model)} · ${h(v.submodel)}</div><div class="vehicle-sub">${h(v.engine)} · ${h(v.drive_type)}</div></div><div class="vehicle-action">${badge(v.battery_records?'Research recorded':'Pending')}<span>${v.battery_records?'Read findings':'No battery research'} →</span></div></a>`).join(''):`<div class="empty"><h3>No matching vehicle in this dataset.</h3><p>Change the filters to explore a recorded configuration. We won’t substitute a different trim.</p></div>`;
}

function batteryCard(b,rav,v){
 const type=rav?'Type '+b.battery_id.slice(-1):b.designation;
 const source=b.sources.find(x=>x.source_id==='S29');
 return `<article class="battery-card"><div class="application">${h(b.application)}</div><h3>${h(type)}</h3>${rav?`<div class="cca">${h(field(b,'cold_cranking_amps_cca'))}<span>CCA</span></div><div class="cca-caption">Minimum replacement requirement<br>Installed type unresolved</div>`:`<div class="long-claim">${h(field(b,'battery_group_size'))}</div><div class="cca-caption" style="margin-top:12px">Recorded group / case finding</div>`}
 <div class="card-meta">${rav?`<div><span>Minimum capacity · 20-hour rate</span>${h(field(b,'rated_capacity_ah'))} Ah</div><div><span>Nominal voltage</span>${h(field(b,'nominal_voltage_v'))} V</div>`:`<div><span>Recorded CCA · subject qualifiers retained</span>${h(field(b,'cold_cranking_amps_cca'))}</div><div><span>Chemistry</span>${h(field(b,'battery_type_chemistry'))}</div>`}</div>
 <div class="card-footer">${badge(b.verification_status)}<p>Confidence tier: not evaluated</p>${rav?`<p>Toyota OM0R010U · p.662</p>`:''}<a href="#/battery/${href(b.battery_id)}/${href(v.vehicle_id)}">View recorded specs & evidence <span>↗</span></a></div></article>`;
}

function renderResults(data){
 const v=data.vehicle,rav=!!data.ambiguity,conflict=data.batteries.some(b=>b.verification_status==='Conflicting sources');state.selected=v.vehicle_id;nav(1,v.vehicle_id);
 root.innerHTML=`<a class="back" href="#/">← Change vehicle</a><div class="selected"><div class="selected-label">Selected vehicle</div><h1>${h(v.year)} ${h(v.make)} ${h(v.model)} ${h(v.submodel)}</h1><div class="chips"><span>${h(v.engine)}</span><span>${h(v.drive_type)}</span><span>Local research reference · canonical mapping pending</span></div></div>
 ${rav?`<section class="honesty"><p class="eyebrow">WHAT THE MODEL ALONE CAN’T RESOLVE</p><h2>Which of three battery types is installed?</h2><p>Toyota lists Type A, Type B and Type C for this auxiliary application. Check the label on your battery, or keep all three possibilities visible.</p><div class="row-actions"><button class="quiet-button" id="label-help">What should I check?</button><span class="small-note">“Not sure” is a valid answer.</span></div><div class="hint" id="label-hint" hidden>Look for identifying text on the battery label. If you cannot match it confidently, leave “Not sure — show all” selected. Filtering these research records does not confirm physical fit or installation.</div></section>`:conflict?`<section class="honesty"><p class="eyebrow">CONFLICTING SOURCES</p><h2>The recorded findings do not establish one fitment.</h2><p>Competing group-size claims are retained below. A standard-trim finding is not evidence for a performance trim. Follow the sources before accepting a fitment.</p></section>`:`<div class="notice">These are research records, not approved replacement recommendations. Original qualifiers, gaps and source limitations remain visible.</div>`}
 <div class="result-layout"><section><div class="section-title"><h2>${rav?'Three documented alternatives':'Recorded battery research'}</h2><span class="small-note">${data.batteries.length} low-voltage record${data.batteries.length===1?'':'s'}</span></div>
 ${rav?`<div class="type-filter" aria-label="Filter battery research by label"><button class="active" data-type="all">Not sure — show all</button><button data-type="A">Label says Type A</button><button data-type="B">Label says Type B</button><button data-type="C">Label says Type C</button></div>`:''}<div id="battery-grid" class="battery-grid ${rav?'':'single'}"></div>
 ${rav?`<p class="date-note" style="margin-top:17px">285 / 286 / 345 CCA are printed in Toyota’s manual. The one-amp A/B difference is retained exactly; Toyota does not explain it. These minimums are not service-product ratings.</p>`:''}</section>
 <aside class="side-panel"><div><p class="eyebrow">WHAT THIS RESULT MEANS</p><h3>Evidence, with its limits.</h3><p>Each number stays attached to its recorded source context. “Partially verified” is a research status, not a confidence tier or fitment approval.</p><div class="divider"></div><h3>Still unresolved</h3><p>Canonical identity, source mappings and physical fit have not been approved. Confidence tiers remain unassigned.</p></div><div><div class="divider"></div><p class="eyebrow">HIGH-VOLTAGE BOUNDARY</p><p>${data.hv_gate.traction_records?'Auxiliary and traction records are present. High-voltage details remain suppressed.':'This demo does not provide high-voltage components or service instructions.'}</p><button class="safety-button" id="hv-button">Why are high-voltage results blocked? ↗</button></div></aside></div>`;
 const grid=document.getElementById('battery-grid');const draw=type=>{const rows=data.batteries.filter(b=>type==='all'||b.battery_id.endsWith(type));grid.innerHTML=rows.length?rows.map(b=>batteryCard(b,rav,v)).join(''):`<div class="empty"><h3>No battery research for this configuration yet.</h3><p>This vehicle is recorded, but no linked battery row is available. No substitute has been selected.</p></div>`;};draw('all');
 if(rav){document.getElementById('label-help').onclick=()=>{const p=document.getElementById('label-hint');p.hidden=!p.hidden;};document.querySelectorAll('[data-type]').forEach(btn=>btn.onclick=()=>{document.querySelectorAll('[data-type]').forEach(x=>x.classList.toggle('active',x===btn));draw(btn.dataset.type);});}
 document.getElementById('hv-button').onclick=async()=>{try{await api('/api/vehicles/'+href(v.vehicle_id)+'/batteries?category=high_voltage');}catch(e){document.getElementById('safety-message').textContent=e.message;document.getElementById('safety-dialog').showModal();}};
}

function renderEvidence(data,vehicle){
 const b=data.battery;nav(2,vehicle,b.battery_id);
 const review=Object.values(b.field_provenance)[0]?.provenance.record_review_date;
 root.innerHTML=`<a class="back" href="#/vehicle/${href(vehicle)}">← Back to findings</a><p class="eyebrow">FOLLOW THE EVIDENCE</p><h1>${h(b.battery_id.startsWith('B-RAV-00')?'RAV4 · Type '+b.battery_id.slice(-1):b.designation)}</h1><div class="chips"><span>${h(b.application)}</span><span>${h(b.battery_id)}</span><span>Confidence tier: not evaluated</span></div>${badge(b.verification_status)}
 <div class="notice">Values below preserve the recorded wording. A row citation does not verify every field. Status and review date apply to the record; field-level verification has not been inferred.</div>
 <div class="evidence-layout"><section><div class="evidence-search"><label for="spec-search">Find a specification<input id="spec-search" type="search" placeholder="Search group, capacity, chemistry…"></label></div><div class="spec-table"><div class="spec-head">RECORDED CLAIM &nbsp; / &nbsp; PROVENANCE</div><div id="spec-rows"></div></div><p class="date-note" style="margin-top:14px">High-voltage fields are suppressed in this consumer view. The complete original rows and notes remain intact in the database and source workbook.</p></section><aside class="evidence-sidebar"><h2>Sources on record</h2><p class="date-note">Record review: ${h(review?review.slice(0,10):'not recorded')}<br>Source dates below are recorded checks, not fresh link checks.</p>${b.sources.length?b.sources.map(s=>`<article class="source-card" id="source-${h(s.source_id)}"><span class="source-id">${h(s.source_id)} · Source quality ${h(s.quality_tier)}</span><h3>${h(s.title)}</h3><p>${h(s.source_type)}<br>Recorded check: ${h(s.checked_at?s.checked_at.slice(0,10):'not recorded')}</p>${s.url?`<a href="${h(s.url)}" target="_blank" rel="noopener noreferrer">Open cited source ↗</a>`:`<p>No URL on record</p>`}</article>`).join(''):`<div class="source-card"><p>No source citations are recorded for these fields.</p></div>`}</aside></div>`;
 const draw=query=>{const rows=Object.entries(b.field_provenance).filter(([k,s])=>(label(k)+' '+s.text).toLowerCase().includes(query.toLowerCase()));
 document.getElementById('spec-rows').innerHTML=rows.length?rows.map(([k,s])=>{const p=s.provenance,unknown=/^(Not publicly verified|N\/A|PENDING|Unknown|$)/i.test(s.text);return `<article class="spec-row"><div class="field-name">${h(label(k))}</div><p class="field-value ${unknown?'unknown':''}">${h(s.text||'Blank in source record — no value inferred')}</p><div class="provenance"><span>${h(p.association==='explicit_field_reference'?'Field reference recorded':p.association==='record_citations_only'?'Row citations only; field association unverified':'No supporting source recorded')}</span>${p.source_ids.map(id=>`<a href="#" data-source="${h(id)}">${h(id)}</a>`).join('')}<span>${h(p.basis_tags.length?p.basis_tags.join(' · '):unknown?'No basis assigned to this marker':'No field basis tag recorded')}</span><span>Workbook row ${p.row}</span></div>${p.locator?`<div class="date-note" style="margin-top:7px">${h(p.locator)}</div>`:''}</article>`;}).join(''):`<div class="empty">No recorded fields match that search.</div>`;
 document.querySelectorAll('[data-source]').forEach(a=>a.onclick=e=>{e.preventDefault();const target=document.getElementById('source-'+a.dataset.source);if(target){target.scrollIntoView({behavior:'smooth',block:'center'});target.animate([{background:'#dfebd9'},{background:'#fff'}],{duration:1000});}});};
 document.getElementById('spec-search').oninput=e=>draw(e.target.value);draw('');
}

async function route(){
 const request=++state.request;const parts=location.hash.replace(/^#\/?/,'').split('/').map(decodeURIComponent);root.innerHTML='<p class="loading">Reading the local records…</p>';
 try{
  if(!state.vehicles.length)state.vehicles=(await api('/api/vehicles')).vehicles;
  if(parts[0]==='vehicle'&&parts[1]){const data=await api('/api/vehicles/'+href(parts[1])+'/batteries');if(request!==state.request)return;renderResults(data);}
  else if(parts[0]==='battery'&&parts[1]&&parts[2]){const data=await api('/api/batteries/'+href(parts[1]));if(request!==state.request)return;renderEvidence(data,parts[2]);}
  else if(parts[0]){throw new Error('This page is not in the demo. Return to vehicle selection.');}
  else{if(request!==state.request)return;picker();}
 }catch(e){if(request!==state.request)return;root.innerHTML=`<a class="back" href="#/">← Vehicle selection</a><div class="empty"><p class="eyebrow">NO RESULT RETURNED</p><h2>${h(e.data?.code==='HV_COVERAGE_INCOMPLETE'?'Coverage gate blocked this result.':'This record is unavailable.')}</h2><p>${h(e.message)}</p></div>`;}
 window.scrollTo(0,0);root.focus({preventScroll:true});
}
window.addEventListener('hashchange',route);route();
