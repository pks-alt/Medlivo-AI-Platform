"use client";

import Link from "next/link";
import {useEffect,useState} from "react";

async function load(id:string){
 const r=await fetch("/api/team/candidates/"+id,{cache:"no-store",credentials:"same-origin"});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||"Candidate HTTP "+r.status);
 return b;
}
function scoreBand(v:number){return v>=9?"Strong":v>=8?"Good":v>0?"Needs Review":"Excluded"}
function title(v:any){return String(v||"").replaceAll("_"," ").replace(/\b\w/g,m=>m.toUpperCase())}
function evidenceLabel(x:any){
 if(x?.is_verified)return "Source Confirmed";
 if(x?.source_type==="candidate")return "Candidate Confirmed";
 if(x?.source_type==="resume")return "Resume Evidence";
 if(x?.source_type==="ai"||x?.source_type==="inferred")return "AI Suggested";
 return title(x?.source_type||"Evidence");
}
function readinessLabel(v:any){
 return v==="ready"?"Ready for Recruiter":v==="review"?"Review Needed":"Information Missing";
}

export default function CandidatePage({params}:{params:Promise<{candidateId:string}>}){
 const[c,setC]=useState<any>(null),[err,setErr]=useState("");
 useEffect(()=>{params.then(p=>load(p.candidateId)).then(setC).catch(e=>setErr(e.message))},[params]);

 if(err)return <main className="page"><div className="adminError"><b>Candidate unavailable</b><span>{err}</span></div></main>;
 if(!c)return <main className="page"><div className="adminLoading">Loading Candidate 360...</div></main>;

 const owner=c.owner||{},ready=c.readiness||{},validation=c.validation||{},summary=c.match_summary||{};
 const availability=(c.availability||[])[0]||null,preference=c.preference||{};
 const activeLicenses=(c.licenses||[]).filter((x:any)=>String(x.status||"").toLowerCase()==="active");

 return <main className="page candidate360Page">
  <div className="pageHead">
   <div><small>CANDIDATE 360{c.source?.source_id?" · JobDiva "+c.source.source_id:""}</small><h1>{c.canonical_name||"Candidate"}</h1><p>{[c.profession,c.specialty,[c.city,c.state].filter(Boolean).join(", ")].filter(Boolean).join(" · ")||"Professional profile incomplete"}</p></div>
   <Link className="linkButton" href="/candidates">Back to Candidates</Link>
  </div>

  <section className="candidate360Hero">
   <div><small>TALENT OVERVIEW</small><h2>{c.profession||"Profession pending"}{c.specialty?" · "+c.specialty:""}</h2><p>{owner.division||"Division pending"} · Owner {owner.owner_name||"not assigned"}{owner.manager_name?" · Delivery Manager "+owner.manager_name:""}</p></div>
   <span className={"candidateReadinessBadge "+(ready.status||"information_missing")}>{readinessLabel(ready.status)}</span>
  </section>

  <div className="candidate360Facts">
   <article><small>Lifecycle</small><b>{title(c.lifecycle_status||"unknown")}</b></article>
   <article><small>Availability</small><b>{availability?.available_from||title(availability?.status||"Not confirmed")}</b></article>
   <article><small>Profile freshness</small><b>{c.profile_freshness??"—"}</b></article>
   <article><small>Active licenses</small><b>{activeLicenses.length}</b></article>
   <article><small>Certifications</small><b>{(c.certifications||[]).length}</b></article>
   <article><small>Strong jobs</small><b>{summary.strong??0}</b></article>
   <article><small>Good jobs</small><b>{summary.good??0}</b></article>
   <article><small>Validation</small><b>{title(validation.status||"not_screened")}</b></article>
  </div>

  <section className="candidate360Grid">
   <div className="panelBox"><small>CANDIDATE READINESS</small>
    <div className="candidateReadinessChecks">{(ready.checks||[]).map((x:any)=><span key={x.key} className={x.ready?"ok":"missing"}>{x.ready?"✓":"△"} {x.label}</span>)}</div>
    <div className="candidateReadinessMeta"><b>{ready.resume_count??0}</b><span>resume versions</span><b>{ready.verified_credential_count??0}</b><span>verified credentials</span><b>{ready.evidence_count??0}</b><span>evidence facts</span></div>
   </div>
   <div className="panelBox"><small>MATCH SUMMARY</small>
    <div className="candidateMatchMetrics"><span><b>{summary.strong??0}</b>Strong 9+</span><span><b>{summary.good??0}</b>Good 8-8.9</span><span><b>{summary.excluded??0}</b>Excluded</span></div>
    <p className="sectionHelp">Candidate 360, Job 360 and Match Queue use the same persisted matching results and explanations.</p>
   </div>
  </section>

  <section className="panelBox"><small>PROFESSIONAL DNA</small>
   <div className="candidateDnaGrid">
    <div><span>Profession</span><b>{c.profession||"Not confirmed"}</b></div>
    <div><span>Specialty</span><b>{c.specialty||"Not confirmed"}</b></div>
    <div><span>Location</span><b>{[c.city,c.state].filter(Boolean).join(", ")||"Not confirmed"}</b></div>
    <div><span>Division</span><b>{owner.division||"Not assigned"}</b></div>
    <div><span>Travel / local</span><b>{title(preference.travel_local||"Not confirmed")}</b></div>
    <div><span>Shift preference</span><b>{(preference.shift_preferences||[]).join(", ")||"Not confirmed"}</b></div>
    <div><span>Preferred locations</span><b>{(preference.preferred_locations||[]).join(", ")||"Not confirmed"}</b></div>
    <div><span>Team</span><b>{owner.team_name||"Not assigned"}</b></div>
   </div>
  </section>

  <section className="candidate360Grid">
   <div className="panelBox"><small>LICENSES</small>
    <div className="credentialGrid">{(c.licenses||[]).map((x:any)=><article key={x.id}><b>{x.license_type} {x.state||""}</b><span>{title(x.status||"unknown")}{x.expires_at?" · expires "+x.expires_at:""}</span><em>{title(x.verification_status||"unverified")} · {x.source_system||x.verification_source||"source unknown"}</em></article>)}
    {!(c.licenses||[]).length&&<div className="emptyState">No license records have been enriched yet.</div>}</div>
   </div>
   <div className="panelBox"><small>CERTIFICATIONS</small>
    <div className="credentialGrid">{(c.certifications||[]).map((x:any)=><article key={x.id}><b>{x.certification_name}</b><span>{title(x.status||"unknown")}{x.expires_at?" · expires "+x.expires_at:""}</span><em>{title(x.verification_status||"unverified")} · {x.source_system||x.verification_source||"source unknown"}</em></article>)}
    {!(c.certifications||[]).length&&<div className="emptyState">No certification records have been enriched yet.</div>}</div>
   </div>
  </section>

  <section className="panelBox"><small>VALIDATION & COMPLIANCE READINESS</small>
   <div className="validationHeader"><b>{title(validation.status||"not_screened")}</b><span>{validation.summary||"No job-specific validation has been completed yet."}</span></div>
   {(validation.answers||[]).length>0&&<table className="adminTable"><thead><tr><th>Question</th><th>Answer</th><th>Confirmed</th></tr></thead><tbody>{validation.answers.map((a:any)=><tr key={a.id}><td>{title(a.question_key)}</td><td>{typeof a.answer==="string"?a.answer:JSON.stringify(a.answer)}</td><td>{a.confirmed?"Yes":"No"}</td></tr>)}</tbody></table>}
   <p className="sectionHelp">Phase 1 shows the verified readiness evidence we already have. Future outreach and automated qualification will use this same record rather than a second candidate profile.</p>
  </section>

  <section className="panelBox"><small>BEST CURRENT JOBS</small>
   {(c.best_jobs||[]).length?<div className="candidateBestJobs">{c.best_jobs.map((j:any)=><article className="candidateJobCard" key={j.match_id}>
    <div className="candidateJobHead"><div><b>{j.title}</b><span>{j.division||"Division"} · {[j.city,j.state].filter(Boolean).join(", ")||"Location pending"}{j.start_date?" · Starts "+j.start_date:""}</span></div><strong>{Number(j.overall_score).toFixed(1)}</strong></div>
    <p><b>{scoreBand(Number(j.overall_score))}</b>{((j.explanation||{}).strengths||[]).length?" · "+((j.explanation||{}).strengths||[]).slice(0,3).join(" · "):""}</p>
    {((j.explanation||{}).gaps||[]).length>0&&<div className="candidateGaps">Needs review: {((j.explanation||{}).gaps||[]).slice(0,2).join(" · ")}</div>}
    <div className="candidateJobActions"><Link href={"/jobs/"+j.job_id}>Open Job 360</Link><Link href={"/jobs/"+j.job_id+"/candidates/"+c.id+"/pay-package"}>Pay Package / GM</Link><Link href={"/jobs/"+j.job_id+"/candidates/"+c.id+"/submission"}>Prepare Submission</Link></div>
   </article>)}</div>:<div className="emptyState">No eligible stored job matches are available yet.</div>}
  </section>

  <section className="candidate360Grid">
   <div className="panelBox"><small>EXCLUDED / FAILED JOBS</small>
    {(c.exclusions||[]).length?<div className="candidateExclusionList">{c.exclusions.map((x:any,i:number)=><div key={i}><div><b>{x.job_title||"Job"}</b><span>{title(x.reason_code)}{x.reason_detail?" · "+x.reason_detail:""}</span></div><strong>{x.overridden?"Overridden":"Excluded"}</strong></div>)}</div>:<div className="goodState">No stored hard-gate exclusions for this candidate.</div>}
   </div>
   <div className="panelBox"><small>SUBMISSION HISTORY</small>
    {(c.submissions||[]).length?<div className="candidateSubmissionList">{c.submissions.map((s:any)=><div key={s.id}><div><b>{s.job_title||"Job"}</b><span>{title(s.status)} · {title(s.readiness_status)}{s.submitted_at?" · Submitted "+new Date(s.submitted_at).toLocaleDateString():""}</span></div><Link href={"/funnel/"+s.job_id+"/"+c.id}>Open</Link></div>)}</div>:<div className="emptyState">No submission history is stored for this candidate yet.</div>}
   </div>
  </section>

  <section className="panelBox"><small>EVIDENCE & PROVENANCE</small>
   <div className="candidateEvidenceLegend"><span>Source Confirmed</span><span>Candidate Confirmed</span><span>Resume Evidence</span><span>AI Suggested</span></div>
   <div className="evidenceList">{(c.evidence||[]).slice(0,30).map((x:any)=><article key={x.id}><b>{title(x.fact_key)}</b><p>{typeof x.fact_value==="string"?x.fact_value:JSON.stringify(x.fact_value)}</p><span>{evidenceLabel(x)}{x.confidence!=null?" · confidence "+x.confidence:""}{x.source_reference?" · "+x.source_reference:""}</span></article>)}
   {!(c.evidence||[]).length&&<div className="emptyState">Evidence will appear after JobDiva resume/profile enrichment.</div>}</div>
  </section>

  <section className="candidate360Grid">
   <div className="panelBox"><small>RESUME HISTORY</small>
    {(c.resumes||[]).length?<table className="adminTable"><thead><tr><th>Resume</th><th>Primary</th><th>Resume date</th><th>Updated</th></tr></thead><tbody>{c.resumes.map((x:any)=><tr key={x.id}><td>{x.source_resume_id||"Resume"}</td><td>{x.is_primary?"Yes":"No"}</td><td>{x.resume_date||"—"}</td><td>{x.updated_at?new Date(x.updated_at).toLocaleDateString():"—"}</td></tr>)}</tbody></table>:<div className="emptyState">No resume versions are stored yet.</div>}
   </div>
   <div className="panelBox"><small>DATA QUALITY</small>
    <div className="adminRows">
     <div><span>Source</span><b>{c.source?"JobDiva":"Direct / Canonical Intake"}</b></div>
     <div><span>Source record</span><b>{c.source?.source_id||"Not linked"}</b></div>
     <div><span>Source updated</span><b>{c.source?.source_updated_at?new Date(c.source.source_updated_at).toLocaleString():"Not available"}</b></div>
     <div><span>Enrichment</span><b>{c.source?.enriched_at?"Complete":"Needs review"}</b></div>
     <div><span>Evidence facts</span><b>{ready.evidence_count??0}</b></div>
    </div>
   </div>
  </section>

  <div className="candidate360Boundary"><b>Human decision boundary</b><span>Recruit AI normalizes, validates, ranks and explains. No outreach, qualification call, submission, ownership change or JobDiva writeback happens automatically from Candidate 360 in Phase 1.</span></div>
 </main>;
}
