"use client";
import {useEffect,useState} from "react";

function monday(){
 const d=new Date(); const day=d.getDay(); const diff=(day+6)%7; d.setDate(d.getDate()-diff);
 return d.toISOString().slice(0,10);
}
async function get(path:string){const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});if(!r.ok)throw new Error(path+" HTTP "+r.status);return r.json()}
export default function Home(){
 const[me,setMe]=useState<any>(null);const[data,setData]=useState<any>(null);const[err,setErr]=useState("");
 useEffect(()=>{(async()=>{const who=await get("me");setMe(who);if(who.role==="recruiter"){const[dash,priorities,queue]=await Promise.all([get("recruiter/dashboard?week_start="+monday()),get("daily-priorities?limit=20"),get("work-queue?limit=10&matches_per_job=3")]);setData({dash,priorities,queue})}else{setData({})}})().catch(e=>setErr(e.message))},[]);
 if(err)return <main className="page"><div className="adminError"><b>Workspace unavailable</b><span>{err}</span><p>Use a provisioned Medlivo account.</p></div></main>;
 if(!me||!data)return <main className="page"><div className="adminLoading">Loading Recruit AI…</div></main>;
 if(me.role!=="recruiter")return <main className="shell"><Nav role={me.role}/><section className="content"><header><div><small>Medlivo Recruit AI</small><h1>Today</h1></div></header><section className="hero"><small>{me.role.toUpperCase()} WORKSPACE</small><h2>Welcome, {me.display_name||"team member"}.</h2><p>Your role uses the management and administration views. Recruiter-specific Daily Priorities remain isolated to recruiter accounts.</p><div className="heroActions">{me.role==="admin"&&<a className="linkButton" href="/admin">Open Admin</a>}{me.business_role==="executive"&&<a className="linkButton" href="/executive/margin">Executive GM</a>}{me.system_admin&&<a className="linkButton" href="/admin/gm-config">GM Configuration</a>}<a className="linkButton" href="/manager">Open Manager</a><a className="linkButton" href="/jobs">Jobs</a><a className="linkButton" href="/candidates">Candidates</a></div></section></section></main>;
 const p=data.priorities||{},d=data.dash||{},q=data.queue||{};
 return <main className="shell"><Nav role={me.role}/><section className="content">
   <header><div><small>Recruiter command center</small><h1>Today</h1></div><span className="sourcePill">JOBDIVA · READ ONLY</span></header>
   <section className="hero"><small>DAILY PRIORITIES</small><h2>What should you work on next?</h2><p>Overdue follow-ups come first, then due-soon work and unreviewed Strong/Good matches. The system explains why each candidate is recommended; you make the recruiting decision.</p><div className="heroActions"><a className="linkButton" href="/jobs">Review Jobs</a><a className="linkButton" href="/candidates">Review Candidates</a></div></section>
   <div className="adminMetricGrid recruiterMetrics">
    <article><strong>{p.totals?.overdue_followups??0}</strong><b>Overdue follow-ups</b><span>Work needing immediate action</span></article>
    <article><strong>{p.totals?.due_soon_followups??0}</strong><b>Due soon</b><span>Upcoming recruiter commitments</span></article>
    <article><strong>{p.totals?.match_reviews??0}</strong><b>Match reviews</b><span>Strong/Good matches not yet reviewed</span></article>
    <article><strong>{d.workload?.owned_work_items??0}</strong><b>Owned work</b><span>Current recruiter workload</span></article>
    <article><strong>{d.workload?.active_priority_jobs??0}</strong><b>Priority jobs</b><span>Active jobs requiring attention</span></article>
    <article><strong>{d.workload?.unreviewed_matches??0}</strong><b>Unreviewed matches</b><span>Explainable matches awaiting feedback</span></article>
   </div>
   <h3>Your next actions</h3><div className="priorityList">{(p.items||[]).map((x:any,i:number)=><article key={x.id||i} className={"priorityItem "+(x.urgency||"")}><div><small>{String(x.type||"work").replaceAll("_"," ")}</small><b>{x.title||x.candidate_name||"Review work item"}</b><span>{x.score?"Score "+Number(x.score).toFixed(1)+" · ":""}{x.urgency||"review"}</span></div>{x.job_id&&<a href={"/jobs/"+x.job_id}>Open</a>}</article>)}</div>
   <h3>Priority matching</h3><div className="cards">{(q.items||[]).slice(0,5).map((job:any)=><article key={job.job_id}><strong>{(job.matches||[]).length}</strong><div><b>{job.title}</b><span>JobDiva {job.jobdiva_job_id||"—"} · priority {job.priority??0}</span></div><a className="linkButton" href={"/jobs/"+job.job_id}>Open Job</a></article>)}</div>
 </section></main>
}
function Nav({role}:{role:string}){return <aside className="sidebar"><div className="brand"><div><b>medlivo</b><small> Recruit AI</small></div></div><nav><a className="active" href="/">Today</a><a href="/jobs">Jobs</a><a href="/candidates">Candidates</a><a href="/manager">Manager</a>{role==="admin"&&<a href="/admin">Admin</a>}</nav></aside>}
