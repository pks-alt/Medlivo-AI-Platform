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

  return <main className="page jobsHubPage">
    <div className="pageHead"><div><small>Block 1 · Delivery management</small><h1>Job Distribution</h1><p>Route synchronized and approved jobs to the correct division and recruiter without changing JobDiva ownership.</p></div><span className="sourcePill">MEDLIVO STAGING</span></div>

    <section className="todayWelcome">
      <small>THREE DIVISIONS · ONE PLATFORM</small>
      <h2>Assign responsibility. Keep division visibility broad.</h2>
      <p>Delivery Managers assign Priority 1 ownership. Recruiters still see other active jobs in their own division as Priority 2 opportunities when matching produces a real candidate opportunity.</p>
    </section>

    {error&&<div className="adminError"><b>Latest action could not be completed</b><span>{error}</span></div>}
    {message&&<div className="goodState">{message}</div>}
    {incomplete>0&&<div className="todayDataNotice"><b>Staging data is not yet representative of the Block 1 real-data flow</b><span>{incomplete} job record{incomplete===1?"":"s"} currently lack a JobDiva source link, division classification, or both.</span><p>They remain visible for workflow validation, but they should not be treated as real synchronized JobDiva demand.</p></div>}

    <div className="adminMetricGrid">
      <article><strong>{rows.length}</strong><b>Jobs in view</b><span>Live canonical jobs</span></article>
      <article><strong>{assigned}</strong><b>Assigned</b><span>Primary recruiter responsibility</span></article>
      <article className={unassigned>0?"attention":""}><strong>{unassigned}</strong><b>Unassigned</b><span>Needs Delivery Manager action</span></article>
      <article><strong>{high}</strong><b>High priority</b><span>Manager-directed focus</span></article>
    </div>

    <div className="jobsHubToolbar">
      <div className="jobsStatusFilters">{divisions.map((d:any)=><button key={d} className={division===d?"active":""} onClick={()=>setDivision(d)}>{d}</button>)}</div>
      <button onClick={()=>load().catch(e=>setError(e.message))}>Refresh</button>
    </div>

    <div className="jobsHubList">
      {rows.map((j:any)=>{
        const recruiters=recruitersFor(j);
        const current=j.operational_owner_user_id||"";
        return <article key={j.id} className="jobsHubCard">
          <div className="jobsHubPrimary">
            <small>{j.division||"DIVISION PENDING"}{j.customer_name?" · "+j.customer_name:""} · {j.jobdiva_job_id?"JOBDIVA SYNC":"STAGING CANONICAL RECORD"}</small>
            <h2>{j.title}</h2>
            <p>{[j.profession,j.specialty,[j.city,j.state].filter(Boolean).join(", ")].filter(Boolean).join(" · ")||"Job context incomplete"}</p>
            <span>Assigned recruiter: {j.operational_owner_name||"Unassigned"} · Start {j.start_date||"pending"}</span>
          </div>

          <div className="jobsHubSignals">
            <span><b>{isHigh(j.operational?.job_priority)?"High":"Normal"}</b>Manager priority</span>
            <span><b>{j.match_readiness==="ready"?"Ready":j.match_readiness==="needs_review"?"Review":"Limited"}</b>Match readiness</span>
            <span><b>{j.strong_match_count??0}</b>Strong matches</span>
            <span><b>{j.good_match_count??0}</b>Good matches</span>
          </div>

          <div className="jobsHubFoot">
            <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"}}>
              <select value={current} disabled={!recruiters.length||working===j.id} onChange={e=>assign(j,e.target.value)}>
                <option value="">Assign recruiter</option>
                {recruiters.map((r:any)=><option key={r.id} value={r.id}>{r.display_name} · {r.work_items??0} work items</option>)}
              </select>
              {working===j.id&&<span>Saving assignment...</span>}
            </div>
            <Link href={"/jobs/"+j.id}>Open Job 360</Link>
          </div>
        </article>
      })}
      {!rows.length&&<div className="emptyState">No jobs are available in this division view.</div>}
    </div>

    <div className="job360Boundary"><b>V1 operating rule</b><span>Delivery Manager assignment controls Priority 1 responsibility. It does not hide the job from other recruiters in the same division and it does not mutate JobDiva ownership.</span></div>
  </main>;
}
