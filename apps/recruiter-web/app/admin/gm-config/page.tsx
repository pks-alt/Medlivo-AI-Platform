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
 const[me,setMe]=useState<any>(null),[rows,setRows]=useState<any[]>([]),[customers,setCustomers]=useState<any[]>([]),[rules,setRules]=useState<any[]>([]),[error,setError]=useState(""),[working,setWorking]=useState(false),[message,setMessage]=useState("");
 async function refresh(){
  const m=await api("me");setMe(m);
  const profiles=Object.keys(names);
  const [groups,cs,rs]=await Promise.all([
   Promise.all(profiles.map(async p=>{const x=await api("economic-config/assumptions?profile="+p+"&limit=10");return (x.items||[]).map((r:any)=>({...r,profile:p}))})),
   api("economic-config/customers?limit=500"),
   api("economic-config/customer-rules?limit=500")
  ]);
  setRows(groups.flat());setCustomers(cs.items||[]);setRules(rs.items||[]);
 }
 useEffect(()=>{refresh().catch(e=>setError(e.message))},[]);

 async function saveCustomerRule(e:any){
  e.preventDefault();setWorking(true);setError("");setMessage("");
  const f=new FormData(e.currentTarget);
  const rule_payload:any={};
  [["msp_fee_rate","msp_fee_rate"],["professional_liability_rate","professional_liability_rate"],["factoring_rate","factoring_rate"],["overhead_rate","overhead_rate"]].forEach(([field,key])=>{
   const raw=String(f.get(field)||"").trim();
   if(raw!=="")rule_payload[key]=Number(raw)/100;
  });
  if(!Object.keys(rule_payload).length){setWorking(false);setError("Enter at least one customer economic override.");return}
  try{
   const stamp=new Date().toISOString().replace(/[-:.TZ]/g,"").slice(0,14);
   await api("economic-config/customers",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({
    customer_id:String(f.get("customer_id")),
    calculation_profile:String(f.get("calculation_profile")),
    version:"customer-"+stamp,
    rule_payload,
    effective_from:new Date().toISOString()
   })});
   setMessage("Customer economic rule saved as a new effective-dated version.");
   e.currentTarget.reset();await refresh();
  }catch(e:any){setError(e.message)}finally{setWorking(false)}
 }
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
  <section className="panelBox customerEconomics"><small>CUSTOMER / MSP ECONOMIC OVERRIDES</small><p className="sectionHelp">Use this only when a customer or MSP has an approved economic rule that differs from the company profile. Values are percentages and become a new effective-dated version.</p>{customers.length?<form className="customerRuleForm" onSubmit={saveCustomerRule}><label><span>Customer</span><select name="customer_id" required>{customers.map((x:any)=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label><span>Calculator Profile</span><select name="calculation_profile" required>{Object.keys(names).map(p=><option key={p} value={p}>{names[p]}</option>)}</select></label><label><span>MSP / VMS Fee %</span><input name="msp_fee_rate" type="number" step="0.01" min="0" max="100"/></label><label><span>Professional Liability %</span><input name="professional_liability_rate" type="number" step="0.01" min="0" max="100"/></label><label><span>Factoring %</span><input name="factoring_rate" type="number" step="0.01" min="0" max="100"/></label><label><span>Overhead %</span><input name="overhead_rate" type="number" step="0.01" min="0" max="100"/></label><button disabled={working}>{working?"Saving…":"Save New Rule Version"}</button></form>:<div className="emptyState">Customer master records will appear here when available.</div>}
   {rules.length?<table className="adminTable"><thead><tr><th>Customer</th><th>Profile</th><th>Version</th><th>MSP Fee</th><th>Effective</th><th>Status</th></tr></thead><tbody>{rules.slice(0,50).map((x:any)=><tr key={x.id}><td>{x.customer_name}</td><td>{names[x.calculation_profile]||x.calculation_profile}</td><td>{x.version}</td><td>{x.rule_payload?.msp_fee_rate!=null?(Number(x.rule_payload.msp_fee_rate)*100).toFixed(2)+"%":"Profile default"}</td><td>{new Date(x.effective_from).toLocaleString()}</td><td>{x.status}</td></tr>)}</tbody></table>:null}</section>
  <section className="panelBox"><small>CONFIGURATION GOVERNANCE</small><div className="adminRows"><div><span>Who can change company assumptions?</span><b>System Admin only</b></div><div><span>Who owns final negotiated rate?</span><b>Recruiter</b></div><div><span>Who approves negative GM?</span><b>Executive only</b></div><div><span>Customer/MSP overrides</span><b>Versioned and effective-dated</b></div><div><span>Historical calculations</span><b>Never recalculated when assumptions change</b></div></div></section>
 </main>
}
