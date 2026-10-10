"use client";
import {useEffect,useState} from "react";

async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const body=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(body.detail||path+" HTTP "+r.status);
 return body;
}
const names:any={
 nursing_allied_ca_w2:"Nursing & Allied · California W-2",
 nursing_allied_national_w2:"Nursing & Allied · National W-2",
 rehabilitation_ca_w2:"Rehabilitation · California W-2",
 rehabilitation_national_w2:"Rehabilitation · National W-2",
 locums_ca_w2:"Locums · California W-2",
 locums_national_1099:"Locums · Nationwide 1099"
};
const source:any={
 nursing_allied_ca_w2:"Anand",
 nursing_allied_national_w2:"Anand",
 rehabilitation_ca_w2:"Prachi",
 rehabilitation_national_w2:"Prachi",
 locums_ca_w2:"CA Locums W-2",
 locums_national_1099:"Locums 1099"
};
export default function GMConfigPage(){
 const[me,setMe]=useState<any>(null),[rows,setRows]=useState<any[]>([]),[error,setError]=useState(""),[working,setWorking]=useState(false),[message,setMessage]=useState("");
 async function refresh(){
  const m=await api("me");setMe(m);
  const profiles=Object.keys(names);
  const groups=await Promise.all(profiles.map(async p=>{const x=await api("economic-config/assumptions?profile="+p+"&limit=10");return (x.items||[]).map((r:any)=>({...r,profile:p}))}));
  setRows(groups.flat());
 }
 useEffect(()=>{refresh().catch(e=>setError(e.message))},[]);
 async function bootstrap(){
  setWorking(true);setError("");setMessage("");
  try{
   const r=await api("economic-config/bootstrap-assumptions",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:"{}"});
   setMessage(r.created.length?String(r.created.length)+" approved calculator profile(s) initialized.":"All approved calculator profiles were already configured.");
   await refresh();
  }catch(e:any){setError(e.message)}finally{setWorking(false)}
 }
 if(error&&!me)return <main className="page"><div className="adminError"><b>GM configuration unavailable</b><span>{error}</span></div></main>;
 if(!me)return <main className="page"><div className="adminLoading">Loading GM configuration…</div></main>;
 if(!me.system_admin)return <main className="page"><div className="adminError"><b>System Admin access required</b><span>Company calculator assumptions are protected configuration.</span></div></main>;
 const current=Object.keys(names).map(p=>({profile:p,row:rows.filter(x=>x.profile===p&&x.status==="active").sort((a:any,b:any)=>String(b.effective_from).localeCompare(String(a.effective_from)))[0]}));
 return <main className="page gmConfigPage">
  <div className="pageHead"><div><small>System Administration · Gross Margin</small><h1>GM Configuration</h1><p>Protected calculator assumptions and workbook-source versions used by recruiter pricing.</p></div><div className="pageActions"><a href="/admin">Admin</a><a href="/executive/margin">Executive GM</a></div></div>
  <section className="gmConfigIntro"><div><b>Approved calculator profiles</b><p>Recruiters cannot change these values. Each calculation stores the exact assumption version used.</p></div><button onClick={bootstrap} disabled={working}>{working?"Initializing…":"Initialize Missing Approved Profiles"}</button></section>
  {message&&<div className="goodState">{message}</div>}{error&&<div className="payError">{error}</div>}
  <div className="gmProfileGrid">{current.map(x=><article key={x.profile} className={x.row?"configured":"missing"}><div className="gmProfileTop"><small>{source[x.profile]}</small><span>{x.row?"ACTIVE":"MISSING"}</span></div><h2>{names[x.profile]}</h2>{x.row?<><b>{x.row.version}</b><p>Effective {new Date(x.row.effective_from).toLocaleString()}</p></>:<><b>Not configured</b><p>Recruiter calculations for this profile will fail closed until initialized.</p></>}</article>)}</div>
  <section className="panelBox"><small>CONFIGURATION GOVERNANCE</small><div className="adminRows"><div><span>Who can change company assumptions?</span><b>System Admin only</b></div><div><span>Who owns final negotiated rate?</span><b>Recruiter</b></div><div><span>Who approves negative GM?</span><b>Executive only</b></div><div><span>Customer/MSP overrides</span><b>Versioned and effective-dated</b></div><div><span>Historical calculations</span><b>Never recalculated when assumptions change</b></div></div></section>
 </main>
}
