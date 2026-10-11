"use client";
import Link from "next/link";
import {useEffect,useState} from "react";

function monday(){
 const d=new Date(); const day=d.getDay(); const diff=(day+6)%7; d.setDate(d.getDate()-diff);
 return d.toISOString().slice(0,10);
}
async function get(path:string){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
 return b;
}
export default function Home(){
 const[me,setMe]=useState<any>(null);const[data,setData]=useState<any>(null);const[err,setErr]=useState("");
 useEffect(()=>{(async()=>{
  const who=await get("me");setMe(who);
  if(who.business_role==="recruiter"){
    const[dash,priorities,queue]=await Promise.all([
      get("recruiter/dashboard?week_start="+monday()),
      get("daily-priorities?limit=20"),
      get("work-queue?limit=10&matches_per_job=3")
    ]);
    setData({dash,priorities,queue});return;
  }
  const requests=[
    get("manager/overview"),
    get("funnel?limit=200"),
    get("margin/management-summary")
  ];
  if(who.system_admin||who.role==="admin")requests.push(get("admin/operations"));
  const results=await Promise.all(requests);
  setData({overview:results[0],funnel:results[1],margin:results[2],ops:results[3]||null});
 })().catch(e=>setErr(e.message))},[]);

 if(err)return <main className="page"><div className="adminError"><b>Workspace unavailable</b><span>{err}</span><p>Use a provisioned Medlivo account.</p></div></main>;
 if(!me||!data)return <main className="page"><div className="adminLoading">Loading Recruit AI...</div></main>;

 if(me.business_role!=="recruiter"){
   const o=data.overview||{},f=data.funnel||{},ft=f.totals||{},m=data.margin||{},mt=m.totals||{},ops=data.ops||{};
   const canon=ops.canonical||{},src=ops.source_counts||{};
   const atRisk=(f.items||[]).filter((x:any)=>["high","critical"].includes(String(x.start_readiness?.risk_level||""))).slice(0,5);
   return <main className="page todayPage">
    <div className="pageHead"><div><small>{me.business_role==="executive"?"Executive command center":"Management command center"}</small><h1>Today</h1><p>What needs attention across recruiting, starts, commercial performance and platform operations.</p></div><span className="sourcePill">LIVE MEDLIVO WORKSPACE</span></div>

    <section className="todayWelcome"><small>{me.business_role==="executive"?"EXECUTIVE WORKSPACE":"MANAGEMENT WORKSPACE"}</small><h2>Welcome, {me.display_name||"team member"}.</h2><p>Use the navigation on the left to move through the application. This page is your operating summary, not a launcher.</p></section>

    <div className="todayMetricGrid">
      <article><strong>{o.totals?.active_recruiters??0}</strong><b>Active recruiters</b><span>Current managed recruiting capacity</span></article>
      <article><strong>{o.totals?.overdue_followups??0}</strong><b>Overdue follow-ups</b><span>Work needing immediate attention</span></article>
      <article><strong>{ft.submissions??0}</strong><b>Submitted</b><span>Current Submission-to-Start funnel</span></article>
      <article className={(ft.at_risk_starts??0)>0?"attention":""}><strong>{ft.at_risk_starts??0}</strong><b>At-risk starts</b><span>High or critical start risk</span></article>
      <article><strong>{((Number(mt.average_gm_percent||0))*100).toFixed(1)}%</strong><b>Average GM</b><span>Across current rate packages</span></article>
      <article className={(mt.negative_gm??0)>0?"attention":""}><strong>{mt.negative_gm??0}</strong><b>Negative GM</b><span>Commercial exceptions needing review</span></article>
      {data.ops&&<article><strong>{canon.open_jobs??0}</strong><b>Open jobs</b><span>{src.jobs_enriched??0} JobDiva jobs enriched</span></article>}
      {data.ops&&<article><strong>{canon.strong_matches??0}</strong><b>Strong matches</b><span>High-confidence matches available</span></article>}
    </div>

    <div className="todayGrid">
      <section className="panelBox"><small>STARTS NEEDING ATTENTION</small>
        {atRisk.length?<div className="todayList">{atRisk.map((x:any)=><Link key={x.id} href={"/funnel/"+x.job_id+"/"+x.candidate_id}><div><b>{x.candidate_name||"Candidate"}</b><span>{x.job_title||"Job"} · {x.recruiter_name||"Recruiter"}</span></div><strong>{String(x.start_readiness?.risk_level||"risk").toUpperCase()}</strong></Link>)}</div>:<div className="goodState">No high or critical start risks are currently visible.</div>}
      </section>
      <section className="panelBox"><small>RECRUITING OPERATIONS</small>
        <div className="adminRows">
          <div><span>Work items</span><b>{o.totals?.work_items??0}</b></div>
          <div><span>Open follow-ups</span><b>{o.totals?.open_followups??0}</b></div>
          <div><span>Placements</span><b>{ft.placements??0}</b></div>
          <div><span>Started</span><b>{ft.starts??0}</b></div>
          <div><span>Finalized rate packages</span><b>{mt.finalized??0}</b></div>
        </div>
      </section>
    </div>
   </main>;
 }

 const p=data.priorities||{},d=data.dash||{},q=data.queue||{};
 return <main className="page todayPage">
   <div className="pageHead"><div><small>Recruiter command center</small><h1>Today</h1><p>Prioritized recruiter work and explainable candidate matching.</p></div><span className="sourcePill">JOBDIVA · READ ONLY</span></div>
   <section className="todayWelcome"><small>DAILY PRIORITIES</small><h2>What should you work on next?</h2><p>Overdue follow-ups come first, then due-soon work and unreviewed Strong/Good matches. You make the recruiting decision.</p></section>
   <div className="adminMetricGrid recruiterMetrics">
    <article><strong>{p.totals?.overdue_followups??0}</strong><b>Overdue follow-ups</b><span>Work needing immediate action</span></article>
    <article><strong>{p.totals?.due_soon_followups??0}</strong><b>Due soon</b><span>Upcoming recruiter commitments</span></article>
    <article><strong>{p.totals?.match_reviews??0}</strong><b>Match reviews</b><span>Strong/Good matches not yet reviewed</span></article>
    <article><strong>{d.workload?.owned_work_items??0}</strong><b>Owned work</b><span>Current recruiter workload</span></article>
    <article><strong>{d.workload?.active_priority_jobs??0}</strong><b>Priority jobs</b><span>Active jobs requiring attention</span></article>
    <article><strong>{d.workload?.unreviewed_matches??0}</strong><b>Unreviewed matches</b><span>Explainable matches awaiting feedback</span></article>
   </div>
   <h3>Your next actions</h3><div className="priorityList">{(p.items||[]).map((x:any,i:number)=><article key={x.id||i} className={"priorityItem "+(x.urgency||"")}><div><small>{String(x.type||"work").replaceAll("_"," ")}</small><b>{x.title||x.candidate_name||"Review work item"}</b><span>{x.score?"Score "+Number(x.score).toFixed(1)+" · ":""}{x.urgency||"review"}</span></div>{x.job_id&&<Link href={"/jobs/"+x.job_id}>Open</Link>}</article>)}</div>
   <h3>Priority matching</h3><div className="cards">{(q.items||[]).slice(0,5).map((job:any)=><article key={job.job_id}><strong>{(job.matches||[]).length}</strong><div><b>{job.title}</b><span>JobDiva {job.jobdiva_job_id||"—"} · priority {job.priority??0}</span></div><Link className="linkButton" href={"/jobs/"+job.job_id}>Open Job</Link></article>)}</div>
 </main>
}
