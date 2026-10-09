"use client";
import {useEffect,useState} from "react";

async function load(){
 const r=await fetch("/api/team/candidates?limit=100",{cache:"no-store",credentials:"same-origin"});
 if(!r.ok) throw new Error("Candidates HTTP "+r.status);
 return r.json();
}
export default function CandidatesPage(){
 const [data,setData]=useState<any>(null); const [err,setErr]=useState("");
 useEffect(()=>{load().then(setData).catch(e=>setErr(e.message))},[]);
 if(err)return <main className="page"><div className="adminError"><b>Candidates unavailable</b><span>{err}</span></div></main>;
 if(!data)return <main className="page"><div className="adminLoading">Loading candidates…</div></main>;
 return <main className="page">
  <div className="pageHead"><div><small>Candidate intelligence</small><h1>Candidates</h1><p>Canonical profiles with JobDiva source linkage and enrichment status.</p></div><div className="pageActions"><a href="/">Today</a><a href="/admin">Admin</a></div></div>
  <div className="jobList">{(data.items||[]).map((c:any)=><article className="jobCard" key={c.id}>
    <div><small>{c.jobdiva_candidate_id?"JOBDIVA "+c.jobdiva_candidate_id:"CANONICAL RECORD"}</small><h2>{c.canonical_name||"Unnamed candidate"}</h2><p>{c.profession||"Profession unknown"}{c.specialty?" · "+c.specialty:""} · {[c.city,c.state].filter(Boolean).join(", ")||"Location unknown"}</p></div>
    <div className="jobStats"><span><b>{c.profile_freshness??"—"}</b>Profile freshness</span><span><b>{c.lifecycle_status||"—"}</b>Status</span></div>
    <a href={"/candidates/"+c.id}>Open 360</a>
  </article>)}</div>
 </main>
}