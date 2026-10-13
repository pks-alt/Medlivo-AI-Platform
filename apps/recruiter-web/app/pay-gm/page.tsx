"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
async function api(path:string){const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);return b}
export default function PayGMEntryPage(){
 const[jobs,setJobs]=useState<any[]>([]),[candidates,setCandidates]=useState<any[]>([]),[jobId,setJobId]=useState(""),[candidateId,setCandidateId]=useState(""),[error,setError]=useState("");
 useEffect(()=>{Promise.all([api("jobs?limit=100"),api("candidates?limit=100")]).then(([j,c])=>{setJobs(j.items||[]);setCandidates(c.items||[])}).catch(e=>setError(e.message))},[]);
 if(error)return <main className="page"><div className="adminError"><b>Pay & GM unavailable</b><span>{error}</span></div></main>;
 const ready=jobId&&candidateId;
 return <main className="page payGMEntryPage">
  <div className="pageHead"><div><small>Commercial decision workspace</small><h1>Pay & GM</h1><p>Select a real candidate/job pair, then open the existing Medlivo pay-package and margin calculator. No sample commercial data is inserted here.</p></div><span className="sourcePill">REAL MEDLIVO RECORDS</span></div>
  <section className="payGMSelector panelBox"><small>SELECT WORK CONTEXT</small><div className="payGMFields"><label>Candidate<select value={candidateId} onChange={e=>setCandidateId(e.target.value)}><option value="">Choose candidate…</option>{candidates.map(c=><option key={c.id} value={c.id}>{c.canonical_name||c.id}</option>)}</select></label><label>Job<select value={jobId} onChange={e=>setJobId(e.target.value)}><option value="">Choose job…</option>{jobs.map(j=><option key={j.id} value={j.id}>{j.title||j.id}</option>)}</select></label></div>{ready?<Link className="button primary" href={"/jobs/"+jobId+"/candidates/"+candidateId+"/pay-package"}>Open Pay Package & Margin</Link>:<p className="sectionHelp">Candidate and job context are required so package versions, GM guardrails and audit history stay attached to the correct pair.</p>}</section>
  <div className="matchingGuardrail"><b>Commercial guardrail</b><span>The underlying calculator remains recruiter-owned, versioned and policy-controlled. This entry page does not change margin logic or authorization.</span></div>
 </main>;
}
