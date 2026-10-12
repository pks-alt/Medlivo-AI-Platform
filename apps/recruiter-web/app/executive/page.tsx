"use client";
import Link from "next/link";
import {useEffect,useMemo,useState} from "react";

function monday(){
 const d=new Date();const diff=(d.getDay()+6)%7;d.setDate(d.getDate()-diff);
 const y=d.getFullYear(),m=String(d.getMonth()+1).padStart(2,"0"),day=String(d.getDate()).padStart(2,"0");
 return `${y}-${m}-${day}`;
}
async function get(path:string){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
 return b;
}
async function optional(path:string){try{return {value:await get(path),error:""}}catch(e:any){return {value:null,error:e?.message||"Unavailable"}}}
const pct=(a:number,b:number)=>b>0?Math.round((a/b)*100):0;
const moneyPct=(v:any)=>(Number(v||0)*100).toFixed(1)+"%";
const risk=(x:any)=>String(x?.start_readiness?.risk_level||"unknown");
const label=(v:any)=>String(v||"").replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());

export default function ExecutivePage(){
 const[me,setMe]=useState<any>(null),[data,setData]=useState<any>(null),[error,setError]=useState("");
 useEffect(()=>{(async()=>{try{
  const who=await get("me");setMe(who);
  if(who.business_role!=="executive")throw new Error("Executive access required");
  const[overview,weekly,funnel,margin,exceptions]=await Promise.all([
   optional("manager/overview"),
   optional("manager/weekly-review?week_start="+monday()),
   optional("funnel?limit=200"),
   optional("margin/management-summary"),
   optional("margin/negative-gm-exceptions?status=pending&limit=100")
  ]);
  setData({overview:overview.value||{},weekly:weekly.value||{},funnel:funnel.value||{},margin:margin.value||{},exceptions:exceptions.value||{items:[]},
   warnings:[
    overview.error&&"Operations: "+overview.error,
    weekly.error&&"Weekly: "+weekly.error,
    funnel.error&&"Submission to Start: "+funnel.error,
    margin.error&&"Margin: "+margin.error,
    exceptions.error&&"Margin exceptions: "+exceptions.error
   ].filter(Boolean)});
 }catch(e:any){setError(e?.message||"Executive view could not be loaded")}})()},[]);

 const divisionRows=useMemo(()=>{
  const map=new Map<string,any>();
  for(const x of data?.funnel?.items||[]){
   const key=x.division||"Unclassified";
   const row=map.get(key)||{division:key,submissions:0,interviews:0,offers:0,placements:0,starts:0,atRisk:0};
   row.submissions++;
   if(x.interview)row.interviews++;
   if(x.offer)row.offers++;
   if(x.placement)row.placements++;
   if(x.placement?.actual_start_date||x.placement?.placement_status==="started")row.starts++;
   if(["high","critical"].includes(risk(x))||x.start_readiness?.status==="blocked")row.atRisk++;
   map.set(key,row);
  }
  return [...map.values()].sort((a,b)=>b.submissions-a.submissions);
 },[data]);

 if(error)return <main className="page"><div className="adminError"><b>Executive view unavailable</b><span>{error}</span></div></main>;
 if(!me||!data)return <main className="page"><div className="adminLoading">Loading Executive command center…</div></main>;

 const o=data.overview||{},ot=o.totals||{},w=data.weekly||{},wt=w.totals||{},f=data.funnel||{},ft=f.totals||{},m=data.margin||{},mt=m.totals||{};
 const atRisk=(f.items||[]).filter((x:any)=>["high","critical"].includes(risk(x))||x.start_readiness?.status==="blocked").slice(0,6);
 const weeklyRisk=(w.recruiters||[]).filter((r:any)=>["at_risk","needs_attention","goal_not_set"].includes(r.delivery_status)).slice(0,8);
 const pendingExceptions=data.exceptions?.items||[];
 const submissionToInterview=pct(ft.interviews??0,ft.submissions??0),interviewToOffer=pct(ft.offers??0,ft.interviews??0),offerToStart=pct(ft.starts??0,ft.offers??0);

 return <main className="page executiveCommandPage">
  <div className="pageHead"><div><small>Executive command center</small><h1>Executive</h1><p>Company operating view across recruiting production, starts, risk and gross margin.</p></div><div className="pageActions"><Link href="/weekly">Weekly</Link><Link href="/funnel">Submission to Start</Link><Link href="/executive/margin">GM Exceptions</Link></div></div>

  {(data.warnings||[]).length>0&&<div className="todayDataNotice"><b>Some executive data is temporarily unavailable</b><span>{data.warnings.join(" · ")}</span><p>The rest of the command center remains available.</p></div>}

  <section className="executiveHero">
   <div><small>LEADERSHIP VIEW</small><h2>Are we producing, converting, and protecting margin?</h2><p>Use this page for the company signal. Drill into Manager, Weekly, Submission to Start, or GM Exceptions only when something needs action.</p></div>
   <span>Week of {monday()}</span>
  </section>

  <div className="executiveMetricGrid">
   <article><strong>{ot.active_recruiters??0}</strong><b>Active recruiters</b><span>{ot.overdue_followups??0} overdue follow-ups</span></article>
   <article><strong>{ft.submissions??0}</strong><b>Submitted</b><span>{submissionToInterview}% reached interview</span></article>
   <article><strong>{ft.interviews??0}</strong><b>Interviews</b><span>{interviewToOffer}% converted to offer</span></article>
   <article><strong>{ft.starts??0}</strong><b>Started</b><span>{offerToStart}% of offers started</span></article>
   <article className={(ft.at_risk_starts??0)>0?"attention":""}><strong>{ft.at_risk_starts??0}</strong><b>At-risk starts</b><span>High / critical readiness risk</span></article>
   <article><strong>{moneyPct(mt.average_gm_percent)}</strong><b>Average GM</b><span>{mt.finalized??0} finalized packages</span></article>
   <article className={(mt.negative_gm??0)>0?"attention":""}><strong>{mt.negative_gm??0}</strong><b>Negative GM</b><span>{pendingExceptions.length} awaiting decision</span></article>
   <article><strong>{wt.goals_set??0} / {wt.recruiters??0}</strong><b>Weekly goals set</b><span>{wt.starts_actual??0} starts this weekly snapshot</span></article>
  </div>

  <div className="executiveTwo">
   <section className="panelBox"><div className="executiveSectionHead"><div><small>DELIVERY RISK</small><h2>Starts needing leadership attention</h2></div><Link href="/funnel">Open pipeline</Link></div>
    {atRisk.length?<div className="executiveRiskList">{atRisk.map((x:any)=><Link key={x.id} href={"/funnel/"+x.job_id+"/"+x.candidate_id}><div><b>{x.candidate_name||"Candidate"}</b><span>{x.job_title||"Job"} · {x.division||"Division pending"}</span><small>{x.start_readiness?.next_action||"Next action not assigned"}</small></div><strong>{label(risk(x))}</strong></Link>)}</div>:<div className="goodState">No high or critical start risks are currently visible.</div>}
   </section>

   <section className="panelBox"><div className="executiveSectionHead"><div><small>WEEKLY EXECUTION</small><h2>Recruiters needing attention</h2></div><Link href="/weekly">Open Weekly</Link></div>
    {weeklyRisk.length?<div className="executiveWeeklyList">{weeklyRisk.map((r:any)=><article key={r.id}><div><b>{r.display_name||r.email}</b><span>{label(r.delivery_status)}</span></div><strong>{r.attainment==null?"—":r.attainment+"%"}</strong><small>{r.actuals?.submissions??0}/{r.targets?.submissions??0} submissions · {r.actuals?.interviews??0}/{r.targets?.interviews??0} interviews · {r.actuals?.closures??0}/{r.targets?.closures??0} closures</small></article>)}</div>:<div className="goodState">No weekly execution exceptions are currently visible.</div>}
   </section>
  </div>

  <section className="panelBox"><div className="executiveSectionHead"><div><small>DIVISION PERFORMANCE</small><h2>Submission-to-start by division</h2></div><Link href="/manager">Open Manager</Link></div>
   {divisionRows.length?<div className="adminTableWrap"><table className="adminTable"><thead><tr><th>Division</th><th>Submitted</th><th>Interview</th><th>Offer</th><th>Placement</th><th>Started</th><th>At Risk</th></tr></thead><tbody>{divisionRows.map((r:any)=><tr key={r.division}><td><b>{r.division}</b></td><td>{r.submissions}</td><td>{r.interviews}</td><td>{r.offers}</td><td>{r.placements}</td><td>{r.starts}</td><td>{r.atRisk}</td></tr>)}</tbody></table></div>:<div className="emptyState">No Submission-to-Start records are available to summarize by division yet.</div>}
  </section>

  <section className="panelBox"><div className="executiveSectionHead"><div><small>COMMERCIAL CONTROL</small><h2>Margin exceptions</h2></div><Link href="/executive/margin">Open GM & Rate Exceptions</Link></div>
   <div className="executiveCommercialGrid"><article><strong>{mt.current_packages??0}</strong><b>Current packages</b></article><article><strong>{moneyPct(mt.finalized_average_gm_percent)}</strong><b>Finalized average GM</b></article><article><strong>{mt.discussion_required??0}</strong><b>Needs discussion</b></article><article><strong>{pendingExceptions.length}</strong><b>Executive decisions pending</b></article></div>
  </section>
 </main>;
}
