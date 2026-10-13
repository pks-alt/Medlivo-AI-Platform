"use client";

import Link from "next/link";
import {useEffect,useMemo,useState} from "react";

async function api(path:string,options:RequestInit={}){
  const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
  const b=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
  return b;
}
const text=(v:any)=>String(v||"").replaceAll("_"," ").replace(/\b\w/g,m=>m.toUpperCase());
const isHigh=(v:any)=>["hot","priority"].includes(String(v||""));

export default function DistributionPage(){
  const[me,setMe]=useState<any>(null);
  const[jobs,setJobs]=useState<any[]>([]);
  const[overview,setOverview]=useState<any>({teams:[],recruiters:[],totals:{}});
  const[division,setDivision]=useState("All");
  const[working,setWorking]=useState("");
  const[message,setMessage]=useState("");
  const[error,setError]=useState("");

  async function load(){
    setError("");
    const[who,jobPage,manager]=await Promise.all([
      api("me"),
      api("jobs?limit=100"),
      api("manager/overview")
    ]);
    setMe(who);setJobs(jobPage.items||[]);setOverview(manager||{});
  }
  useEffect(()=>{load().catch(e=>setError(e.message))},[]);

  const divisions=useMemo(()=>["All",...Array.from(new Set((jobs||[]).map((j:any)=>j.division).filter(Boolean)))],[jobs]);
  const rows=useMemo(()=>jobs.filter((j:any)=>division==="All"||j.division===division),[jobs,division]);
  const teamById=useMemo(()=>Object.fromEntries((overview.teams||[]).map((t:any)=>[t.id,t])),[overview]);
  const recruitersFor=(job:any)=>(overview.recruiters||[]).filter((r:any)=>teamById[r.team_id]?.division===job.division);

  async function assign(job:any,recruiterId:string){
    const recruiter=(overview.recruiters||[]).find((r:any)=>r.id===recruiterId);
    if(!recruiter)return;
    setWorking(job.id);setMessage("");setError("");
    try{
      await api("jobs/"+job.id+"/assignment",{
        method:"PUT",
        headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},
        body:JSON.stringify({
          recruiter_user_id:recruiter.id,
          team_id:recruiter.team_id,
          reason:"Delivery Manager Block 1 assignment",
          expected_version:job.operational?.version||0
        })
      });
      setMessage("Assigned "+job.title+" to "+recruiter.display_name+".");
      await load();
    }catch(e:any){setError(e.message)}
    finally{setWorking("")}
  }

  if(error&&!me)return <main className="page"><div className="adminError"><b>Job Distribution unavailable</b><span>{error}</span></div></main>;
  if(!me)return <main className="page"><div className="adminLoading">Loading Job Distribution...</div></main>;
  if(me.business_role==="recruiter")return <main className="page"><div className="adminError"><b>Delivery Manager access required</b><span>Recruiters see assigned Priority 1 and division Priority 2 work from Today and Jobs.</span></div></main>;

  const assigned=rows.filter((j:any)=>j.operational_owner_user_id).length;
  const unassigned=rows.length-assigned;
  const high=rows.filter((j:any)=>isHigh(j.operational?.job_priority)).length;
  const incomplete=rows.filter((j:any)=>!j.division||!j.jobdiva_job_id).length;
  const counts=(name:string)=>jobs.filter((j:any)=>j.division===name).length;
  const actionCount=unassigned+high+incomplete;

  return <main className="page distributionPage">
    <div className="pageHead">
      <div><small>BLOCK 1 · DELIVERY MANAGEMENT</small><h1>Job Distribution</h1><p>Turn incoming demand into clear recruiter responsibility across Rehabilitation, Nursing & Allied, and Locum Tenens.</p></div>
      <span className="sourcePill">MEDLIVO STAGING</span>
    </div>

    <section className="blockFlow">
      <div className="done"><span>1</span><b>Intake</b><small>JobDiva + Excel</small></div>
      <i>→</i>
      <div className="current"><span>2</span><b>Distribution</b><small>Division + recruiter</small></div>
      <i>→</i>
      <div><span>3</span><b>Recruiter Work</b><small>Priority 1 + 2</small></div>
    </section>

    <section className="distributionHero">
      <div>
        <small>DELIVERY MANAGER CONTROL</small>
        <h2>Assign the right job to the right recruiter.</h2>
        <p>Assignment sets Priority 1 responsibility. Other recruiters in the same division can still discover qualified Priority 2 opportunities without changing JobDiva ownership.</p>
      </div>
      <div className="distributionHeroAction">
        <strong>{actionCount}</strong>
        <span>items needing attention</span>
        <button onClick={()=>load().catch(e=>setError(e.message))}>Refresh live data</button>
      </div>
    </section>

    {error&&<div className="adminError distributionInlineError"><b>Latest action could not be completed</b><span>{error}</span></div>}
    {message&&<div className="goodState distributionMessage">{message}</div>}
    {incomplete>0&&<div className="todayDataNotice"><b>Staging data still has incomplete records</b><span>{incomplete} job record{incomplete===1?"":"s"} lack a JobDiva source link, division classification, or both.</span><p>These records remain visible for workflow validation, but they are not proof of the real JobDiva feed.</p></div>}

    <section className="distributionMetrics">
      <article><small>TOTAL DEMAND</small><strong>{rows.length}</strong><span>jobs in current view</span></article>
      <article><small>ASSIGNED</small><strong>{assigned}</strong><span>Priority 1 ownership set</span></article>
      <article className={unassigned?"attention":""}><small>UNASSIGNED</small><strong>{unassigned}</strong><span>needs manager assignment</span></article>
      <article className={high?"attention":""}><small>HIGH PRIORITY</small><strong>{high}</strong><span>manager-directed focus</span></article>
    </section>

    <section className="divisionLaneGrid">
      {[
        ["Rehabilitation",counts("Rehabilitation"),"Travel contracts · 13+ weeks"],
        ["Nursing & Allied",counts("Nursing & Allied"),"Contract staffing · no per-diem"],
        ["Locum Tenens",counts("Locum Tenens"),"Locums · call / clinic / coverage"],
      ].map(([name,count,desc]:any)=><button key={name} className={division===name?"active":""} onClick={()=>setDivision(division===name?"All":name)}>
        <span>{name}</span><strong>{count}</strong><small>{desc}</small>
      </button>)}
    </section>

    <section className="distributionToolbar">
      <div>
        <small>VIEW</small>
        <div className="distributionFilters">{["All",...divisions.filter((d:any)=>d!=="All")].map((d:any)=><button key={d} className={division===d?"active":""} onClick={()=>setDivision(d)}>{d}</button>)}</div>
      </div>
      <span>{rows.length} job{rows.length===1?"":"s"} shown</span>
    </section>

    <section className="distributionQueue">
      <div className="distributionQueueHead">
        <div><small>JOB</small></div>
        <div><small>PRIORITY</small></div>
        <div><small>MATCHING</small></div>
        <div><small>ASSIGNED RECRUITER</small></div>
        <div><small>ACTION</small></div>
      </div>

      {rows.map((j:any)=>{
        const recruiters=recruitersFor(j);
        const current=j.operational_owner_user_id||"";
        const dataState=!j.division||!j.jobdiva_job_id?"needs_review":"ready";
        return <article key={j.id} className={"distributionRow "+(isHigh(j.operational?.job_priority)?"high":"")}>
          <div className="distributionJob">
            <div className="distributionJobTop">
              <span className={"dataSourceBadge "+dataState}>{j.jobdiva_job_id?"JOBDIVA":"STAGING"}</span>
              <span>{j.division||"Division pending"}</span>
            </div>
            <b>{j.title}</b>
            <small>{[j.customer_name,j.profession,j.specialty,[j.city,j.state].filter(Boolean).join(", ")].filter(Boolean).join(" · ")||"Job details need review"}</small>
            <em>Start {j.start_date||"pending"}</em>
          </div>
          <div className="distributionPriority">
            <b>{isHigh(j.operational?.job_priority)?"High":"Normal"}</b>
            <span>{j.operational?.priority_reason||"No manager escalation"}</span>
          </div>
          <div className="distributionMatch">
            <div><strong>{j.strong_match_count??0}</strong><span>Strong</span></div>
            <div><strong>{j.good_match_count??0}</strong><span>Good</span></div>
            <small>{j.match_readiness==="ready"?"Ready to match":j.match_readiness==="needs_review"?"Review job data":"Limited data"}</small>
          </div>
          <div className="distributionAssign">
            <b>{j.operational_owner_name||"Unassigned"}</b>
            <select value={current} disabled={!recruiters.length||working===j.id} onChange={e=>assign(j,e.target.value)}>
              <option value="">Assign recruiter</option>
              {recruiters.map((r:any)=><option key={r.id} value={r.id}>{r.display_name} · {r.work_items??0} active</option>)}
            </select>
            {working===j.id&&<small>Saving...</small>}
            {!recruiters.length&&<small>No recruiter available for this division</small>}
          </div>
          <div className="distributionAction">
            <Link href={"/jobs/"+j.id}>Open Job 360</Link>
            <small>{current?"Priority 1 assigned":"Assignment needed"}</small>
          </div>
        </article>
      })}
      {!rows.length&&<div className="emptyState">No jobs are available in this division view.</div>}
    </section>

    <section className="distributionRule">
      <b>Block 1 rule</b>
      <span>Delivery Manager assignment sets Priority 1 accountability. Same-division visibility remains open for Priority 2 matching opportunities. JobDiva source ownership is not changed.</span>
    </section>
  </main>;
}
