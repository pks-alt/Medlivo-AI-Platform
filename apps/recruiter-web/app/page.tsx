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
async function post(path:string,body:any){
 const sessionResponse=await fetch("/api/team/session",{cache:"no-store",credentials:"same-origin"});
 const session=await sessionResponse.json().catch(()=>({}));
 if(!sessionResponse.ok||!session.csrf)throw new Error("Please reload the workspace before saving.");
 const r=await fetch("/api/team/"+path,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json","X-CSRF-Token":session.csrf,"Idempotency-Key":crypto.randomUUID()},body:JSON.stringify(body)});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
 return b;
}
function daysUntil(v:any){if(!v)return null;const d=new Date(v+"T12:00:00");if(Number.isNaN(d.getTime()))return null;return Math.ceil((d.getTime()-Date.now())/86400000)}
function todayLocal(v:any){if(!v)return false;const d=new Date(v),n=new Date();return d.getFullYear()===n.getFullYear()&&d.getMonth()===n.getMonth()&&d.getDate()===n.getDate()}
export default function Home(){
 const[me,setMe]=useState<any>(null);const[data,setData]=useState<any>(null);const[err,setErr]=useState(""),[actionErr,setActionErr]=useState("");
 useEffect(()=>{(async()=>{
  const who=await get("me");setMe(who);
  if(who.business_role==="recruiter"){
    const[dash,priorities,queue,protectedActions,funnel]=await Promise.all([
      get("recruiter/dashboard?week_start="+monday()),
      get("daily-priorities?limit=40"),
      get("work-queue?limit=20&matches_per_job=5"),
      get("recruiter/protected-actions?limit=50"),
      get("funnel?limit=200")
    ]);
    setData({dash,priorities,queue,protectedActions,funnel});return;
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

 const p=data.priorities||{},d=data.dash||{},q=data.queue||{},pa=data.protectedActions||{},f=data.funnel||{};
 const priority1=(p.items||[]).filter((x:any)=>x.type==="follow_up"||x.work_priority==="priority_1");
 const priority2=(p.items||[]).filter((x:any)=>x.type==="match_review"&&x.work_priority==="priority_2");
 const assignedJobs=(q.items||[]).filter((x:any)=>x.work_priority==="priority_1");
 const newMatches=(p.items||[]).filter((x:any)=>x.type==="match_review").slice(0,6);
 const protectedMine=(pa.items||[]).filter((x:any)=>x.is_mine&&["protected","working"].includes(x.effective_status));
 const supportAvailable=(pa.items||[]).filter((x:any)=>!x.is_mine&&x.effective_status==="available_for_support");
 const funnelItems=f.items||[];
 const interviewsToday=funnelItems.filter((x:any)=>x.interview?.scheduled_at&&todayLocal(x.interview.scheduled_at)&&!x.interview?.completed_at).slice(0,5);
 const upcomingStarts=funnelItems.filter((x:any)=>{const n=daysUntil(x.placement?.planned_start_date);return !x.placement?.actual_start_date&&n!==null&&n>=0&&n<=14}).sort((a:any,b:any)=>daysUntil(a.placement?.planned_start_date)!-daysUntil(b.placement?.planned_start_date)!).slice(0,5);
 const atRiskStarts=upcomingStarts.filter((x:any)=>["high","critical"].includes(String(x.start_readiness?.risk_level||""))||x.start_readiness?.status==="blocked");
 const attention=[...priority1.filter((x:any)=>x.type==="follow_up"),...atRiskStarts.map((x:any)=>({type:"start_risk",title:x.candidate_name,detail:x.job_title,job_id:x.job_id,candidate_id:x.candidate_id,urgency:"at_risk"}))].slice(0,6);

 async function markWorking(jobId:string){
  try{
   await post("jobs/"+jobId+"/protected-action",{action_type:"working",source_type:"medlivo"});
   const refreshed=await get("recruiter/protected-actions?limit=50");
   setData((current:any)=>({...current,protectedActions:refreshed}));
  }catch(e:any){setErr(e.message)}
 }

 const actionHref=(x:any)=>{
   if(x.type==="start_risk"&&x.job_id&&x.candidate_id)return "/funnel/"+x.job_id+"/"+x.candidate_id;
   if(x.type==="follow_up")return "/conversations";
   if(x.job_id&&x.candidate_id)return "/jobs/"+x.job_id;
   if(x.job_id)return "/jobs/"+x.job_id;
   return "/jobs";
 };
 const remaining=(row:any)=>{
   if(row.effective_status==="working")return "Working";
   if(row.effective_status==="available_for_support")return "Available for Support";
   return String(row.remaining_business_minutes??0)+" min protected";
 };

 return <main className="page todayPage recruiterTodayFinal">
   <div className="pageHead"><div><small>Recruiter command center</small><h1>Today</h1><p>Urgent work first, then assigned work, schedule, new matches and division opportunities.</p></div><span className="sourcePill">{me.division||"Rehabilitation"} · LIVE MEDLIVO</span></div>

   <section className="todayWelcome finalTodayHero"><small>YOUR DAY</small><h2>What should you work on next?</h2><p>Medlivo ranks actionable work while Delivery Manager assignment remains the source of Priority 1 accountability.</p></section>
   {actionErr&&<div className="adminError todayActionError"><b>Action could not be saved</b><span>{actionErr}</span></div>}

   <div className="todayMetricGrid">
    <article className={attention.length?"attention":""}><strong>{attention.length}</strong><b>Needs attention</b><span>Replies, follow-ups and start risks</span></article>
    <article><strong>{assignedJobs.length}</strong><b>My jobs</b><span>Priority 1 assignments</span></article>
    <article><strong>{newMatches.length}</strong><b>New strong matches</b><span>Unreviewed evidence-backed matches</span></article>
    <article className={atRiskStarts.length?"attention":""}><strong>{upcomingStarts.length}</strong><b>Upcoming starts</b><span>{atRiskStarts.length} currently at risk</span></article>
   </div>

   <section className="panelBox todayFinalSection"><div className="todaySectionHead"><div><small>NEEDS YOUR ATTENTION</small><h2>Handle these before routine queue work.</h2></div><span>{attention.length} items</span></div>
    {attention.length?<div className="todayActionGrid">{attention.map((x:any,i:number)=><article key={(x.task_id||x.candidate_id||i)+"attention"} className={"todayActionCard "+(x.urgency||"")}>
      <div><small>{x.type==="start_risk"?"UPCOMING START RISK":"FOLLOW-UP"}</small><b>{x.title||"Review work item"}</b><span>{x.detail||x.recommended_next_action||"Needs action"}</span></div>
      <Link href={actionHref(x)}>{x.type==="start_risk"?"Review start":"Continue"}</Link>
    </article>)}</div>:<div className="goodState">You are caught up on urgent actions. Continue with your highest-priority assigned job.</div>}
   </section>

   <section className="panelBox todayFinalSection"><div className="todaySectionHead"><div><small>TIME-SENSITIVE ASSIGNED WORK</small><h2>Protected first-action window</h2></div><span>8 AM–5 PM Pacific · business time</span></div>
    {protectedMine.length?<div className="protectedActionList">{protectedMine.map((x:any)=><article key={x.id} className={"protectedActionCard "+x.effective_status}>
      <div><small>PRIORITY 1 · ASSIGNED TO YOU</small><b>{x.job_title}</b><span>{[x.city,x.state].filter(Boolean).join(", ")} · {remaining(x)}</span></div>
      <div className="protectedActionButtons">{x.effective_status==="protected"&&<button onClick={()=>markWorking(x.job_id)}>Mark Working</button>}<Link href={"/jobs/"+x.job_id}>Open Job 360</Link></div>
    </article>)}</div>:<div className="emptyState">No assigned jobs currently have an open protected first-action window.</div>}
    {supportAvailable.length>0&&<><div className="todaySubhead">AVAILABLE FOR SUPPORT</div><div className="protectedActionList support">{supportAvailable.map((x:any)=><article key={x.id} className="protectedActionCard available_for_support"><div><small>PRIORITY 2 SUPPORT OPPORTUNITY</small><b>{x.job_title}</b><span>Assigned to {x.assigned_recruiter_name} · assignment stays unchanged</span></div><Link href={"/jobs/"+x.job_id}>Help on this job</Link></article>)}</div></>}
   </section>

   <section className="panelBox todayFinalSection"><div className="todaySectionHead"><div><small>MY PRIORITY 1 WORK</small><h2>Assigned jobs ranked by next action</h2></div><Link href="/jobs">View all My Jobs</Link></div>
    {assignedJobs.length?<div className="todayJobGrid">{assignedJobs.slice(0,5).map((job:any)=><article key={job.job_id}><div><small>{job.operational?.job_priority==="hot"?"HIGH PRIORITY":"PRIORITY 1"}</small><b>{job.title}</b><span>{(job.matches||[]).length} candidate matches{job.operational?.next_action?" · "+job.operational.next_action:""}</span></div><Link href={"/jobs/"+job.job_id}>Continue work</Link></article>)}</div>:<div className="emptyState">No assigned active jobs are currently visible.</div>}
   </section>

   <div className="todayTwoColumn">
    <section className="panelBox todayFinalSection"><div className="todaySectionHead"><div><small>TODAY'S SCHEDULE</small><h2>Interviews</h2></div><Link href="/interviews">View all</Link></div>
      {interviewsToday.length?<div className="todayCompactList">{interviewsToday.map((x:any)=><Link key={x.id} href={"/funnel/"+x.job_id+"/"+x.candidate_id}><b>{x.candidate_name||"Candidate"}</b><span>{x.job_title||"Job"} · {new Date(x.interview.scheduled_at).toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}</span></Link>)}</div>:<div className="emptyState">No interviews are scheduled for today.</div>}
    </section>
    <section className="panelBox todayFinalSection"><div className="todaySectionHead"><div><small>UPCOMING STARTS</small><h2>Protect the start</h2></div><Link href="/funnel">View all</Link></div>
      {upcomingStarts.length?<div className="todayCompactList">{upcomingStarts.map((x:any)=><Link key={x.id} className={["high","critical"].includes(String(x.start_readiness?.risk_level||""))?"risk":""} href={"/funnel/"+x.job_id+"/"+x.candidate_id}><b>{x.candidate_name||"Candidate"}</b><span>{x.job_title||"Job"} · starts in {daysUntil(x.placement?.planned_start_date)} days · {x.start_readiness?.status||"readiness pending"}</span></Link>)}</div>:<div className="emptyState">No starts are scheduled in the next 14 days.</div>}
    </section>
   </div>

   <section className="panelBox todayFinalSection"><div className="todaySectionHead"><div><small>NEW STRONG MATCHES</small><h2>Opportunities Medlivo found</h2></div><Link href="/matching">Review Matching</Link></div>
    {newMatches.length?<div className="todayMatchGrid">{newMatches.map((x:any)=><article key={x.match_id}><strong>{Number(x.score||0).toFixed(1)}</strong><div><b>{x.title||x.candidate_name||"Candidate"}</b><span>{x.detail||"Job"} · {x.work_priority==="priority_1"?"Priority 1":"Priority 2"}</span></div><Link href={x.job_id?"/jobs/"+x.job_id:"/matching"}>Review</Link></article>)}</div>:<div className="emptyState">No new strong matches are waiting for review.</div>}
   </section>

   <section className="panelBox todayFinalSection"><div className="todaySectionHead"><div><small>REHABILITATION OPPORTUNITIES YOU CAN HELP WITH</small><h2>Priority 2 · evidence-backed only</h2></div><Link href="/jobs">Division Opportunities</Link></div>
    {priority2.length?<div className="priorityList">{priority2.map((x:any,i:number)=><article key={x.match_id||i} className="priorityItem"><div><small>PRIORITY 2 · NOT ASSIGNED TO YOU</small><b>{x.title||x.candidate_name||"Opportunity"}</b><span>{x.detail||"Division job"} · Score {Number(x.score||0).toFixed(1)} · shown because a real match exists</span></div>{x.job_id&&<Link href={"/jobs/"+x.job_id}>Review opportunity</Link>}</article>)}</div>:<div className="emptyState">No evidence-backed Priority 2 opportunities are waiting right now.</div>}
   </section>
 </main>

}
