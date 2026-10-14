"use client";
import {useEffect,useState} from "react";
import RecruiterToday from "../components/RecruiterToday";

async function get(path:string){
  const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});
  const body=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(body.detail||path+" HTTP "+r.status);
  return body;
}
const now=Date.now();
const iso=(hours:number)=>new Date(now+hours*3600000).toISOString();
const date=(days:number)=>new Date(now+days*86400000).toISOString().slice(0,10);

const previewData={
  dash:{
    targets:{submissions:8,interviews:4,closures:2,priority_jobs:5},
    actuals:{submissions:5,interviews:3,closures:1,offers:2,starts:1,qualified:9,responses:14},
    workload:{owned_work_items:7,open_followups:4,overdue_followups:2,active_priority_jobs:5,unreviewed_matches:6}
  },
  priorities:{
    totals:{priority_1_matches:6},
    items:[
      {id:"p1",type:"follow_up",urgency:"overdue",candidate_name:"Jamie Carter",detail:"Candidate replied about Monday availability.",job_id:"preview-job-1"},
      {id:"p2",type:"match_review",urgency:"high",candidate_name:"Taylor Morgan",title:"Physical Therapist · Portland",detail:"Strong evidence-backed match",score:9.2,job_id:"preview-job-1",work_priority:"priority_1"},
      {id:"p3",type:"match_review",urgency:"high",candidate_name:"Avery Lee",title:"Occupational Therapist · Seattle",detail:"License and setting aligned",score:8.8,job_id:"preview-job-2",work_priority:"priority_1"}
    ]
  },
  queue:{
    items:[
      {job_id:"preview-job-1",title:"Physical Therapist",city:"Portland",state:"OR",work_priority:"priority_1",operational:{job_priority:"high"},matches:[{},{},{}]},
      {job_id:"preview-job-2",title:"Occupational Therapist",city:"Seattle",state:"WA",work_priority:"priority_1",operational:{job_priority:"normal"},matches:[{},{}]},
      {job_id:"preview-job-3",title:"Speech-Language Pathologist",city:"Tacoma",state:"WA",work_priority:"priority_2",matches:[{},{}]}
    ]
  },
  protectedActions:{
    items:[
      {id:"pa1",job_id:"preview-job-1",job_title:"Physical Therapist",city:"Portland",state:"OR",assigned_recruiter_name:"Recruiter Preview",is_mine:true,effective_status:"protected",remaining_business_minutes:32},
      {id:"pa2",job_id:"preview-job-4",job_title:"Physical Therapist Assistant",city:"Bellevue",state:"WA",assigned_recruiter_name:"Another Rehab Recruiter",is_mine:false,effective_status:"available_for_support"}
    ]
  },
  funnel:{
    items:[
      {id:"f1",job_id:"preview-job-1",candidate_id:"preview-c1",candidate_name:"Jamie Carter",job_title:"Physical Therapist",interview:{scheduled_at:iso(2),completed_at:null}},
      {id:"f2",job_id:"preview-job-2",candidate_id:"preview-c2",candidate_name:"Taylor Morgan",job_title:"Occupational Therapist",placement:{planned_start_date:date(6),actual_start_date:null},start_readiness:{status:"review",risk_level:"high"}},
      {id:"f3",job_id:"preview-job-3",candidate_id:"preview-c3",candidate_name:"Avery Lee",job_title:"Speech-Language Pathologist",placement:{planned_start_date:date(11),actual_start_date:null},start_readiness:{status:"ready",risk_level:"low"}}
    ]
  }
};

export default function RecruiterPreviewPage(){
  const[me,setMe]=useState<any>(null);
  const[error,setError]=useState("");
  useEffect(()=>{get("me").then(x=>{
    if(!x.system_admin)throw new Error("System Administrator access required");
    setMe({...x,business_role:"recruiter",division:"Rehabilitation",display_name:"Recruiter Preview"});
  }).catch(e=>setError(e.message))},[]);
  if(error)return <main className="page"><div className="adminError"><b>Recruiter preview unavailable</b><span>{error}</span></div></main>;
  if(!me)return <main className="page"><div className="adminLoading">Loading Recruiter UX preview…</div></main>;
  return <RecruiterToday me={me} data={previewData} preview/>;
}
