"use client";
import {FormEvent,useEffect,useMemo,useState} from "react";

async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const body=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(body.detail||path+" HTTP "+r.status);
 return body;
}
const common:any[]=[
 {key:"resume",label:"Resume / CV",type:"document",category:"resume",strategy:"source_or_ai"},
 {key:"active_license",label:"Active License Verification",type:"document",category:"licensure",strategy:"source_only"},
 {key:"skills_checklist",label:"Specialty Skills Checklist",type:"skills_checklist",category:"skills",strategy:"source_only"},
 {key:"candidate_summary",label:"Candidate / Provider Presentation",type:"derived",category:"presentation",strategy:"source_or_ai"},
 {key:"professional_references",label:"Professional References",type:"reference",category:"references",strategy:"source_only"},
 {key:"board_certification_verification",label:"Board Certification Verification",type:"document",category:"board_certification",strategy:"source_only"},
 {key:"dea_registration",label:"DEA Registration",type:"document",category:"dea",strategy:"source_only"},
 {key:"npi",label:"NPI",type:"field",category:"identity",strategy:"source_only"},
 {key:"sex_offender_search",label:"Sex Offender Search",type:"document",category:"background",strategy:"source_only",sensitivity:"confidential"},
 {key:"covid_documentation",label:"Vaccination / Exemption Evidence",type:"document",category:"health_document",strategy:"source_only",sensitivity:"confidential"},
 {key:"availability",label:"Availability / Schedule Confirmation",type:"field",category:"availability",strategy:"manual_confirmation"},
 {key:"commercial_terms",label:"Bill Rate / OT / Travel Terms",type:"derived",category:"commercial",strategy:"derived",sensitivity:"internal"},
];
const defaultKeys:any={
 "Rehabilitation":["resume","active_license","candidate_summary"],
 "Nursing & Allied":["resume","active_license","skills_checklist","candidate_summary"],
 "Locum Tenens":["resume","active_license","candidate_summary","availability","board_certification_verification","dea_registration","npi"]
};

