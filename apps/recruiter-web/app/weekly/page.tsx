"use client";

import {useEffect,useMemo,useState} from "react";

function monday(){
 const d=new Date();const diff=(d.getDay()+6)%7;d.setDate(d.getDate()-diff);
 const y=d.getFullYear(),m=String(d.getMonth()+1).padStart(2,"0"),day=String(d.getDate()).padStart(2,"0");
 return `${y}-${m}-${day}`;
}
async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const b=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(b.detail||path+" HTTP "+r.status);
 return b;
}
function metric(target:any,actual:any,goalSet=true){
 if(!goalSet)return {main:"—",sub:"Goal not set"};
 if(Number(target||0)===0)return {main:String(actual??0),sub:"Goal set at 0"};
 const pct=Math.round((Number(actual||0)/Number(target))*100);
 return {main:`${actual??0} / ${target??0}`,sub:`${pct}% of goal`};
}
function statusLabel(v:string){return ({on_track:"On Track",needs_attention:"Needs Attention",at_risk:"At Risk",goal_not_set:"Goal Not Set",goal_set:"Goal Set"} as any)[v]||"Review"}

export default function WeeklyPage(){
 const[me,setMe]=useState<any>(null),[data,setData]=useState<any>(null),[week,setWeek]=useState(monday()),[mode,setMode]=useState<"monday"|"friday">("monday"),[err,setErr]=useState(""),[edit,setEdit]=useState<any>(null),[saved,setSaved]=useState("");
 const managed=me&&me.business_role!=="recruiter";
 async function load(){
  setErr("");setSaved("");
  const who=await api("me");setMe(who);
  if(who.business_role==="recruiter")setData(await api("recruiters/"+who.id+"/weekly-goals?week_start="+week));
  else setData(await api("manager/weekly-review?week_start="+week));
 }
 useEffect(()=>{load().catch(e=>setErr(e.message))},[week]);

 async function saveRecruiter(e:any){
  e.preventDefault();const f=new FormData(e.currentTarget);
  await api("recruiters/"+me.id+"/weekly-goals",{method:"PUT",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({
   week_start:week,submissions_target:Number(f.get("submissions")),interviews_target:Number(f.get("interviews")),closures_target:Number(f.get("closures")),priority_jobs_target:Number(f.get("priority")),notes:String(f.get("notes")||"")||null
  })});setSaved("Monday goals committed. This baseline is now locked.");await load();
 }
 async function saveManager(e:any){
  e.preventDefault();const f=new FormData(e.currentTarget);
  await api("recruiters/"+edit.id+"/weekly-goals",{method:"PUT",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({
   week_start:week,submissions_target:Number(f.get("submissions")),interviews_target:Number(f.get("interviews")),closures_target:Number(f.get("closures")),priority_jobs_target:Number(f.get("priority")),notes:String(f.get("notes")||"")||null
  })});setEdit(null);setSaved("Monday commitment adjusted by manager.");await load();
 }

 const rows=managed?(data?.recruiters||[]):[];const totals=data?.totals||{};
 const recruiter=data||{},t=recruiter.targets||{},a=recruiter.actuals||{};

 async function downloadExcel(){
  const XLSX=await import("xlsx");
  const exportRows=rows.map((r:any)=>({
   "Week Starting":week,
   "Recruiter":r.display_name||r.email,
   "Status":statusLabel(r.delivery_status),
   "Attainment %":r.attainment??"",
   "Submissions Goal":r.goal_set?r.targets.submissions:"",
   "Submissions Actual":r.actuals.submissions??0,
   "Interviews Goal":r.goal_set?r.targets.interviews:"",
   "Interviews Actual":r.actuals.interviews??0,
   "Closures Goal":r.goal_set?r.targets.closures:"",
   "Closures Actual":r.actuals.closures??0,
   "Priority Jobs Goal":r.goal_set?r.targets.priority_jobs:"",
   "Offers":r.actuals.offers??0,
   "Starts":r.actuals.starts??0,
   "Qualified":r.actuals.qualified??0,
   "Responses":r.actuals.responses??0,
   "Monday Focus":r.notes||""
  }));
  const ws=XLSX.utils.json_to_sheet(exportRows);
  ws["!cols"]=[
   {wch:14},{wch:24},{wch:18},{wch:14},{wch:18},{wch:18},{wch:18},{wch:18},
   {wch:16},{wch:16},{wch:18},{wch:12},{wch:10},{wch:12},{wch:12},{wch:42}
  ];
  const wb=XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb,ws,"Friday Status");
  XLSX.writeFile(wb,`Medlivo_Weekly_Status_${week}.xlsx`);
 }
 if(err&&!data)return <main className="page"><div className="adminError"><b>Weekly unavailable</b><span>{err}</span></div></main>;
 if(!me||!data)return <main className="page"><div className="adminLoading">Loading Weekly...</div></main>;

 return <main className="page weeklyAppPage">
  <div className="pageHead"><div><small>Weekly operating rhythm</small><h1>Weekly</h1><p>Monday sets the commitment. Friday reviews delivery against system-generated actuals.</p></div></div>
  {err&&<div className="adminError"><b>Could not save</b><span>{err}</span></div>}
  {saved&&<div className="goodState weeklySave">{saved}</div>}
  <div className="weeklyTopBar">
   <div className="weeklyModeTabs"><button className={mode==="monday"?"active":""} onClick={()=>setMode("monday")}>Monday Goal Meeting</button><button className={mode==="friday"?"active":""} onClick={()=>setMode("friday")}>Friday Status Meeting</button></div>
   <input type="date" value={week} onChange={e=>setWeek(e.target.value)}/>
  </div>

  {managed?<>
   {mode==="monday"?<>
    <section className="weeklySummaryGrid"><article><b>{totals.goals_set??0} / {totals.recruiters??0}</b><span>Goals set</span></article><article><b>{totals.submissions_target??0}</b><span>Submission commitment</span></article><article><b>{totals.interviews_target??0}</b><span>Interview commitment</span></article><article><b>{totals.closures_target??0}</b><span>Closure commitment</span></article><article><b>{totals.priority_jobs_target??0}</b><span>Priority jobs</span></article></section>
    {edit&&<section className="panelBox"><small>MANAGER ADJUSTMENT</small><h3>{edit.display_name||edit.email}</h3><form onSubmit={saveManager} className="weeklyEditForm"><input name="submissions" type="number" min="0" defaultValue={edit.targets.submissions}/><input name="interviews" type="number" min="0" defaultValue={edit.targets.interviews}/><input name="closures" type="number" min="0" defaultValue={edit.targets.closures}/><input name="priority" type="number" min="0" defaultValue={edit.targets.priority_jobs}/><textarea name="notes" defaultValue={edit.notes||""}/><button>Save Manager Adjustment</button></form></section>}
    <div className="weeklyRecruiterGrid">{rows.map((r:any)=><article key={r.id} className="weeklyRecruiterCard"><div><b>{r.display_name||r.email}</b><span>{r.email}</span></div><strong className={"weeklyStatus "+(r.goal_set?"on_track":"goal_not_set")}>{r.goal_set?"Goal Set":"Goal Not Set"}</strong><div className="weeklyCommitments"><span><b>{r.targets.submissions}</b>Submissions</span><span><b>{r.targets.interviews}</b>Interviews</span><span><b>{r.targets.closures}</b>Closures</span><span><b>{r.targets.priority_jobs}</b>Priority Jobs</span></div><p>{r.notes||"No weekly focus recorded."}</p><button onClick={()=>setEdit(r)}>{r.goal_set?"Adjust Goals":"Set Goals"}</button></article>)}</div>
   </>:<>
    <section className="weeklySummaryGrid"><article><b>{totals.submissions_actual??0} / {totals.submissions_target??0}</b><span>Submissions</span></article><article><b>{totals.interviews_actual??0} / {totals.interviews_target??0}</b><span>Interviews</span></article><article><b>{totals.closures_actual??0} / {totals.closures_target??0}</b><span>Closures</span></article><article><b>{totals.offers_actual??0}</b><span>Offers</span></article><article><b>{totals.starts_actual??0}</b><span>Starts</span></article><article><b>{totals.qualified_actual??0}</b><span>Qualified</span></article><article><b>{totals.responses_actual??0}</b><span>Responses</span></article></section>
    <section className="panelBox"><div className="weeklyReportHead"><div><small>MONDAY GOAL VS FRIDAY ACTUAL</small><p className="sectionHelp">Download the Friday meeting report as an Excel workbook for management review or recordkeeping.</p></div><button className="button" type="button" onClick={downloadExcel}>Download Excel (.xlsx)</button></div><table className="adminTable"><thead><tr><th>Recruiter</th><th>Submissions</th><th>Interviews</th><th>Closures</th><th>Offers</th><th>Starts</th><th>Qualified</th><th>Responses</th></tr></thead><tbody>{rows.map((r:any)=>{const s=metric(r.targets.submissions,r.actuals.submissions,r.goal_set),i=metric(r.targets.interviews,r.actuals.interviews,r.goal_set),c=metric(r.targets.closures,r.actuals.closures,r.goal_set);return <tr key={r.id}><td><b>{r.display_name||r.email}</b><span className={"weeklyStatus "+r.delivery_status}>{statusLabel(r.delivery_status)}{r.attainment!=null?" · "+r.attainment+"%":""}</span></td><td><b>{s.main}</b><small>{s.sub}</small></td><td><b>{i.main}</b><small>{i.sub}</small></td><td><b>{c.main}</b><small>{c.sub}</small></td><td>{r.actuals.offers}</td><td>{r.actuals.starts}</td><td>{r.actuals.qualified}</td><td>{r.actuals.responses}</td></tr>})}</tbody></table></section>
   </>}
  </>:<>
   {mode==="monday"?<section className="weeklyRecruiterSelf">
    <div className="panelBox"><small>MONDAY COMMITMENT</small>{recruiter.goal_locked?<div className="weeklyLock"><b>Monday goals are locked</b><span>Your committed baseline is preserved. Ask your Delivery Manager if a correction is needed.</span></div>:<form onSubmit={saveRecruiter} className="weeklyEditForm"><input name="submissions" type="number" min="0" defaultValue={t.submissions}/><input name="interviews" type="number" min="0" defaultValue={t.interviews}/><input name="closures" type="number" min="0" defaultValue={t.closures}/><input name="priority" type="number" min="0" defaultValue={t.priority_jobs}/><textarea name="notes" defaultValue={recruiter.notes||""}/><button>Commit Monday Goals</button></form>}</div>
    <div className="panelBox"><small>PROGRESS SO FAR</small><div className="weeklySummaryGrid">{["submissions","interviews","closures"].map(k=>{const m=metric(t[k],a[k],recruiter.goal_set);return <article key={k}><b>{m.main}</b><span>{k} · {m.sub}</span></article>})}<article><b>{a.starts??0}</b><span>Starts</span></article></div></div>
   </section>:<><section className="weeklySummaryGrid">{["submissions","interviews","closures"].map(k=>{const m=metric(t[k],a[k],recruiter.goal_set);return <article key={k}><b>{m.main}</b><span>{k} · {m.sub}</span></article>})}<article><b>{a.offers??0}</b><span>Offers</span></article><article><b>{a.starts??0}</b><span>Starts</span></article><article><b>{a.qualified??0}</b><span>Qualified</span></article><article><b>{a.responses??0}</b><span>Responses</span></article></section><section className="panelBox"><small>MONDAY FOCUS</small><p>{recruiter.notes||"No weekly focus was recorded."}</p><p className="sectionHelp">Friday actuals are generated from Medlivo and JobDiva activity. Recruiters do not manually enter status numbers.</p></section></>}
  </>}
 </main>;
}
