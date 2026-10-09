"use client";
import {useEffect,useState} from "react";

async function load(id:string){
 const r=await fetch("/api/team/candidates/"+id,{cache:"no-store",credentials:"same-origin"});
 if(!r.ok) throw new Error("Candidate HTTP "+r.status);
 return r.json();
}
function scoreBand(v:number){return v>=9?"Strong":v>=8?"Good":v>0?"Needs Review":"Excluded"}
function sourceLabel(x:any){if(x?.is_verified)return "Source Confirmed"; if(x?.source_type==="resume")return "Resume Evidence"; if(x?.source_type==="candidate")return "Candidate Confirmed"; return x?.source_type||"Evidence"}
export default function CandidatePage({params}:{params:Promise<{candidateId:string}>}){
 const [id,setId]=useState(""); const [c,setC]=useState<any>(null); const [err,setErr]=useState("");
 useEffect(()=>{params.then(p=>{setId(p.candidateId);return load(p.candidateId)}).then(setC).catch(e=>setErr(e.message))},[params]);
 if(err)return <main className="page"><div className="adminError"><b>Candidate unavailable</b><span>{err}</span></div></main>;
 if(!c)return <main className="page"><div className="adminLoading">Loading Candidate 360…</div></main>;
 const profile=c.canonical_profile||{}; const validation=c.validation||{};
 return <main className="page">
  <div className="pageHead"><div><small>Candidate 360 {c.source?.source_id?"· JobDiva "+c.source.source_id:""}</small><h1>{c.canonical_name||"Candidate"}</h1><p>{c.profession||"Profession unknown"}{c.specialty?" · "+c.specialty:""} · {[c.city,c.state].filter(Boolean).join(", ")||"Location unknown"}</p></div><div className="pageActions"><a href="/candidates">Candidates</a><a href="/admin">Admin</a></div></div>

  <div className="profileStrip">
   <span><b>{c.lifecycle_status||"—"}</b>Lifecycle</span><span><b>{c.profile_freshness??"—"}</b>Profile freshness</span><span><b>{validation.status||"not_screened"}</b>Validation</span><span><b>{(c.licenses||[]).length}</b>Licenses</span><span><b>{(c.certifications||[]).length}</b>Certifications</span>
  </div>

  <div className="detailGrid">
   <section className="panelBox"><small>Professional profile</small><div className="requirements">
    <div><span>Profession</span><b>{c.profession||"Unknown"}</b></div><div><span>Specialty</span><b>{c.specialty||"Unknown"}</b></div><div><span>Location</span><b>{[c.city,c.state].filter(Boolean).join(", ")||"Unknown"}</b></div><div><span>JobDiva enriched</span><b>{c.source?.enriched_at?"Yes":"Not yet"}</b></div>
   </div>{Object.keys(profile).length>0&&<pre className="jsonBlock compactJson">{JSON.stringify(profile,null,2)}</pre>}</section>

   <section className="panelBox"><small>Licenses & certifications</small><div className="credentialGrid">
    {(c.licenses||[]).map((x:any)=><article key={x.id}><b>{x.license_type} {x.state||""}</b><span>{x.status||"Unknown"} · expires {x.expires_at||"Unknown"}</span><em>{x.verification_status||"unverified"} · {x.source_system||"source unknown"}</em></article>)}
    {(c.certifications||[]).map((x:any)=><article key={x.id}><b>{x.certification_name}</b><span>{x.status||"Unknown"} · expires {x.expires_at||"Unknown"}</span><em>{x.verification_status||"unverified"} · {x.source_system||"source unknown"}</em></article>)}
    {!(c.licenses||[]).length&&!(c.certifications||[]).length&&<div className="emptyState">No credential records have been enriched yet.</div>}
   </div></section>

   <section className="panelBox"><small>Candidate Validation & Readiness</small>
    <div className="validationHeader"><b>{String(validation.status||"not_screened").replaceAll("_"," ")}</b><span>{validation.summary||"No job-specific validation has been completed yet."}</span></div>
    <div className="validationSteps">{["not_screened","screening_started","information_missing","candidate_confirmed","recruiter_review_needed","ready_for_recruiter"].map((s:string)=><span className={validation.status===s?"current":""} key={s}>{s.replaceAll("_"," ")}</span>)}</div>
    {(validation.answers||[]).length>0&&<table className="adminTable"><thead><tr><th>Question</th><th>Answer</th><th>Confirmed</th></tr></thead><tbody>{validation.answers.map((a:any)=><tr key={a.id}><td>{a.question_key}</td><td>{JSON.stringify(a.answer)}</td><td>{a.confirmed?"Yes":"No"}</td></tr>)}</tbody></table>}
   </section>

   <section className="panelBox"><small>Evidence & provenance</small><div className="evidenceList">
    {(c.evidence||[]).slice(0,20).map((x:any)=><article key={x.id}><b>{x.fact_key}</b><p>{typeof x.fact_value==="string"?x.fact_value:JSON.stringify(x.fact_value)}</p><span>{sourceLabel(x)}{x.source_reference?" · "+x.source_reference:""}</span></article>)}
    {!(c.evidence||[]).length&&<div className="emptyState">Evidence will appear after JobDiva resume/profile enrichment.</div>}
   </div></section>

   <section className="panelBox"><small>Best Jobs</small>{(c.best_jobs||[]).map((j:any)=><article className="matchCard" key={j.match_id}><div><b>{j.title}</b><span>{j.division} · {[j.city,j.state].filter(Boolean).join(", ")}</span></div><strong>{Number(j.overall_score).toFixed(1)}</strong><p><b>{scoreBand(Number(j.overall_score))}</b> · {((j.explanation||{}).strengths||[]).join(" · ")||"Match evidence available in explanation."}</p><a href={"/jobs/"+j.job_id}>Open job</a></article>)}</section>

   <section className="panelBox"><small>Resume versions</small><table className="adminTable"><thead><tr><th>Resume ID</th><th>Primary</th><th>Date</th><th>Updated</th></tr></thead><tbody>{(c.resumes||[]).map((r:any)=><tr key={r.id}><td>{r.source_resume_id||"—"}</td><td>{r.is_primary?"Yes":"No"}</td><td>{r.resume_date||"—"}</td><td>{r.updated_at||"—"}</td></tr>)}</tbody></table></section>
  </div>
 </main>
}