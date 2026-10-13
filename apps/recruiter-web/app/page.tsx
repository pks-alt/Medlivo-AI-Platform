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
async function optional(path:string){
 try{return {ok:true,data:await get(path),error:""}}
 catch(e:any){return {ok:false,data:null,error:e?.message||"Unavailable"}}
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
  const [overview,funnel,margin,ops]=await Promise.all([
    optional("manager/overview"),
    optional("funnel?limit=200"),
    optional("margin/management-summary"),
    (who.system_admin||who.role==="admin")?optional("admin/operations"):Promise.resolve({ok:false,data:null,error:"Not applicable"})
  ]);
  setData({overview:overview.data,funnel:funnel.data,margin:margin.data,ops:ops.data,sources:{overview,funnel,margin,ops}});
 })().catch(e=>setErr(e.message))},[]);

 if(err)return <main className="page"><div className="adminError"><b>Workspace unavailable</b><span>{err}</span><p>Use a provisioned Medlivo account.</p></div></main>;
 if(!me||!data)return <main className="page"><div className="adminLoading">Loading Recruit AI...</div></main>;

 if(me.business_role!=="recruiter"){
   const o=data.overview||{},f=data.funnel||{},ft=f.totals||{},m=data.margin||{},mt=m.totals||{},ops=data.ops||{};
   const canon=ops.canonical||{},src=ops.source_counts||{},sources=data.sources||{};
   const atRisk=(f.items||[]).filter((x:any)=>["high","critical"].includes(String(x.start_readiness?.risk_level||""))).slice(0,5);
   const missing=[
    !sources.overview?.ok&&"Recruiting operations",
    !sources.funnel?.ok&&"Submission to Start",
    !sources.margin?.ok&&"Gross Margin",
    (me.system_admin||me.role==="admin")&&!sources.ops?.ok&&"Platform operations"
   ].filter(Boolean);
   const metric=(ok:boolean,value:any,suffix="")=>ok?String(value??0)+suffix:"—";
   return <main className="page todayPage">
    <div className="pageHead"><div><small>{me.business_role==="executive"?"Executive command center":"Management command center"}</small><h1>Today</h1><p>What needs attention across recruiting, starts, commercial performance and platform operations.</p></div><span className="sourcePill">LIVE MEDLIVO WORKSPACE</span></div>

    <section className="todayWelcome"><small>{me.business_role==="executive"?"EXECUTIVE WORKSPACE":"MANAGEMENT WORKSPACE"}</small><h2>Welcome, {me.display_name||"team member"}.</h2><p>Use the navigation on the left to move through the application. This page is your operating summary, not a launcher.</p></section>
    {missing.length>0&&<div className="todayDataNotice"><b>Some dashboard data is unavailable</b><span>{missing.join(" · ")}</span><p>The rest of Today is still available. This can be caused by role scope or a temporary service issue.</p></div>}

    <div className="todayMetricGrid">
      <article><strong>{metric(Boolean(sources.overview?.ok),o.totals?.active_recruiters)}</strong><b>Active recruiters</b><span>Current managed recruiting capacity</span></article>
      <article><strong>{metric(Boolean(sources.overview?.ok),o.totals?.overdue_followups)}</strong><b>Overdue follow-ups</b><span>Work needing immediate attention</span></article>
      <article><strong>{metric(Boolean(sources.funnel?.ok),ft.submissions)}</strong><b>Submitted</b><span>Current Submission-to-Start funnel</span></article>
      <article className={sources.funnel?.ok&&(ft.at_risk_starts??0)>0?"attention":""}><strong>{metric(Boolean(sources.funnel?.ok),ft.at_risk_starts)}</strong><b>At-risk starts</b><span>High or critical start risk</span></article>
      <article><strong>{sources.margin?.ok?((Number(mt.average_gm_percent||0))*100).toFixed(1)+"%":"—"}</strong><b>Average GM</b><span>Across current rate packages</span></article>
      <article className={sources.margin?.ok&&(mt.negative_gm??0)>0?"attention":""}><strong>{metric(Boolean(sources.margin?.ok),mt.negative_gm)}</strong><b>Negative GM</b><span>Commercial exceptions needing review</span></article>
      {(me.system_admin||me.role==="admin")&&<article><strong>{metric(Boolean(sources.ops?.ok),canon.open_jobs)}</strong><b>Open jobs</b><span>{sources.ops?.ok?(src.jobs_enriched??0)+" JobDiva jobs enriched":"Platform data unavailable"}</span></article>}
      {(me.system_admin||me.role==="admin")&&<article><strong>{metric(Boolean(sources.ops?.ok),canon.strong_matches)}</strong><b>Strong matches</b><span>High-confidence matches available</span></article>}
    </div>

    <div className="todayGrid">
      <section className="panelBox"><small>STARTS NEEDING ATTENTION</small>
        {!sources.funnel?.ok?<div className="emptyState">Submission-to-Start data is unavailable for this role or session.</div>:atRisk.length?<div className="todayList">{atRisk.map((x:any)=><Link key={x.id} href={"/funnel/"+x.job_id+"/"+x.candidate_id}><div><b>{x.candidate_name||"Candidate"}</b><span>{x.job_title||"Job"} · {x.recruiter_name||"Recruiter"}</span></div><strong>{String(x.start_readiness?.risk_level||"risk").toUpperCase()}</strong></Link>)}</div>:<div className="goodState">No high or critical start risks are currently visible.</div>}
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
 const priority1=(p.items||[]).filter((x:any)=>x.type==="follow_up"||x.work_priority==="priority_1");
 const priority2=(p.items||[]).filter((x:any)=>x.type==="match_review"&&x.work_priority==="priority_2");
 const assignedJobs=(q.items||[]).filter((x:any)=>x.work_priority==="priority_1");
 const divisionJobs=(q.items||[]).filter((x:any)=>x.work_priority==="priority_2");
 const actionCard=(x:any,i:number)=><article key={x.id||x.match_id||i} className={"priorityItem "+(x.urgency||"")}><div><small>{x.work_priority==="priority_2"?"PRIORITY 2 · DIVISION OPPORTUNITY":String(x.type||"work").replaceAll("_"," ")}</small><b>{x.title||x.candidate_name||"Review work item"}</b><span>{x.detail?x.detail+" · ":""}{x.score?"Score "+Number(x.score).toFixed(1)+" · ":""}{x.urgency||"review"}</span></div>{x.job_id&&<Link href={"/jobs/"+x.job_id}>Open</Link>}</article>;
 return <main className="page todayPage">
   <div className="pageHead"><div><small>Recruiter command center</small><h1>Today</h1><p>Your assigned work first, then AI-ranked opportunities across your division.</p></div><span className="sourcePill">LIVE MEDLIVO · JOBDIVA SYNC</span></div>
   <section className="todayWelcome"><small>DAILY WORK ORDER</small><h2>Priority 1 first. Never lose sight of Priority 2.</h2><p>Delivery Manager assignments define Priority 1. You can still see strong opportunities from other active jobs in your division as Priority 2.</p></section>
   <div className="adminMetricGrid recruiterMetrics">
    <article><strong>{p.totals?.overdue_followups??0}</strong><b>Overdue follow-ups</b><span>Work needing immediate action</span></article>
    <article><strong>{p.totals?.due_soon_followups??0}</strong><b>Due soon</b><span>Upcoming recruiter commitments</span></article>
    <article><strong>{p.totals?.priority_1_matches??0}</strong><b>Priority 1 matches</b><span>Matches on your assigned jobs</span></article>
    <article><strong>{p.totals?.priority_2_matches??0}</strong><b>Priority 2 matches</b><span>Other opportunities in your division</span></article>
    <article><strong>{d.workload?.owned_work_items??0}</strong><b>Owned work</b><span>Current recruiter workload</span></article>
    <article><strong>{d.workload?.unreviewed_matches??0}</strong><b>Unreviewed matches</b><span>Explainable matches awaiting feedback</span></article>
   </div>
   <h3>Priority 1 · My assigned work</h3><div className="priorityList">{priority1.length?priority1.map(actionCard):<div className="emptyState">No assigned actions need attention right now.</div>}</div>
   <h3>Priority 2 · Division opportunities</h3><div className="priorityList">{priority2.length?priority2.map(actionCard):<div className="emptyState">No additional strong division opportunities are waiting right now.</div>}</div>
   <h3>Jobs with candidate matches</h3>
   <div className="cards">{[...assignedJobs,...divisionJobs].slice(0,8).map((job:any)=><article key={job.job_id}><strong>{(job.matches||[]).length}</strong><div><b>{job.title}</b><span>{job.work_priority==="priority_1"?"Priority 1 · Assigned to you":"Priority 2 · Division opportunity"} · JobDiva {job.jobdiva_job_id||"—"}</span></div><Link className="linkButton" href={"/jobs/"+job.job_id}>Open Job</Link></article>)}</div>
 </main>
}
