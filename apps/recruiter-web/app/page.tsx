"use client";
import Link from "next/link";
import RecruiterToday from "./components/RecruiterToday";
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

 return <RecruiterToday me={me} data={data}/>;

}
