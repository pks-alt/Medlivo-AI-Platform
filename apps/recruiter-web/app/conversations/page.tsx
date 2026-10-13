"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";
async function api(path:string){const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);return b}
export default function ConversationsPage(){
 const[data,setData]=useState<any>(null),[error,setError]=useState(""),[channel,setChannel]=useState<"email"|"sms">("email"),[draft,setDraft]=useState("");
 useEffect(()=>{api("daily-priorities?limit=50").then(setData).catch(e=>setError(e.message))},[]);
 const followups=useMemo(()=>(data?.items||[]).filter((x:any)=>x.type==="follow_up"),[data]);
 const selected=followups[0];
 function generate(){
  const who=selected?.candidate_name||"there",job=selected?.title||selected?.job_title||"the opportunity";
  setDraft(channel==="email"
   ?`Hi ${who},\n\nI’m following up on ${job}. I want to make sure I give you the most current information before we decide the next step. Please let me know if you are still interested and whether your availability has changed.\n\nThank you,\nMedlivo`
   :`Hi ${who} — following up on ${job}. Are you still interested, and has your availability changed? I’ll confirm the latest details before we move forward. — Medlivo`);
 }
 if(error)return <main className="page"><div className="adminError"><b>Conversations unavailable</b><span>{error}</span></div></main>;
 return <main className="page conversationsPage">
  <div className="pageHead"><div><small>Recruiter communication</small><h1>Conversations</h1><p>Action queue and AI-assisted draft preparation. External email/SMS sending remains disabled until the approved provider boundary is enabled.</p></div><span className="sourcePill">RECRUITER CONTROLLED</span></div>
  <div className="conversationLayout">
   <section className="panelBox"><small>FOLLOW-UPS NEEDING ACTION</small><div className="conversationQueue">{followups.map((x:any,i:number)=><article key={x.id||i}><b>{x.candidate_name||x.title||"Follow-up"}</b><span>{x.detail||x.urgency||"Review next action"}</span>{x.job_id&&<Link href={"/jobs/"+x.job_id}>Open job</Link>}</article>)}{!followups.length&&<div className="emptyState">No follow-up items are currently visible.</div>}</div></section>
   <section className="panelBox"><small>AI EMAIL / TEXT DRAFT</small><div className="workspaceTabs"><button className={channel==="email"?"active":""} onClick={()=>setChannel("email")}>Email</button><button className={channel==="sms"?"active":""} onClick={()=>setChannel("sms")}>Text / SMS</button></div><p className="sectionHelp">AI may prepare wording from trusted Medlivo context. Recruiter review is required. No provider send is triggered from this page.</p><button className="button" onClick={generate}>Generate draft</button><textarea value={draft} onChange={e=>setDraft(e.target.value)} placeholder="Generate or edit a recruiter-controlled draft"/><div className="draftGuardrail"><b>Block 1 guardrail</b><span>Do not invent pay, housing, credentialing or client promises. Sending will be wired only after approved email/SMS provider integration.</span></div></section>
  </div>
 </main>;
}
