"use client";

import Link from "next/link";
import {useEffect,useState} from "react";

async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
 return b;
}
function band(v:number){return v>=9?"Strong":v>=8?"Good":v>0?"Needs Review":"Excluded"}
function label(v:any){return String(v||"").replaceAll("_"," ").replace(/\b\w/g,m=>m.toUpperCase())}
function priorityLabel(v:any){
 const value=String(v||"standard");
 return value==="hot"?"Hot":value==="priority"?"High":value==="hold"?"On Hold":"Standard";
}

export default function JobPage({params}:{params:Promise<{jobId:string}>}){
 const[j,setJ]=useState<any>(null),[me,setMe]=useState<any>(null),[e,setE]=useState(""),[working,setWorking]=useState(false),[saved,setSaved]=useState("");
 const[form,setForm]=useState<any>(null);
 async function refresh(id:string){
   const[job,who]=await Promise.all([api("jobs/"+id),api("me")]);setJ(job);setMe(who);
   const o=job.operational||{};
   setForm({
     client_priority:o.client_priority||"normal",job_priority:o.job_priority||"standard",
     priority_reason:o.priority_reason||"",manager_note:o.manager_note||"",next_action:o.next_action||"",
     due_at:o.due_at?new Date(o.due_at).toISOString().slice(0,16):"",
     operational_status:o.operational_status||"active",expected_version:o.version||0
   });
 }
 useEffect(()=>{params.then(p=>refresh(p.jobId)).catch(x=>setE(x.message))},[params]);

 async function saveOperational(){
   if(!j||!form)return;
   setWorking(true);setE("");setSaved("");
   try{
     const payload={...form,due_at:form.due_at?new Date(form.due_at).toISOString():null,
       priority_reason:form.priority_reason.trim()||null,manager_note:form.manager_note.trim()||null,next_action:form.next_action.trim()||null};
     await api("jobs/"+j.id+"/operational",{method:"PUT",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify(payload)});
     await refresh(j.id);setSaved("Operational priority updated and audited.");
   }catch(x:any){setE(x.message)}finally{setWorking(false)}
 }

 if(e&&!j)return <main className="page"><div className="adminError"><b>Job unavailable</b><span>{e}</span></div></main>;
 if(!j||!me||!form)return <main className="page"><div className="adminLoading">Loading Job 360...</div></main>;

 const readiness=j.match_readiness||{},dna=j.job_dna||{},summary=j.match_summary||{},operational=j.operational||{};
 const missing=(readiness.checks||[]).filter((x:any)=>!x.ready);
 const sourceCurrent=Boolean(j.source?.source_updated_at);
 const canManage=["manager","admin"].includes(me.role);

 return <main className="page job360Page">
  <div className="pageHead">
   <div><small>{j.division||"Job"}{j.source?.source_id?" · JobDiva "+j.source.source_id:""}</small><h1>{j.title}</h1><p>{j.customer_name||"Customer pending"} · {[j.city,j.state].filter(Boolean).join(", ")||"Location pending"} · Start {j.start_date||"pending"}</p></div>
   <Link className="linkButton" href="/jobs">Back to Jobs</Link>
  </div>

  {e&&<div className="adminError jobInlineError"><b>Could not save the latest change</b><span>{e}</span></div>}
  {saved&&<div className="goodState jobSaveState">{saved}</div>}

  <section className="job360Hero">
    <div><small>JOB OVERVIEW</small><h2>{j.profession||"Profession pending"}{j.specialty?" · "+j.specialty:""}</h2><p>{j.customer_name||"Customer pending"} · {j.division||"Division pending"} · Owner {j.owner_name||"not assigned"}{j.manager_name?" · Delivery Manager "+j.manager_name:""}</p></div>
    <div className="job360Badges"><span className={"operationalPriority "+String(operational.job_priority||"standard")}>{priorityLabel(operational.job_priority)}</span><span className={"readinessBadge "+(readiness.status||"limited_data")}>{readiness.status==="ready"?"Ready to Match":readiness.status==="needs_review"?"Ready with Review Items":"Not Ready"}</span></div>
  </section>

  <div className="job360Facts">
    <article><small>Status</small><b>{label(operational.operational_status||j.status||"open")}</b></article>
    <article><small>Client priority</small><b>{label(operational.client_priority||"normal")}</b></article>
    <article><small>Start</small><b>{j.start_date||"Pending"}</b></article>
    <article><small>Shift</small><b>{dna.shift||"Not confirmed"}</b></article>
    <article><small>Contract</small><b>{dna.contract_type||dna.duration||"Not confirmed"}</b></article>
    <article><small>Openings</small><b>{dna.openings||"Not confirmed"}</b></article>
    <article><small>Care setting</small><b>{dna.care_setting||"Not confirmed"}</b></article>
    <article><small>EMR</small><b>{dna.emr||"Not confirmed"}</b></article>
  </div>

  {(operational.next_action||operational.priority_reason||operational.due_at)&&<section className="jobNextAction">
    <div><small>MANAGEMENT FOCUS</small><b>{operational.next_action||"Priority job review"}</b><span>{operational.priority_reason||"No priority reason recorded"}{operational.due_at?" · Due "+new Date(operational.due_at).toLocaleString():""}</span></div>
    {operational.manager_note&&<p>{operational.manager_note}</p>}
  </section>}

  {canManage&&<section className="panelBox jobOperationalEditor"><small>DELIVERY MANAGER PRIORITY</small>
    <p className="sectionHelp">Set operating priority and next action without changing the JobDiva requisition. Every save is version-checked and audited.</p>
    <div className="jobOperationalForm">
      <label><span>Job priority</span><select value={form.job_priority} onChange={x=>setForm({...form,job_priority:x.target.value})}><option value="hot">Hot</option><option value="priority">High</option><option value="standard">Standard</option><option value="hold">On Hold</option></select></label>
      <label><span>Client priority</span><select value={form.client_priority} onChange={x=>setForm({...form,client_priority:x.target.value})}><option value="high">High</option><option value="normal">Normal</option><option value="low">Low</option></select></label>
      <label><span>Operational status</span><select value={form.operational_status} onChange={x=>setForm({...form,operational_status:x.target.value})}><option value="active">Active</option><option value="hold">Hold</option><option value="closed">Closed</option></select></label>
      <label><span>Due date / time</span><input type="datetime-local" value={form.due_at} onChange={x=>setForm({...form,due_at:x.target.value})}/></label>
      <label className="wide"><span>Priority reason</span><input value={form.priority_reason} onChange={x=>setForm({...form,priority_reason:x.target.value})} placeholder="Why does this job need special focus?"/></label>
      <label className="wide"><span>Next action</span><input value={form.next_action} onChange={x=>setForm({...form,next_action:x.target.value})} placeholder="Submit two qualified candidates"/></label>
      <label className="wide"><span>Manager note</span><textarea value={form.manager_note} onChange={x=>setForm({...form,manager_note:x.target.value})} placeholder="Internal operating context for the recruiting team"/></label>
      <button disabled={working} onClick={saveOperational}>{working?"Saving...":"Save Priority"}</button>
    </div>
  </section>}

  <section className="job360Grid">
    <div className="panelBox job360Readiness"><small>MATCH READINESS</small>
      <div className="readinessCheckGrid">{(readiness.checks||[]).map((x:any)=><span key={x.key} className={x.ready?"ok":"missing"}>{x.ready?"✓":"△"} {x.label}</span>)}</div>
      <div className="job360ReadinessMeta"><b>{readiness.requirement_count??0}</b><span>normalized requirements</span><b>{readiness.hard_gate_count??0}</b><span>hard gates</span></div>
      {missing.length>0&&<p className="sectionHelp">Matching can still operate with partial data, but the missing items above should be reviewed before treating a weak result as a true talent shortage.</p>}
    </div>

    <div className="panelBox"><small>MATCH SUMMARY</small>
      <div className="job360MatchMetrics"><span><b>{summary.strong??0}</b>Strong 9+</span><span><b>{summary.good??0}</b>Good 8-8.9</span><span><b>{summary.excluded??0}</b>Excluded</span></div>
      <p className="sectionHelp">The same stored matching intelligence powers Job 360 and Match Queue. No separate scoring logic is used here.</p>
    </div>
  </section>

  <section className="panelBox"><small>JOB DNA</small>
    <div className="jobDnaGrid">
      <div><span>Profession</span><b>{j.profession||"Not confirmed"}</b></div>
      <div><span>Specialty</span><b>{j.specialty||"Not confirmed"}</b></div>
      <div><span>Division</span><b>{j.division||"Not assigned"}</b></div>
      <div><span>Location</span><b>{[j.city,j.state].filter(Boolean).join(", ")||"Not confirmed"}</b></div>
      <div><span>Schedule</span><b>{dna.schedule||"Not confirmed"}</b></div>
      <div><span>Call</span><b>{dna.call||"Not confirmed"}</b></div>
      <div><span>Team</span><b>{j.team_name||"Not assigned"}</b></div>
      <div><span>Recruiter owner</span><b>{j.owner_name||"Not assigned"}</b></div>
    </div>
  </section>

  <section className="job360Grid">
    <div className="panelBox"><small>MUST HAVE · HARD GATES</small>
      <div className="requirementList">{(j.hard_gates||[]).map((r:any)=><article key={r.id} className="hardReq"><div><b>{label(r.canonical_key)}</b><span>{label(r.requirement_type)}</span></div><strong>{typeof r.value==="string"?r.value:JSON.stringify(r.value)}</strong><em>HARD GATE</em></article>)}</div>
      {!(j.hard_gates||[]).length&&<div className="emptyState">No hard-gate requirements have been normalized yet.</div>}
    </div>
    <div className="panelBox"><small>PREFERRED · RANKING FACTORS</small>
      <div className="requirementList">{(j.preferences||[]).map((r:any)=><article key={r.id} className="softReq"><div><b>{label(r.canonical_key)}</b><span>{label(r.requirement_type)}</span></div><strong>{typeof r.value==="string"?r.value:JSON.stringify(r.value)}</strong><em>PREFERENCE</em></article>)}</div>
      {!(j.preferences||[]).length&&<div className="emptyState">No preferred ranking factors have been normalized yet.</div>}
    </div>
  </section>

  <section className="panelBox"><small>BEST CANDIDATES</small>
    {(j.best_candidates||[]).length?<div className="jobCandidateList">{j.best_candidates.map((c:any)=><article className="jobCandidateCard" key={c.match_id}>
      <div className="jobCandidateHead"><div><b>{c.canonical_name||"Candidate"}</b><span>{[c.profession,c.specialty,[c.city,c.state].filter(Boolean).join(", ")].filter(Boolean).join(" · ")}</span></div><strong>{Number(c.overall_score).toFixed(1)}</strong></div>
      <p><b>{band(Number(c.overall_score))}</b>{((c.explanation||{}).strengths||[]).length?" · "+((c.explanation||{}).strengths||[]).slice(0,3).join(" · "):""}</p>
      {((c.explanation||{}).gaps||[]).length>0&&<div className="candidateGaps">Needs review: {((c.explanation||{}).gaps||[]).slice(0,2).join(" · ")}</div>}
      <div className="jobCandidateActions"><Link href={"/candidates/"+c.candidate_id}>Open Candidate 360</Link><Link href={"/jobs/"+j.id+"/candidates/"+c.candidate_id+"/pay-package"}>Pay Package / GM</Link><Link href={"/jobs/"+j.id+"/candidates/"+c.candidate_id+"/submission"}>Prepare Submission</Link></div>
    </article>)}</div>:<div className="emptyState">No eligible stored matches are available yet. Review Match Readiness before treating this as a sourcing shortage.</div>}
  </section>

  <section className="panelBox"><small>EXCLUDED CANDIDATES</small>
    {(j.exclusions||[]).length?<table className="adminTable"><thead><tr><th>Candidate</th><th>Reason</th><th>Detail</th><th>Override</th></tr></thead><tbody>{j.exclusions.map((x:any,i:number)=><tr key={i}><td>{x.canonical_name||"Candidate"}</td><td>{label(x.reason_code)}</td><td>{x.reason_detail||"No additional detail"}</td><td>{x.overridden?"Overridden":"No"}</td></tr>)}</tbody></table>:<div className="goodState">No stored hard-gate exclusions for this job.</div>}
  </section>

  <section className="job360Grid">
    <div className="panelBox"><small>SUBMISSION & COMMERCIAL PATH</small>
      <div className="job360Path">
        <div><b>Candidate selected</b><span>Open Candidate 360 and validate evidence.</span></div>
        <div><b>Pay Package / GM</b><span>Use the existing commercial workflow for serious candidates.</span></div>
        <div><b>Prepare Submission</b><span>Submission Studio applies customer/program requirements and human review.</span></div>
      </div>
    </div>
    <div className="panelBox"><small>DATA QUALITY & PROVENANCE</small>
      <div className="adminRows">
        <div><span>Source</span><b>{j.source?"JobDiva":"Direct / Canonical Intake"}</b></div>
        <div><span>Source record</span><b>{j.source?.source_id||"Not linked"}</b></div>
        <div><span>Source freshness</span><b>{sourceCurrent?new Date(j.source.source_updated_at).toLocaleString():"Not available"}</b></div>
        <div><span>Enrichment</span><b>{j.source?.enriched_at?"Complete":"Needs review"}</b></div>
        <div><span>Enrichment version</span><b>{j.source?.enrichment_version||"Not available"}</b></div>
      </div>
    </div>
  </section>

  <div className="job360Boundary"><b>Human decision boundary</b><span>Recruit AI normalizes, ranks and explains. Recruiters and managers make the recruiting decision. No outreach, submission, ownership change or JobDiva writeback happens automatically from Job 360.</span></div>
 </main>;
}
