"use client";
import {FormEvent,useEffect,useState} from "react";

async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const body=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(body.detail||path+" HTTP "+r.status);
 return body;
}
const label=(s:any)=>String(s||"").replaceAll("_"," ");
const fmt=(v:any)=>v?new Date(v).toLocaleString():"—";

export default function FunnelDetail({params}:{params:Promise<{jobId:string,candidateId:string}>}){
 const[ids,setIds]=useState<any>(null),[me,setMe]=useState<any>(null),[job,setJob]=useState<any>(null),[candidate,setCandidate]=useState<any>(null),[data,setData]=useState<any>(null);
 const[error,setError]=useState(""),[busy,setBusy]=useState(false);
 const[status,setStatus]=useState("in_progress"),[risk,setRisk]=useState("unknown"),[riskReason,setRiskReason]=useState(""),[nextAction,setNextAction]=useState(""),[owner,setOwner]=useState(""),[due,setDue]=useState("");
 const[itemKey,setItemKey]=useState(""),[itemLabel,setItemLabel]=useState(""),[itemCategory,setItemCategory]=useState("compliance"),[itemStatus,setItemStatus]=useState("missing"),[itemRequired,setItemRequired]=useState(true),[itemNotes,setItemNotes]=useState("");

 async function refresh(p=ids){
  if(!p)return;
  const[m,j,c,d]=await Promise.all([api("me"),api("jobs/"+p.jobId),api("candidates/"+p.candidateId),api("funnel/"+p.jobId+"/"+p.candidateId)]);
  setMe(m);setJob(j);setCandidate(c);setData(d);
  const r=d.start_readiness;
  if(r){setStatus(r.status);setRisk(r.risk_level);setRiskReason(r.risk_reason||"");setNextAction(r.next_action||"");setOwner(r.owner_user_id||"");setDue(r.due_at?new Date(r.due_at).toISOString().slice(0,16):"");}
 }
 useEffect(()=>{params.then(async p=>{setIds(p);await refresh(p)}).catch(e=>setError(e.message))},[params]);

 async function saveReadiness(e:FormEvent){
  e.preventDefault();if(!ids||!data)return;setBusy(true);setError("");
  try{
   await api("funnel/"+ids.jobId+"/"+ids.candidateId+"/start-readiness",{method:"PUT",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({
    status,risk_level:risk,risk_reason:riskReason.trim()||null,next_action:nextAction.trim()||null,
    owner_user_id:owner||null,due_at:due?new Date(due).toISOString():null,expected_version:data.start_readiness?.version||0
   })});await refresh();
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }

 async function saveItem(e:FormEvent){
  e.preventDefault();if(!ids)return;setBusy(true);setError("");
  try{
   await api("funnel/"+ids.jobId+"/"+ids.candidateId+"/start-readiness/items",{method:"PUT",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({
    item_key:itemKey.trim().toLowerCase().replace(/[^a-z0-9]+/g,"_"),label:itemLabel.trim(),category:itemCategory,status:itemStatus,required:itemRequired,
    source_type:null,source_reference:null,due_at:null,notes:itemNotes.trim()||null
   })});
   setItemKey("");setItemLabel("");setItemNotes("");await refresh();
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }

 if(error&&!data)return <main className="page"><div className="adminError"><b>Start readiness unavailable</b><span>{error}</span></div></main>;
 if(!data||!me||!job||!candidate)return <main className="page"><div className="adminLoading">Loading start readiness…</div></main>;
 const submissions=data.submissions||[],interviews=data.interviews||[],offers=data.offers||[],placements=data.placements||[],items=data.readiness_items||[];
 return <main className="page readinessPage">
  <div className="pageHead"><div><small>Submission to Start</small><h1>{candidate.canonical_name||"Candidate"}</h1><p>{job.title} · {[job.city,job.state].filter(Boolean).join(", ")||"Location pending"}</p></div><div className="pageActions"><a href="/funnel">Funnel</a><a href={"/jobs/"+ids.jobId}>Job</a><a href={"/candidates/"+ids.candidateId}>Candidate</a></div></div>

  <div className="readinessTimeline">
   <Stage title="Submitted" done={submissions.length>0} detail={submissions[0]?.source_status||"No submission"} />
   <Stage title="Interview" done={interviews.length>0} detail={interviews[0]?.source_status||"Not yet"} />
   <Stage title="Offer" done={offers.length>0} detail={offers[0]?.source_status||"Not yet"} />
   <Stage title="Placement" done={placements.length>0} detail={placements[0]?.placement_status||placements[0]?.source_status||"Not yet"} />
   <Stage title="Start" done={!!placements[0]?.actual_start_date||placements[0]?.placement_status==="started"} detail={placements[0]?.actual_start_date||placements[0]?.planned_start_date||"Not yet"} />
  </div>

  {error&&<div className="payError">{error}</div>}

  <div className="readinessGrid">
   <section className="panelBox"><small>START READINESS</small>
    <form className="readinessForm" onSubmit={saveReadiness}>
     <label><span>Status</span><select value={status} onChange={e=>setStatus(e.target.value)}><option value="not_started">Not Started</option><option value="in_progress">In Progress</option><option value="ready">Ready</option><option value="blocked">Blocked</option><option value="started">Started</option></select></label>
     <label><span>Risk Level</span><select value={risk} onChange={e=>setRisk(e.target.value)}><option value="unknown">Unknown</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></label>
     <label><span>Owner User ID</span><input value={owner} onChange={e=>setOwner(e.target.value)} placeholder="Assign responsible owner"/></label>
     <label><span>Due Date</span><input type="datetime-local" value={due} onChange={e=>setDue(e.target.value)}/></label>
     <label className="wide"><span>Risk Reason</span><textarea value={riskReason} onChange={e=>setRiskReason(e.target.value)} placeholder="Required for high or critical risk"/></label>
     <label className="wide"><span>Next Action</span><textarea value={nextAction} onChange={e=>setNextAction(e.target.value)} placeholder="What should happen next?"/></label>
     <div className="readinessSave"><button disabled={busy}>{busy?"Saving…":"Save Start Readiness"}</button><span>Version {data.start_readiness?.version||0}</span></div>
    </form>
   </section>

   <aside className={"panelBox readinessRisk "+(data.start_readiness?.risk_level||"unknown")}><small>RISK & NEXT ACTION</small>
    <strong>{label(data.start_readiness?.risk_level||"unknown")}</strong>
    <b>{data.start_readiness?.status?label(data.start_readiness.status):"Not assessed"}</b>
    <p>{data.start_readiness?.risk_reason||"No risk reason recorded."}</p>
    <div><span>Next action</span><b>{data.start_readiness?.next_action||"Not assigned"}</b></div>
    <div><span>Due</span><b>{fmt(data.start_readiness?.due_at)}</b></div>
   </aside>
  </div>

  <section className="panelBox"><small>READINESS CHECKLIST</small>
   {items.length?<div className="readinessItems">{items.map((x:any)=><article key={x.id} className={"readinessItem "+x.status}><div><b>{x.label}</b><span>{x.category} · {x.required?"Required":"Optional"}</span></div><strong>{label(x.status)}</strong><p>{x.notes||"No notes"}</p></article>)}</div>:<div className="emptyState">No readiness items have been added yet.</div>}
   <form className="readinessItemForm" onSubmit={saveItem}>
    <label><span>Item</span><input value={itemLabel} onChange={e=>{setItemLabel(e.target.value);if(!itemKey)setItemKey(e.target.value)}} placeholder="e.g. Background Check" required/></label>
    <label><span>Category</span><input value={itemCategory} onChange={e=>setItemCategory(e.target.value)} required/></label>
    <label><span>Status</span><select value={itemStatus} onChange={e=>setItemStatus(e.target.value)}><option value="missing">Missing</option><option value="pending">Pending</option><option value="complete">Complete</option><option value="waived">Waived</option><option value="not_applicable">Not Applicable</option></select></label>
    <label className="checkField"><input type="checkbox" checked={itemRequired} onChange={e=>setItemRequired(e.target.checked)}/><span>Required</span></label>
    <label className="wide"><span>Notes</span><input value={itemNotes} onChange={e=>setItemNotes(e.target.value)} placeholder="Optional note"/></label>
    <button disabled={busy}>Add / Update Item</button>
   </form>
  </section>

  <section className="panelBox"><small>JOBDIVA FUNNEL HISTORY · READ ONLY</small><div className="funnelHistoryCols">
   <History title="Submissions" rows={submissions} dateKey="submitted_at"/>
   <History title="Interviews" rows={interviews} dateKey="scheduled_at"/>
   <History title="Offers" rows={offers} dateKey="offered_at"/>
   <History title="Placements" rows={placements} dateKey="planned_start_date"/>
  </div></section>
 </main>
}
function Stage({title,done,detail}:{title:string,done:boolean,detail:string}){return <article className={done?"done":""}><span>{done?"✓":"•"}</span><b>{title}</b><small>{String(detail||"—").replaceAll("_"," ")}</small></article>}
function History({title,rows,dateKey}:{title:string,rows:any[],dateKey:string}){return <div><b>{title}</b>{rows.length?rows.map((x:any,i:number)=><article key={x.id||i}><span>{label(x.source_status||x.placement_status||"")}</span><small>{x[dateKey]?String(x[dateKey]):"—"}</small></article>):<p>None</p>}</div>}
