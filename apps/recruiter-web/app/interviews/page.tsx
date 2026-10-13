"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";
async function api(path:string){const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);return b}
const fmt=(v:any)=>v?new Date(v).toLocaleString():"—";
export default function InterviewsPage(){
 const[data,setData]=useState<any>(null),[error,setError]=useState("");
 useEffect(()=>{api("funnel?limit=200").then(setData).catch(e=>setError(e.message))},[]);
 const items=useMemo(()=>(data?.items||[]).filter((x:any)=>x.interview).sort((a:any,b:any)=>new Date(a.interview?.scheduled_at||0).getTime()-new Date(b.interview?.scheduled_at||0).getTime()),[data]);
 if(error)return <main className="page"><div className="adminError"><b>Interviews unavailable</b><span>{error}</span></div></main>;
 if(!data)return <main className="page"><div className="adminLoading">Loading interviews…</div></main>;
 return <main className="page interviewsPage">
  <div className="pageHead"><div><small>Interview workflow</small><h1>Interviews</h1><p>Scheduled interviews, completed interviews and feedback follow-up from the live Submission-to-Start data.</p></div><span className="sourcePill">SYSTEM ACTIVITY</span></div>
  <div className="interviewSummary"><article><b>{items.filter((x:any)=>!x.interview?.completed_at).length}</b><span>Scheduled / upcoming</span></article><article><b>{items.filter((x:any)=>x.interview?.completed_at).length}</b><span>Completed</span></article><article><b>{items.filter((x:any)=>x.interview?.completed_at&&!x.offer).length}</b><span>Feedback / next step</span></article></div>
  <section className="interviewList">{items.map((x:any)=><article key={x.id} className="interviewRow">
   <div><small>{x.interview?.completed_at?"COMPLETED":"SCHEDULED"}</small><b>{x.candidate_name||"Candidate"}</b><span>{x.job_title||"Job"} · {[x.job_city,x.job_state].filter(Boolean).join(", ")}</span></div>
   <div><small>INTERVIEW</small><b>{fmt(x.interview?.completed_at||x.interview?.scheduled_at)}</b><span>{x.offer?"Offer stage":"Next action required"}</span></div>
   <div className="interviewLinks"><Link href={"/candidates/"+x.candidate_id}>Candidate 360</Link><Link href={"/jobs/"+x.job_id}>Job 360</Link><Link className="primary" href={"/funnel/"+x.job_id+"/"+x.candidate_id}>Open Delivery</Link></div>
  </article>)}
  {!items.length&&<div className="emptyState">No interview records are currently visible for this recruiter scope.</div>}</section>
 </main>;
}
