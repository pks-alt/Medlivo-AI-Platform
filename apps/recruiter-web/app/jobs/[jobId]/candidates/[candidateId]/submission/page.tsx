"use client";
import {useEffect,useState} from "react";

async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const body=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(body.detail||path+" HTTP "+r.status);
 return body;
}
const statusLabel=(s:string)=>({
 not_started:"Not Started",missing_required:"Missing Required Items",needs_review:"Needs Review",ready:"Ready to Submit",
 matched:"Found",missing:"Missing",conflict:"Conflict",approved:"Approved",ai_filled:"AI Prepared"
}[s]||String(s||"").replaceAll("_"," "));

export default function SubmissionStudioPage({params}:{params:Promise<{jobId:string,candidateId:string}>}){
 const[ids,setIds]=useState<{jobId:string,candidateId:string}|null>(null);
 const[job,setJob]=useState<any>(null),[candidate,setCandidate]=useState<any>(null),[me,setMe]=useState<any>(null);
 const[pack,setPack]=useState<any>(null),[history,setHistory]=useState<any[]>([]);
 const[error,setError]=useState(""),[busy,setBusy]=useState(false),[program,setProgram]=useState("");
 const[itemNotes,setItemNotes]=useState<Record<string,string>>({}),[itemValues,setItemValues]=useState<Record<string,string>>({});

 async function loadAll(p:{jobId:string,candidateId:string}){
  const[m,j,c,h]=await Promise.all([
   api("me"),api("jobs/"+p.jobId),api("candidates/"+p.candidateId),
   api("submission-studio/packages?job_id="+p.jobId+"&candidate_id="+p.candidateId+"&limit=25")
  ]);
  setMe(m);setJob(j);setCandidate(c);setHistory(h.items||[]);
  if((h.items||[]).length){
   const latest=await api("submission-studio/packages/"+h.items[0].id);
   setPack(latest);
  }
 }
 useEffect(()=>{params.then(async p=>{setIds(p);await loadAll(p)}).catch(e=>setError(e.message))},[params]);

 async function refreshPackage(id:string){
  const latest=await api("submission-studio/packages/"+id);setPack(latest);
  if(ids){
   const h=await api("submission-studio/packages?job_id="+ids.jobId+"&candidate_id="+ids.candidateId+"&limit=25");
   setHistory(h.items||[]);
  }
 }
 async function composeAI(){
  if(!pack)return;setBusy(true);setError("");
  try{
   const drafted=await api("submission-studio/packages/"+pack.id+"/compose-ai",{
    method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:"{}"
   });
   setPack(drafted);
   const summaryItem=(drafted.items||[]).find((x:any)=>x.requirement_key==="candidate_summary");
   if(summaryItem?.resolved_value?.text)setItemValues(v=>({...v,[summaryItem.id]:summaryItem.resolved_value.text}));
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }

 async function reviewItem(item:any,decision:"approved"|"waived"|"not_applicable"){
  if(!pack)return;setBusy(true);setError("");
  try{
   const textValue=String(item._reviewText??itemValues[item.id]??"").trim();
   const payload:any={decision,recruiter_note:(itemNotes[item.id]||"").trim()||null,resolved_value:null};
   if(decision==="approved"&&item.requirement_key==="candidate_summary")payload.resolved_value={...(item.resolved_value||{}),text:textValue};
   else if(decision==="approved"&&item.status==="missing"&&textValue)payload.resolved_value={value:textValue};
   await api("submission-studio/packages/"+pack.id+"/items/"+item.id+"/review",{
    method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify(payload)
   });
   await refreshPackage(pack.id);
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }
 async function finalize(){
  if(!pack)return;setBusy(true);setError("");
  try{
   const final=await api("submission-studio/packages/"+pack.id+"/finalize",{
    method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},
    body:JSON.stringify({confirmation:"reviewed_and_ready"})
   });
   setPack(final);await refreshPackage(final.id);
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }

 async function prepare(){
  if(!ids)return;setBusy(true);setError("");
  try{
   const created=await api("submission-studio/jobs/"+ids.jobId+"/candidates/"+ids.candidateId+"/prepare",{
    method:"POST",
    headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},
    body:JSON.stringify({program_name:program.trim()||null})
   });
   setPack(created);
   const h=await api("submission-studio/packages?job_id="+ids.jobId+"&candidate_id="+ids.candidateId+"&limit=25");
   setHistory(h.items||[]);
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }

 if(error&&!job)return <main className="page"><div className="adminError"><b>Submission Studio unavailable</b><span>{error}</span></div></main>;
 if(!job||!candidate||!me)return <main className="page"><div className="adminLoading">Loading Submission Studio…</div></main>;
 if(me.business_role!=="recruiter")return <main className="page"><div className="adminError"><b>Recruiter access required</b><span>Submission packages are prepared by the assigned recruiter.</span></div></main>;

 const summary=pack?.validation_summary||{};
 const items=pack?.items||[];
 const missing=items.filter((x:any)=>x.status==="missing");
 const review=items.filter((x:any)=>["needs_review","conflict"].includes(x.status));
 const ready=items.filter((x:any)=>["matched","approved","ai_filled","waived","not_applicable"].includes(x.status));
 return <main className="page submissionStudioPage">
  <div className="pageHead"><div><small>{job.division} · Submission Studio</small><h1>Build Submission Package</h1><p>{candidate.canonical_name||"Candidate"} · {job.title} · {job.customer_name||"Customer / MSP"}</p></div><div className="pageActions"><a href={"/jobs/"+ids?.jobId}>Back to Job</a><a href={"/jobs/"+ids?.jobId+"/candidates/"+ids?.candidateId+"/pay-package"}>Pay Package</a></div></div>

  <section className="submissionHero">
   <div><small>AI-ASSISTED SUBMISSION</small><h2>Let Medlivo assemble the package first.</h2><p>Medlivo reuses verified candidate data and documents, applies the active customer/program template, and shows only what is missing or needs review.</p></div>
   <div className="submissionPrepare">
    <label><span>MSP / VMS Program (optional)</span><input value={program} onChange={e=>setProgram(e.target.value)} placeholder="Only enter when the program is known"/></label>
    <button onClick={prepare} disabled={busy}>{busy?"Preparing…":pack?"Prepare New Version":"Prepare Package"}</button>
   </div>
  </section>

  {error&&<div className="payError">{error}</div>}

  {!pack?<section className="panelBox"><div className="emptyMargin"><b>No package prepared yet</b><p>Prepare the package to see what Medlivo can reuse automatically and what still needs recruiter attention.</p></div></section>:<>
   <div className="submissionMetrics">
    <article className={"readiness "+pack.readiness_status}><strong>{Number(pack.readiness_score||0).toFixed(0)}%</strong><b>{statusLabel(pack.readiness_status)}</b><span>Submission readiness</span></article>
    <article><strong>{ready.length}</strong><b>Found automatically</b><span>Reusable facts/documents</span></article>
    <article><strong>{review.length}</strong><b>Needs review</b><span>Human confirmation or AI narrative</span></article>
    <article><strong>{missing.length}</strong><b>Missing</b><span>Required items not found</span></article>
   </div>

   {me.submission_ai_enabled&&pack.status!=="finalized"&&<section className="submissionAIBox">
    <div><small>MEDLIVO AI COMPOSER</small><b>{pack.ai_summary?.status==="draft_ready"?"AI draft ready for review":"Draft presentation + formatted resume from verified source facts"}</b><span>AI cannot finalize the package or invent unsupported experience, credentials, rates, or availability.</span></div>
    <button disabled={busy} onClick={composeAI}>{busy?"Drafting…":pack.ai_summary?.status==="draft_ready"?"Regenerate AI Draft":"Draft with AI"}</button>
   </section>}
   {!me.submission_ai_enabled&&<div className="submissionBoundary aiDisabled"><b>AI composer is not enabled in this environment.</b><span>Recruiters can still prepare and review packages manually. Production AI requires the approved Vertex AI project/model configuration.</span></div>}

   {pack.ai_summary?.status==="draft_ready"&&<section className="panelBox submissionAIPreview"><small>AI DRAFT · RECRUITER REVIEW REQUIRED</small>
    <div className="aiDraftGrid"><article><b>Candidate Presentation</b><p>{pack.ai_summary.candidate_summary}</p></article><article><b>Resume Draft</b><pre>{pack.ai_summary.resume_markdown}</pre></article></div>
    {(pack.ai_summary.warnings||[]).length>0&&<div className="aiWarningList"><b>AI review flags</b>{pack.ai_summary.warnings.map((w:string,i:number)=><span key={i}>{w}</span>)}</div>}
    <p className="aiModelNote">Generated with {pack.ai_summary.provider} · {pack.ai_summary.model}. Final recruiter review is required.</p>
   </section>}

   <div className="submissionGrid">
    <section className="panelBox"><small>PACKAGE CHECKLIST</small>
     <div className="submissionChecklist">{items.map((x:any)=><article key={x.id} className={"submissionItem "+x.status}>
      <div><b>{x.label}</b><span>{String(x.item_type||"item").replaceAll("_"," ")}</span></div>
      <strong>{statusLabel(x.status)}</strong>
      {x.status==="needs_review"&&x.requirement_key==="candidate_summary"&&<>
       <p>Medlivo has gathered source facts. Use the approved AI model when connected, or enter the reviewed presentation text here.</p>
       <textarea className="submissionNarrative" value={itemValues[x.id]??x.resolved_value?.text??""} onChange={e=>setItemValues({...itemValues,[x.id]:e.target.value})} placeholder="Reviewed candidate presentation"/>
       <button className="submissionItemAction" disabled={busy||!String(itemValues[x.id]??x.resolved_value?.text??"").trim()} onClick={()=>reviewItem({...x,_reviewText:itemValues[x.id]??x.resolved_value?.text??""},"approved")}>Approve Presentation</button>
      </>}
      {x.status==="missing"&&<>
       <p>Required by the active template but no current matching evidence was found.</p>
       {!["document","skills_checklist","reference","form"].includes(x.item_type)&&<>
        <input className="submissionManualValue" value={itemValues[x.id]||""} onChange={e=>setItemValues({...itemValues,[x.id]:e.target.value})} placeholder="Confirmed value"/>
        <button className="submissionItemAction" disabled={busy||!(itemValues[x.id]||"").trim()} onClick={()=>reviewItem(x,"approved")}>Confirm Value</button>
       </>}
      </>}
      {x.status==="conflict"&&<>
       <p>Conflicting evidence requires recruiter review. Do not approve until the source is confirmed.</p>
       <textarea className="submissionNarrative" value={itemNotes[x.id]||""} onChange={e=>setItemNotes({...itemNotes,[x.id]:e.target.value})} placeholder="Resolution note"/>
      </>}
      {x.status==="matched"&&<p>Matched to existing candidate evidence. It is already counted toward readiness.</p>}
      {["approved","waived","not_applicable"].includes(x.status)&&x.recruiter_note&&<p>{x.recruiter_note}</p>}
     </article>)}</div>
    </section>

    <aside className="panelBox submissionAttention"><small>WHAT NEEDS YOUR ATTENTION</small>
     {!missing.length&&!review.length?<div className="goodState">All current template requirements are satisfied.</div>:<>
      {missing.map((x:any)=><div className="attentionRow blocking" key={x.id}><b>{x.label}</b><span>Required item missing</span></div>)}
      {review.map((x:any)=><div className="attentionRow review" key={x.id}><b>{x.label}</b><span>{x.status==="conflict"?"Resolve conflicting evidence":"Review before final package"}</span></div>)}
     </>}
     <div className="submissionBoundary"><b>Nothing is submitted automatically.</b><span>Phase 1 prepares, validates and generates the package. The recruiter reviews it and uses the customer/MSP submission channel.</span></div>
    </aside>
   </div>

   {pack.status!=="finalized"&&<section className="submissionFinalize">
    <div><b>{pack.readiness_status==="ready"?"Package is ready for recruiter final review.":"Resolve the remaining items before finalizing."}</b><span>Finalizing locks this package version. It does not submit anything to JobDiva or the MSP/VMS.</span></div>
    <button disabled={busy||pack.readiness_status!=="ready"} onClick={finalize}>{busy?"Working…":"Finalize Submission Package"}</button>
   </section>}
   {pack.status==="finalized"&&<div className="goodState">Submission package finalized and locked for this version.</div>}

   <section className="panelBox"><small>PACKAGE VERSION</small><div className="adminRows">
    <div><span>Template</span><b>{pack.template?.name||"Configured template"}</b></div>
    <div><span>Template version</span><b>v{pack.template_version}</b></div>
    <div><span>Package version</span><b>v{pack.version}</b></div>
    <div><span>Required satisfied</span><b>{summary.required_satisfied??0} / {summary.required_total??0}</b></div>
    <div><span>AI narrative</span><b>{pack.ai_summary?.status==="draft_ready"?"Draft ready for review":pack.ai_summary?.status==="model_pending"?"Not generated":"Available"}</b></div>
   </div></section>

   <section className="panelBox"><small>PACKAGE HISTORY</small>{history.length?<table className="adminTable"><thead><tr><th>Version</th><th>Readiness</th><th>Score</th><th>Status</th><th>Created</th></tr></thead><tbody>{history.map((x:any)=><tr key={x.id}><td>v{x.version}</td><td>{statusLabel(x.readiness_status)}</td><td>{Number(x.readiness_score||0).toFixed(0)}%</td><td>{statusLabel(x.status)}</td><td>{x.created_at?new Date(x.created_at).toLocaleString():"—"}</td></tr>)}</tbody></table>:null}</section>
  </>}
 </main>
}
