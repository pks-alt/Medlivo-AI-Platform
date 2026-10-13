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
 const[candidates,setCandidates]=useState<any[]>([]),[jobs,setJobs]=useState<any[]>([]),[priorities,setPriorities]=useState<any>({items:[]}),[drafts,setDrafts]=useState<any[]>([]),[executions,setExecutions]=useState<any[]>([]),[gmailMessages,setGmailMessages]=useState<any[]>([]),[sequences,setSequences]=useState<any[]>([]);
 const[candidateId,setCandidateId]=useState(""),[jobId,setJobId]=useState(""),[channel,setChannel]=useState<"email"|"sms">("email"),[purpose,setPurpose]=useState("follow_up");
 const[instruction,setInstruction]=useState(""),[activeDraft,setActiveDraft]=useState<any>(null),[subject,setSubject]=useState(""),[body,setBody]=useState("");
 const[relationship,setRelationship]=useState<any>(null),[gmail,setGmail]=useState<any>({connected:false,status:"not_connected"}),[error,setError]=useState(""),[message,setMessage]=useState(""),[busy,setBusy]=useState(false);

 async function load(){
  setError("");
  const[c,j,p,d,x,g,m,sq]=await Promise.all([api("candidates?limit=100"),api("jobs?limit=100"),api("daily-priorities?limit=50"),api("outreach-drafts?limit=50"),api("outreach-executions?limit=50"),api("gmail/status"),api("gmail/messages?limit=25"),api("followup-sequences?limit=50")]);
  setCandidates(c.items||[]);setJobs(j.items||[]);setPriorities(p);setDrafts(d.items||[]);setExecutions(x.items||[]);setGmail(g);setGmailMessages(m.items||[]);setSequences(sq.items||[]);
 }
 useEffect(()=>{load().catch(e=>setError(e.message))},[]);
 useEffect(()=>{if(!candidateId){setRelationship(null);return}api("candidates/"+candidateId+"/relationship").then(setRelationship).catch(()=>setRelationship(null))},[candidateId]);

 const selectedCandidate=useMemo(()=>candidates.find(c=>c.id===candidateId),[candidates,candidateId]);
 const selectedJob=useMemo(()=>jobs.find(j=>j.id===jobId),[jobs,jobId]);
 const followups=useMemo(()=>(priorities.items||[]).filter((x:any)=>x.type==="follow_up"),[priorities]);

 async function prepareDueFollowups(){
  setBusy(true);setError("");setMessage("");
  try{
    const s=await session();
    const result=await api("followup-sequences/prepare-due",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({limit:20})});
    const prepared=result.prepared||[];
    if(prepared.length){
      setDrafts(prev=>[...prepared,...prev.filter(x=>!prepared.some((p:any)=>p.id===x.id))]);
      const first=prepared[0];
      setActiveDraft(first);setCandidateId(first.candidate_id);setJobId(first.job_id||"");setChannel("email");setPurpose("follow_up");setSubject(first.subject||"");setBody(first.body||"");
      setMessage(prepared.length+" due follow-up draft"+(prepared.length===1?" is":"s are")+" ready for recruiter review.");
    }else{
      setMessage("No follow-up steps are due for review right now.");
    }
    const refreshed=await api("followup-sequences?limit=50");
    setSequences(refreshed.items||[]);
  }catch(e:any){setError(e.message||"Due follow-ups could not be prepared")}finally{setBusy(false)}
 }

 async function startSequence(){
  if(!candidateId){setError("Select a candidate before starting follow-ups.");return}
  setBusy(true);setError("");setMessage("");
  try{
    const s=await session();
    const created=await api("followup-sequences",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({candidate_id:candidateId,job_id:jobId||null,cadence_days:[3,7,14],stop_on_reply:true})});
    setSequences(prev=>[created,...prev]);
    setMessage("Follow-up plan started for days 3, 7 and 14. Candidate reply will stop the sequence automatically.");
  }catch(e:any){setError(e.message||"Follow-up plan could not be started")}finally{setBusy(false)}
 }

 async function controlSequence(sequenceId:string,action:"pause"|"resume"|"stop"){
  setBusy(true);setError("");setMessage("");
  try{
    const s=await session();
    const updated=await api("followup-sequences/"+sequenceId+"/action",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({action,reason:action==="stop"?"Recruiter stopped follow-up plan":null})});
    setSequences(prev=>prev.map(x=>x.id===sequenceId?{...x,...updated}:x));
    setMessage("Follow-up plan "+action+"d.");
  }catch(e:any){setError(e.message||"Follow-up plan could not be updated")}finally{setBusy(false)}
 }

 async function suppressEmail(candidate:string){
  setBusy(true);setError("");setMessage("");
  try{
    const s=await session();
    await api("contact-suppressions",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({candidate_id:candidate,channel:"email",reason:"Recruiter recorded do-not-contact / opt-out"})});
    setSequences(prev=>prev.map(x=>x.candidate_id===candidate&&["active","paused"].includes(x.status)?{...x,status:"stopped",stopped_reason:"contact_suppressed"}:x));
    setMessage("Email outreach suppressed. Pending follow-ups were cancelled.");
  }catch(e:any){setError(e.message||"Contact suppression could not be saved")}finally{setBusy(false)}
 }

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

 async function queueApproved(){
  if(!activeDraft?.id||activeDraft.status!=="approved")return;
  setBusy(true);setError("");setMessage("");
  try{
   const s=await session();
   const queued=await api("outreach-drafts/"+activeDraft.id+"/queue",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({})});
   setExecutions(prev=>[queued,...prev.filter(x=>x.id!==queued.id)]);
   setMessage("Approved outreach is queued inside Medlivo. Provider activation is still required before any external send occurs.");
  }catch(e:any){setError(e.message||"Approved outreach could not be queued")}finally{setBusy(false)}
 }

 async function cancelExecution(executionId:string){
  setBusy(true);setError("");setMessage("");
  try{
   const s=await session();
   const cancelled=await api("outreach-executions/"+executionId+"/cancel",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({reason:"Recruiter cancelled before provider delivery"})});
   setExecutions(prev=>prev.map(x=>x.id===executionId?cancelled:x));
   setMessage("Queued outreach cancelled before provider delivery.");
  }catch(e:any){setError(e.message||"Queued outreach could not be cancelled")}finally{setBusy(false)}
 }

 const activeExecution=activeDraft?.id?executions.find(x=>x.draft_id===activeDraft.id):null;
 async function connectGmail(){
  setBusy(true);setError("");setMessage("");
  try{
   const s=await session();
   const started=await api("gmail/oauth/start",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:"{}"});
   window.location.assign(started.authorization_url);
  }catch(e:any){setError(e.message||"Gmail connection could not start");setBusy(false)}
 }

 async function disconnectGmail(){
  setBusy(true);setError("");setMessage("");
  try{
   const s=await session();
   const result=await api("gmail/disconnect",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({reason:"Recruiter disconnected Gmail from Conversations"})});
   setGmail(result);setMessage("Gmail disconnected from Medlivo.");
  }catch(e:any){setError(e.message||"Gmail could not be disconnected")}finally{setBusy(false)}
 }

 async function sendQueuedGmail(executionId:string){
  setBusy(true);setError("");setMessage("");
  try{
   const s=await session();
   const sent=await api("outreach-executions/"+executionId+"/deliver-gmail",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":s.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({expected_status:"queued"})});
   setExecutions(prev=>prev.map(x=>x.id===executionId?sent:x));
   setMessage("Approved email sent through your connected Medlivo Gmail account.");
  }catch(e:any){setError(e.message||"Gmail could not send this approved outreach")}finally{setBusy(false)}
 }


 return <main className="page conversationsPage finalConversationsPage">
  <div className="pageHead"><div><small>Recruiter communication</small><h1>Conversations</h1><p>AI-assisted Email and Text/SMS drafting backed by trusted candidate/job data, recruiter review and an auditable draft record.</p></div><span className="sourcePill">HUMAN REVIEW REQUIRED</span></div>
  {error&&<div className="adminError"><b>Conversation action unavailable</b><span>{error}</span></div>}
  {message&&<div className="goodState conversationMessage">{message}</div>}
  <section className="panelBox gmailPilotBar"><div><small>SCHEDULED FOLLOW-UPS</small><b>Due steps become normal recruiter-reviewed drafts</b><span>Nothing sends automatically. Prepare due steps, review the AI draft, approve it, then queue/send through the existing Gmail guardrails.</span></div><button className="button primary" disabled={busy} onClick={prepareDueFollowups}>Prepare Due Follow-ups</button></section>
  <section className="panelBox gmailPilotBar"><div><small>GMAIL PILOT</small><b>{gmail.connected?"Connected as "+gmail.gmail_address:"Gmail not connected"}</b><span>{gmail.connected?"Approved queued emails can be sent from your own Medlivo mailbox. Replies are tracked with Gmail Watch + Pub/Sub history.":"Connect your own Medlivo Gmail account before live email delivery."}</span></div>{gmail.connected?<button className="button" disabled={busy} onClick={disconnectGmail}>Disconnect Gmail</button>:<button className="button primary" disabled={busy} onClick={connectGmail}>Connect Gmail</button>}</section>

  <div className="conversationLayout">
   <section className="panelBox"><small>NEEDS RESPONSE / FOLLOW-UP</small>
    <div className="conversationQueue">{followups.map((x:any,i:number)=><article key={x.id||i}><b>{x.candidate_name||x.title||"Follow-up"}</b><span>{x.detail||x.urgency||"Review next action"}</span>{x.job_id&&<Link href={"/jobs/"+x.job_id}>Open job</Link>}</article>)}{!followups.length&&<div className="emptyState">No current follow-up actions are visible.</div>}</div>
    <hr className="sectionRule"/>
    <small>FOLLOW-UP PLANS</small>
    <div className="conversationQueue">{sequences.slice(0,8).map((x:any)=><article key={x.id}><b>{title(x.status)} · Days {(x.cadence_days||[]).join(", ")}</b><span>{x.steps?.filter((s:any)=>s.status==="scheduled").length||0} scheduled steps · Stops on reply {x.stop_on_reply?"Yes":"No"}</span><div>{x.status==="active"&&<button className="button subtle" disabled={busy} onClick={()=>controlSequence(x.id,"pause")}>Pause</button>}{x.status==="paused"&&<button className="button subtle" disabled={busy} onClick={()=>controlSequence(x.id,"resume")}>Resume</button>}{["active","paused"].includes(x.status)&&<button className="button subtle" disabled={busy} onClick={()=>controlSequence(x.id,"stop")}>Stop</button>}</div></article>)}{!sequences.length&&<div className="emptyState">No follow-up plans yet.</div>}</div>
    <hr className="sectionRule"/>
    <small>RECENT GMAIL REPLIES</small>
    <div className="conversationQueue">{gmailMessages.slice(0,8).map((x:any)=><article key={x.id}><b>{x.subject||"Candidate reply"}</b><span>{x.from_address||"Candidate"} · {x.received_at?new Date(x.received_at).toLocaleString():""}</span><span>{String(x.body_text||"").slice(0,220)||"Reply received"}</span>{x.candidate_id&&<Link href={"/candidates/"+x.candidate_id}>Open candidate</Link>}</article>)}{!gmailMessages.length&&<div className="emptyState">No synchronized Gmail replies yet.</div>}</div>
    <hr className="sectionRule"/>
    <small>OUTREACH EXECUTION QUEUE</small>
    <div className="conversationQueue">{executions.slice(0,8).map((x:any)=><article key={x.id}><b>{title(x.channel)} · {title(x.status)}</b><span>{title(x.provider)} · {x.scheduled_for?new Date(x.scheduled_for).toLocaleString():"Ready"}</span>{x.status==="queued"&&x.provider==="gmail"&&gmail.connected&&<button className="button primary" disabled={busy} onClick={()=>sendQueuedGmail(x.id)}>Send Email</button>}{(x.status==="queued"||x.status==="failed")&&<button className="button subtle" disabled={busy} onClick={()=>cancelExecution(x.id)}>Cancel</button>}</article>)}{!executions.length&&<div className="emptyState">No approved outreach is queued yet.</div>}</div>
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
    {candidateId&&<div className="conversationActions"><button className="button" disabled={busy} onClick={startSequence}>Start 3 / 7 / 14 Day Follow-up Plan</button><button className="button subtle" disabled={busy} onClick={()=>suppressEmail(candidateId)}>Stop Email / Opt Out</button></div>}
    {relationship?.relationship&&!relationship.relationship.is_mine&&<p className="sectionHelp">AI draft creation is intentionally blocked here until recruiter coordination is resolved.</p>}

    {activeDraft&&<div className="aiDraftWorkspace">
      <div className="aiDraftMeta"><span>Provider <b>{activeDraft.model_provider||"configured AI"}</b></span><span>Model <b>{activeDraft.model_version||"—"}</b></span><span>Policy <b>{activeDraft.policy_version||"—"}</b></span><span>Status <b>{title(activeDraft.status)}</b></span></div>
      {channel==="email"&&<label>Subject<input value={subject} onChange={e=>setSubject(e.target.value)} disabled={activeDraft.status!=="draft"}/></label>}
      <label>Draft<textarea value={body} onChange={e=>setBody(e.target.value)} disabled={activeDraft.status!=="draft"}/></label>
      {(activeDraft.warnings||[]).length>0&&<div className="draftWarnings"><b>AI warnings</b>{activeDraft.warnings.map((w:any,i:number)=><span key={i}>{String(w)}</span>)}</div>}
      <div className="draftGuardrail"><b>Trusted context</b><span>{selectedCandidate?.canonical_name||"Candidate"}{selectedJob?" · "+selectedJob.title:""} · AI draft stored in Medlivo · recruiter approval required</span></div>
      {activeDraft.status==="draft"&&<div className="conversationActions"><button className="button primary" disabled={busy||!body.trim()} onClick={()=>decide("approved")}>Approve Draft</button><button className="button" disabled={busy} onClick={()=>decide("cancelled")}>Cancel Draft</button></div>}
      {activeDraft.status==="approved"&&!activeExecution&&<div className="providerBoundary"><b>Approved — ready for guarded queue</b><span>This draft passed recruiter review. Queueing creates an auditable provider handoff, but no external message is sent until Gmail/Zoom Phone activation is enabled.</span><button className="button primary" disabled={busy} onClick={queueApproved}>Queue Approved Message</button></div>}
      {activeExecution&&<div className="providerBoundary"><b>{title(activeExecution.status)} · {title(activeExecution.provider)}</b><span>Scheduled {activeExecution.scheduled_for?new Date(activeExecution.scheduled_for).toLocaleString():"now"} · {activeExecution.provider==="gmail"?(gmail.connected?"Gmail pilot is connected.":"Connect Gmail before sending."):"SMS provider remains disabled."}</span>{activeExecution.status==="queued"&&activeExecution.provider==="gmail"&&gmail.connected&&<button className="button primary" disabled={busy} onClick={()=>sendQueuedGmail(activeExecution.id)}>Send Approved Email</button>}{(activeExecution.status==="queued"||activeExecution.status==="failed")&&<button className="button" disabled={busy} onClick={()=>cancelExecution(activeExecution.id)}>Cancel Queue</button>}</div>}
    </div>}
   </section>
  </div>
 </main>;
}
