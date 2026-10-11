"use client";

import Link from "next/link";
import {useEffect,useMemo,useState} from "react";

async function load(){
 const r=await fetch("/api/team/candidates?limit=100",{cache:"no-store",credentials:"same-origin"});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||"Candidates HTTP "+r.status);
 return b;
}
const readinessLabel=(v:any)=>v==="ready"?"Ready for Recruiter":v==="review"?"Review Needed":"Information Missing";

export default function CandidatesPage(){
 const[data,setData]=useState<any>(null),[error,setError]=useState(""),[query,setQuery]=useState(""),[readiness,setReadiness]=useState("All");
 useEffect(()=>{load().then(setData).catch(e=>setError(e.message))},[]);
 const items=useMemo(()=>{
   const rows=data?.items||[];
   return rows.filter((c:any)=>{
     const q=query.trim().toLowerCase();
     const hay=[c.canonical_name,c.profession,c.specialty,c.city,c.state,c.owner_name,c.team_name,c.division,c.availability?.status].filter(Boolean).join(" ").toLowerCase();
     if(q&&!hay.includes(q))return false;
     if(readiness!=="All"&&c.readiness_status!==readiness)return false;
     return true;
   });
 },[data,query,readiness]);

 if(error)return <main className="page"><div className="adminError"><b>Candidates unavailable</b><span>{error}</span></div></main>;
 if(!data)return <main className="page"><div className="adminLoading">Loading Candidates...</div></main>;

 return <main className="page candidatesHubPage">
  <div className="pageHead"><div><small>Talent intelligence</small><h1>Candidates</h1><p>Trusted candidate profiles, readiness, credentials and best-job intelligence in one place.</p></div><span className="sourcePill">JOBDIVA · READ ONLY</span></div>

  <section className="candidatesHubIntro"><div><small>CANDIDATE INTELLIGENCE</small><h2>Work from one trusted candidate profile.</h2><p>Each candidate brings together source data, healthcare credentials, availability, validation evidence and current job matches without changing JobDiva.</p></div><strong>{items.length}</strong></section>

  <div className="candidatesHubToolbar">
    <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search name, profession, specialty, location or owner" aria-label="Search candidates"/>
    <div className="candidateReadinessFilters">{[
      ["All","All"],["ready","Ready"],["review","Review"],["information_missing","Missing Info"]
    ].map(([value,label])=><button key={value} className={readiness===value?"active":""} onClick={()=>setReadiness(value)}>{label}</button>)}</div>
  </div>

  <div className="candidatesHubList">
    {items.map((c:any)=><article key={c.id} className="candidateHubCard">
      <div className="candidateHubPrimary">
        <small>{c.division||"Unassigned"}{c.team_name?" · "+c.team_name:""}</small>
        <h2>{c.canonical_name||"Unnamed candidate"}</h2>
        <p>{[c.profession,c.specialty,[c.city,c.state].filter(Boolean).join(", ")].filter(Boolean).join(" · ")||"Professional profile incomplete"}</p>
        <span>Owner: {c.owner_name||"Not assigned"}{c.availability?.available_from?" · Available "+c.availability.available_from:""}{c.jobdiva_candidate_id?" · JobDiva linked":""}</span>
      </div>
      <div className="candidateHubSignals">
        <span><b>{readinessLabel(c.readiness_status)}</b>Readiness</span>
        <span><b>{c.active_license_count??0}</b>Active licenses</span>
        <span><b>{c.strong_match_count??0}</b>Strong jobs</span>
        <span><b>{c.good_match_count??0}</b>Good jobs</span>
      </div>
      <div className="candidateHubFoot">
        <span>{c.validation_status?String(c.validation_status).replaceAll("_"," "):"Not screened"} · Profile freshness {c.profile_freshness??"—"}</span>
        <Link href={"/candidates/"+c.id}>Open Candidate 360</Link>
      </div>
    </article>)}
    {!items.length&&<div className="emptyState">No candidates match the current search and readiness filters.</div>}
  </div>
 </main>;
}