export default function SubmissionStudioAdmin(){
 const[me,setMe]=useState<any>(null),[templates,setTemplates]=useState<any[]>([]),[customers,setCustomers]=useState<any[]>([]);
 const[division,setDivision]=useState("Rehabilitation"),[customer,setCustomer]=useState(""),[program,setProgram]=useState("");
 const[profession,setProfession]=useState(""),[specialty,setSpecialty]=useState(""),[name,setName]=useState("");
 const[selected,setSelected]=useState<string[]>(defaultKeys["Rehabilitation"]),[error,setError]=useState(""),[message,setMessage]=useState(""),[busy,setBusy]=useState(false);
 async function refresh(){
  const[m,t,c]=await Promise.all([api("me"),api("submission-studio/templates?limit=500"),api("economic-config/customers?limit=500")]);
  setMe(m);setTemplates(t.items||[]);setCustomers(c.items||[]);
 }
 useEffect(()=>{refresh().catch(e=>setError(e.message))},[]);
 useEffect(()=>{setSelected(defaultKeys[division]||[])},[division]);
 const parents=useMemo(()=>templates.filter((x:any)=>x.division===division&&x.status==="active"),[templates,division]);

 async function bootstrap(){
  setBusy(true);setError("");setMessage("");
  try{
   const r=await api("submission-studio/bootstrap-templates",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({activate:true})});
   setMessage(r.created.length?String(r.created.length)+" Medlivo division defaults initialized.":"Division defaults are already configured.");
   await refresh();
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }

 async function create(e:FormEvent){
  e.preventDefault();setBusy(true);setError("");setMessage("");
  try{
   const parent=parents.find((x:any)=>x.template_scope==="division_default")||parents[0];
   const requirements=common.filter(x=>selected.includes(x.key)).map((x,i)=>({
    requirement_key:x.key,label:x.label,requirement_type:x.type,category:x.category,lifecycle_stage:"submission",
    sensitivity:x.sensitivity||"standard",fulfillment_strategy:x.strategy,required:true,source_preference:[],
    validation_rule:x.key==="professional_references"?{min_count:2}:{},output_rule:{},display_order:i+1
   }));
   const scope=program.trim()?"program":customer?"customer":"division_default";
   await api("submission-studio/templates",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({
    name:name.trim()||([customer,program,division].filter(Boolean).join(" · ")+" Submission"),
    division,customer_id:customer||null,program_name:program.trim()||null,profession:profession.trim()||null,specialty:specialty.trim()||null,
    template_scope:scope,parent_template_id:parent?.id||null,activate:true,
    resume_format_profile:{style:"medlivo_standard",job_relevant_ordering:true,remove_drafting_artifacts:true,invent_facts:false},
    output_profile:{combined_pdf:true,separate_documents:true,preview_required:true},
    ai_policy:{resume_restructure:true,candidate_summary:true,conflict_detection:true,source_grounding_required:true,model_required_for_narrative:true},
    requirements
   })});
   setMessage("Submission template created as a new active version.");setName("");setProgram("");setProfession("");setSpecialty("");await refresh();
  }catch(e:any){setError(e.message)}finally{setBusy(false)}
 }

 if(error&&!me)return <main className="page"><div className="adminError"><b>Submission Studio configuration unavailable</b><span>{error}</span></div></main>;
 if(!me)return <main className="page"><div className="adminLoading">Loading Submission Studio configuration…</div></main>;
 if(!me.system_admin)return <main className="page"><div className="adminError"><b>System Admin access required</b><span>Submission templates are governed configuration.</span></div></main>;

 return <main className="page submissionAdminPage">
  <div className="pageHead"><div><small>System Administration · Submission Studio</small><h1>Submission Templates</h1><p>Create customer and MSP/VMS program templates without changing code.</p></div><div className="pageActions"><a href="/admin">Admin</a><a href="/">Workspace</a></div></div>
  <section className="submissionAdminIntro"><div><b>Start with Medlivo defaults</b><p>These become the safe base layer. Customer/program templates inherit from them and add only what is different.</p></div><button onClick={bootstrap} disabled={busy}>{busy?"Working…":"Initialize Division Defaults"}</button></section>
  {message&&<div className="goodState">{message}</div>}{error&&<div className="payError">{error}</div>}

  <section className="panelBox"><small>CREATE CUSTOMER / PROGRAM TEMPLATE</small>
   <form className="templateBuilder" onSubmit={create}>
    <label><span>Division</span><select value={division} onChange={e=>setDivision(e.target.value)}><option>Rehabilitation</option><option>Nursing & Allied</option><option>Locum Tenens</option></select></label>
    <label><span>Customer / MSP</span><select value={customer} onChange={e=>setCustomer(e.target.value)}><option value="">Division default</option>{customers.map((x:any)=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
    <label><span>Program (optional)</span><input value={program} onChange={e=>setProgram(e.target.value)} placeholder="e.g. Kaiser"/></label>
    <label><span>Profession (optional)</span><input value={profession} onChange={e=>setProfession(e.target.value)} placeholder="RN, PT, NP…"/></label>
    <label><span>Specialty (optional)</span><input value={specialty} onChange={e=>setSpecialty(e.target.value)} placeholder="ICU, CVOR, Hospitalist…"/></label>
    <label><span>Template Name</span><input value={name} onChange={e=>setName(e.target.value)} placeholder="Optional custom name"/></label>
    <fieldset><legend>Submission requirements</legend><div className="templateRequirementGrid">{common.map(x=><label key={x.key} className="templateCheck"><input type="checkbox" checked={selected.includes(x.key)} onChange={e=>setSelected(e.target.checked?[...selected,x.key]:selected.filter(k=>k!==x.key))}/><span><b>{x.label}</b><small>{String(x.category).replaceAll("_"," ")}</small></span></label>)}</div></fieldset>
    <div className="templateBuilderFoot"><span>{selected.length} requirements selected · versioning is automatic</span><button disabled={busy||!selected.length}>{busy?"Saving…":"Create Active Template"}</button></div>
   </form>
  </section>

  <section className="panelBox"><small>ACTIVE & HISTORICAL TEMPLATES</small>{templates.length?<table className="adminTable"><thead><tr><th>Division</th><th>Template</th><th>Customer / Program</th><th>Scope</th><th>Version</th><th>Requirements</th><th>Status</th></tr></thead><tbody>{templates.map((x:any)=><tr key={x.id}><td>{x.division}</td><td>{x.name}</td><td>{[x.customer_name,x.program_name].filter(Boolean).join(" · ")||"Medlivo default"}</td><td>{String(x.template_scope).replaceAll("_"," ")}</td><td>v{x.version}</td><td>{x.requirement_count}</td><td>{x.status}</td></tr>)}</tbody></table>:<div className="emptyState">No submission templates configured yet.</div>}</section>
 </main>
}
