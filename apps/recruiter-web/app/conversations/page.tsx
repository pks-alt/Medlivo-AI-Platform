"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";

async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
 return b;
}
async function post(path:string,body:any){
 return api(path,{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify(body)});
}

export default function ConversationsPage(){
 const[data,setData]=useState<any>(null),[error,setError]=useState(""),[message,setMessage]=useState("");
 const[channel,setChannel]=useState<"email"|"sms">("email"),[purpose,setPurpose]=useState("follow_up");
 const[selectedKey,setSelectedKey]=useState(""),[draft,setDraft]=useState<any>(null),[subject,setSubject]=useState(""),[body,setBody]=useState(""),[busy,setBusy]=useState(false);
 useEffect(()=>{api("daily-priorities?limit=50").then(setData).catch(e=>setError(e.message))},[]);
 const followups=useMemo(()=>(data?.items||[]).filter((x:any)=>x.type==="follow_up"&&x.candidate_id),[data]);
 const selected=useMemo(()=>followups.find((x:any)=>(x.task_id||x.candidate_id)===selectedKey)||followups[0]||null,[followups,selectedKey]);

 async function generate(){
  if(!selected?.candidate_id){setError("Select a candidate follow-up first");return}
  setBusy(true);setError("");setMessage("");
  try{
   const result=await post("outreach-drafts",{
    candidate_id:selected.candidate_id,
    job_id:selected.job_id||null,
    channel,
    purpose,
    instruction:selected.detail||selected.recommended_next_action||null,
   });
   setDraft(result);setSubject(result.subject||"");setBody(result.body||"");
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }

 async function review(decision:"approved"|"cancelled"){
  if(!draft?.id)return;
  setBusy(true);setError("");setMessage("");
  try{
   const result=await post("outreach-drafts/"+draft.id+"/decision",{decision,subject:channel==="email"?subject:null,body});
   setDraft(result);
   setMessage(decision==="approved"
    ?"Draft approved and stored. External provider send remains disabled."
    :"Draft cancelled.");
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }

 async function recordEngagement(eventType:string){
  if(!selected?.candidate_id)return;
  setBusy(true);setError("");setMessage("");
  try{
   const result=await post("candidates/"+selected.candidate_id+"/engagement",{
    event_type:eventType,
    job_id:selected.job_id||null,
    source_type:"manual",
    source_reference:"recruiter-conversations",
   });
   setMessage(result.meaningful
    ?"Meaningful engagement recorded. Candidate relationship continuity updated."
    :"Activity recorded. This did not establish candidate relationship protection.");
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }

 if(error&&!data)return <main className="page"><div className="adminError"><b>Conversations unavailable</b><span>{error}</span></div></main>;

 return <main className="page conversationsPage">
  <div className="pageHead"><div><small>Recruiter communication</small><h1>Conversations</h1><p>Candidate follow-up, source-grounded AI email/SMS drafts and relationship-aware recruiter actions.</p></div><span className="sourcePill">AI ASSISTED · RECRUITER CONTROLLED</span></div>
  {error&&<div className="adminError"><b>Action could not be completed</b><span>{error}</span></div>}
  {message&&<div className="goodState">{message}</div>}

  <div className="conversationLayout">
   <section className="panelBox"><small>FOLLOW-UPS NEEDING ACTION</small>
    <div className="conversationQueue">{followups.map((x:any,i:number)=>{
     const key=x.task_id||x.candidate_id||String(i);
     return <button type="button" key={key} className={selected===x?"active":""} onClick={()=>{setSelectedKey(key);setDraft(null);setSubject("");setBody("");}}>
      <b>{x.title||"Candidate follow-up"}</b>
      <span>{x.detail||x.recommended_next_action||x.urgency||"Review next action"}</span>
      <em>{x.urgency==="overdue"?"Overdue":"Due soon"}</em>
     </button>
    })}{!followups.length&&<div className="emptyState">No candidate follow-up items are currently visible.</div>}</div>
   </section>

   <section className="panelBox">
    <div className="conversationContextHead"><div><small>CURRENT CONTEXT</small><h2>{selected?.title||"Select a candidate follow-up"}</h2><p>{selected?.detail||"Candidate and job context will appear here."}</p></div>
      <div className="conversationContextLinks">{selected?.candidate_id&&<Link href={"/candidates/"+selected.candidate_id}>Candidate 360</Link>}{selected?.job_id&&<Link href={"/jobs/"+selected.job_id}>Job 360</Link>}</div>
    </div>

    <div className="conversationActionStrip">
      <div><small>MEANINGFUL ENGAGEMENT</small><b>Record only what actually happened.</b><span>Unanswered outreach does not establish a relationship.</span></div>
      <div>{selected?.candidate_id&&<>
        <button disabled={busy} onClick={()=>recordEngagement("completed_call")}>Completed call</button>
        <button disabled={busy} onClick={()=>recordEngagement("availability_confirmed")}>Availability confirmed</button>
        <button disabled={busy} onClick={()=>recordEngagement("interest_confirmed")}>Interest confirmed</button>
        <button disabled={busy} onClick={()=>recordEngagement("next_step_agreed")}>Next step agreed</button>
      </>}</div>
    </div>

    <div className="section-title"><h2>AI Email / Text Draft</h2></div>
    <div className="workspaceTabs"><button className={channel==="email"?"active":""} onClick={()=>{setChannel("email");setDraft(null)}}>Email</button><button className={channel==="sms"?"active":""} onClick={()=>{setChannel("sms");setDraft(null)}}>Text / SMS</button></div>
    <div className="conversationDraftControls">
      <label>Purpose<select value={purpose} onChange={e=>setPurpose(e.target.value)}>
       <option value="follow_up">Follow-up</option><option value="initial_outreach">Initial outreach</option>
       <option value="availability_reconfirm">Availability reconfirmation</option><option value="interview_followup">Interview follow-up</option>
       <option value="pay_followup">Pay follow-up</option><option value="next_step">Next step</option>
      </select></label>
      <button className="button primary" disabled={busy||!selected?.candidate_id} onClick={generate}>{busy?"Working…":"Generate with Medlivo AI"}</button>
    </div>
    <p className="sectionHelp">Vertex Gemini receives only the authorized Medlivo candidate/job context assembled by the private workspace API. Unsupported facts must be omitted or marked for confirmation.</p>

    {draft&&<div className="aiDraftEditor">
      <div className="aiDraftMeta"><span><b>{String(draft.model_provider||"AI").replaceAll("_"," ")}</b> · {draft.model_version||"model"}</span><span>{draft.policy_version}</span></div>
      {channel==="email"&&<label>Subject<input value={subject} onChange={e=>setSubject(e.target.value)}/></label>}
      <label>Draft<textarea value={body} onChange={e=>setBody(e.target.value)}/></label>
      {(draft.warnings||[]).length>0&&<div className="draftWarnings"><b>Review warnings</b>{draft.warnings.map((w:string,i:number)=><span key={i}>{w}</span>)}</div>}
      <div className="draftReviewActions">
       {draft.status==="draft"?<><button className="button" disabled={busy} onClick={()=>review("cancelled")}>Cancel draft</button><button className="button primary" disabled={busy||!body.trim()} onClick={()=>review("approved")}>Approve draft</button></>:<span className="approvedDraftState">{String(draft.status).toUpperCase()} · external send disabled</span>}
      </div>
    </div>}

    <div className="draftGuardrail"><b>External-send boundary</b><span>Approval stores the recruiter-reviewed message and provenance. It does not send Gmail or SMS yet. Provider sending will be enabled only after the approved integration, consent and audit controls are accepted.</span></div>
   </section>
  </div>
 </main>;
}
