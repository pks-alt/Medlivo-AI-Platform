"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";

async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
 return b;
}
async function session(){
 const r=await fetch("/api/team/session",{cache:"no-store",credentials:"same-origin"});
 const b=await r.json().catch(()=>({}));
 if(!r.ok||!b.csrf)throw new Error("Session security context unavailable");
 return b;
}
function title(v:any){return String(v||"").replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase())}

export default function ConversationsPage(){
 const[candidates,setCandidates]=useState<any[]>([]),[jobs,setJobs]=useState<any[]>([]),[priorities,setPriorities]=useState<any>({items:[]}),[drafts,setDrafts]=useState<any[]>([]);
 const[candidateId,setCandidateId]=useState(""),[jobId,setJobId]=useState(""),[channel,setChannel]=useState<"email"|"sms">("email"),[purpose,setPurpose]=useState("follow_up");
 const[instruction,setInstruction]=useState(""),[activeDraft,setActiveDraft]=useState<any>(null),[subject,setSubject]=useState(""),[body,setBody]=useState("");
 const[relationship,setRelationship]=useState<any>(null),[error,setError]=useState(""),[message,setMessage]=useState(""),[busy,setBusy]=useState(false);

 async function load(){
  setError("");
  const[c,j,p,d]=await Promise.all([api("candidates?limit=100"),api("jobs?limit=100"),api("daily-priorities?limit=50"),api("outreach-drafts?limit=50")]);
  setCandidates(c.items||[]);setJobs(j.items||[]);setPriorities(p);setDrafts(d.items||[]);
 }
 useEffect(()=>{load().catch(e=>setError(e.message))},[]);
 useEffect(()=>{if(!candidateId){setRelationship(null);return}api("candidates/"+candidateId+"/relationship").then(setRelationship).catch(()=>setRelationship(null))},[candidateId]);

 const selectedCandidate=useMemo(()=>candidates.find(c=>c.id===candidateId),[candidates,candidateId]);
 const selectedJob=useMemo(()=>jobs.find(j=>j.id===jobId),[jobs,jobId]);
 const followups=useMemo(()=>(priorities.items||[]).filter((x:any)=>x.type==="follow_up"),[priorities]);

 async function createDraft(){
  if(!candidateId){setError("Select a candidate before generating a draft.");return}
  setBusy(true);setError("");setMessage("");
  try{
   const s=await session();
   const created=await api("outreach-drafts",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({
    candidate_id:candidateId,job_id:jobId||null,channel,purpose,instruction:instruction.trim()||null
   })});
   setActiveDraft(created);setSubject(created.subject||"");setBody(created.body||"");
   setDrafts(prev=>[created,...prev]);setMessage("AI draft created from trusted Medlivo context. Review before approval.");
  }catch(e:any){setError(e.message||"AI draft could not be created")}finally{setBusy(false)}
 }

 async function decide(decision:"approved"|"cancelled"){
  if(!activeDraft?.id)return;
  setBusy(true);setError("");setMessage("");
  try{
   const s=await session();
   const reviewed=await api("outreach-drafts/"+activeDraft.id+"/decision",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({decision,subject:channel==="email"?subject:null,body})});
   setActiveDraft(reviewed);setDrafts(prev=>prev.map(x=>x.id===reviewed.id?reviewed:x));
   setMessage(decision==="approved"?"Draft approved and stored. External provider send remains disabled until the approved integration is enabled.":"Draft cancelled.");
  }catch(e:any){setError(e.message||"Draft review failed")}finally{setBusy(false)}
 }

 return <main className="page conversationsPage finalConversationsPage">
  <div className="pageHead"><div><small>Recruiter communication</small><h1>Conversations</h1><p>AI-assisted Email and Text/SMS drafting backed by trusted candidate/job data, recruiter review and an auditable draft record.</p></div><span className="sourcePill">HUMAN REVIEW REQUIRED</span></div>
  {error&&<div className="adminError"><b>Conversation action unavailable</b><span>{error}</span></div>}
  {message&&<div className="goodState conversationMessage">{message}</div>}

  <div className="conversationLayout">
   <section className="panelBox"><small>NEEDS RESPONSE / FOLLOW-UP</small>
    <div className="conversationQueue">{followups.map((x:any,i:number)=><article key={x.id||i}><b>{x.candidate_name||x.title||"Follow-up"}</b><span>{x.detail||x.urgency||"Review next action"}</span>{x.job_id&&<Link href={"/jobs/"+x.job_id}>Open job</Link>}</article>)}{!followups.length&&<div className="emptyState">No current follow-up actions are visible.</div>}</div>
    <hr className="sectionRule"/>
    <small>RECENT AI DRAFTS</small>
    <div className="conversationQueue">{drafts.slice(0,8).map((x:any)=><button key={x.id} className="conversationDraftRow" onClick={()=>{setActiveDraft(x);setCandidateId(x.candidate_id);setJobId(x.job_id||"");setChannel(x.channel);setPurpose(x.purpose);setSubject(x.subject||"");setBody(x.body||"")}}><b>{title(x.channel)} · {title(x.purpose)}</b><span>{title(x.status)} · {x.created_at?new Date(x.created_at).toLocaleString():""}</span></button>)}{!drafts.length&&<div className="emptyState">No AI outreach drafts have been created yet.</div>}</div>
   </section>

   <section className="panelBox"><small>AI EMAIL / TEXT DRAFT</small>
    <div className="conversationSelectors">
     <label>Candidate<select value={candidateId} onChange={e=>{setCandidateId(e.target.value);setActiveDraft(null);setBody("");setSubject("")}}><option value="">Select candidate…</option>{candidates.map(c=><option key={c.id} value={c.id}>{c.canonical_name||c.id}</option>)}</select></label>
     <label>Job (optional)<select value={jobId} onChange={e=>setJobId(e.target.value)}><option value="">No job context</option>{jobs.map(j=><option key={j.id} value={j.id}>{j.title||j.id}</option>)}</select></label>
    </div>

    {candidateId&&<div className={"candidateRelationshipInline "+(relationship?.relationship?.is_mine?"mine":relationship?.relationship?"other":"none")}><div><b>{relationship?.relationship?(relationship.relationship.is_mine?"Active with you":"Active with "+(relationship.relationship.recruiter_name||"another recruiter")):"No active relationship"}</b><span>{relationship?.relationship?"Last meaningful activity "+(relationship.relationship.relationship_age_hours??"—")+" hours ago":"Normal same-division engagement rules apply"}</span></div>{relationship?.relationship&&!relationship.relationship.is_mine&&<strong>Coordinate before outreach</strong>}</div>}

    <div className="workspaceTabs"><button className={channel==="email"?"active":""} onClick={()=>setChannel("email")}>Email</button><button className={channel==="sms"?"active":""} onClick={()=>setChannel("sms")}>Text / SMS</button></div>
    <div className="conversationSelectors compact">
     <label>Purpose<select value={purpose} onChange={e=>setPurpose(e.target.value)}><option value="initial_outreach">Initial outreach</option><option value="follow_up">Follow-up</option><option value="availability_reconfirm">Availability reconfirm</option><option value="interview_followup">Interview follow-up</option><option value="pay_followup">Pay follow-up</option><option value="next_step">Next step</option></select></label>
     <label>Optional instruction<input value={instruction} onChange={e=>setInstruction(e.target.value)} placeholder="Example: keep concise; ask about November availability"/></label>
    </div>

    <button className="button primary" disabled={busy||!candidateId||Boolean(relationship?.relationship&&!relationship.relationship.is_mine)} onClick={createDraft}>{busy?"Generating…":"Generate AI Draft"}</button>
    {relationship?.relationship&&!relationship.relationship.is_mine&&<p className="sectionHelp">AI draft creation is intentionally blocked here until recruiter coordination is resolved.</p>}

    {activeDraft&&<div className="aiDraftWorkspace">
      <div className="aiDraftMeta"><span>Provider <b>{activeDraft.model_provider||"configured AI"}</b></span><span>Model <b>{activeDraft.model_version||"—"}</b></span><span>Policy <b>{activeDraft.policy_version||"—"}</b></span><span>Status <b>{title(activeDraft.status)}</b></span></div>
      {channel==="email"&&<label>Subject<input value={subject} onChange={e=>setSubject(e.target.value)} disabled={activeDraft.status!=="draft"}/></label>}
      <label>Draft<textarea value={body} onChange={e=>setBody(e.target.value)} disabled={activeDraft.status!=="draft"}/></label>
      {(activeDraft.warnings||[]).length>0&&<div className="draftWarnings"><b>AI warnings</b>{activeDraft.warnings.map((w:any,i:number)=><span key={i}>{String(w)}</span>)}</div>}
      <div className="draftGuardrail"><b>Trusted context</b><span>{selectedCandidate?.canonical_name||"Candidate"}{selectedJob?" · "+selectedJob.title:""} · AI draft stored in Medlivo · recruiter approval required</span></div>
      {activeDraft.status==="draft"&&<div className="conversationActions"><button className="button primary" disabled={busy||!body.trim()} onClick={()=>decide("approved")}>Approve Draft</button><button className="button" disabled={busy} onClick={()=>decide("cancelled")}>Cancel Draft</button></div>}
      {activeDraft.status==="approved"&&<div className="providerBoundary"><b>Approved — provider send not enabled</b><span>The approved Email/SMS integration will send this stored draft later. No external message is sent by this action.</span></div>}
    </div>}
   </section>
  </div>
 </main>;
}
