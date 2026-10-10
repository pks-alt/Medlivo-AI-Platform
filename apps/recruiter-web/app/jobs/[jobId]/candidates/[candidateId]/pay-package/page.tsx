"use client";
import {FormEvent,useEffect,useMemo,useState} from "react";

async function api(path:string,options:RequestInit={}){
 const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin",...options});
 const body=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(body.detail||path+" HTTP "+r.status);
 return body;
}
const n=(v:string)=>v===""?0:Number(v);
const money=(v:any)=>Number(v||0).toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:2});
const pct=(v:any)=>(Number(v||0)*100).toFixed(1)+"%";
const statusLabel=(s:string)=>({
 within_guideline:"Within Guideline",
 discuss_delivery_manager:"Discuss with Delivery Manager",
 discuss_leadership:"Discuss with Leadership",
 negative_gm:"Executive Exception Required",
 policy_unconfigured:"Guideline Not Configured",
}[s]||s.replaceAll("_"," "));

export default function PayPackagePage({params}:{params:Promise<{jobId:string,candidateId:string}>}){
 const[job,setJob]=useState<any>(null),[candidate,setCandidate]=useState<any>(null),[me,setMe]=useState<any>(null);
 const[result,setResult]=useState<any>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 const[ids,setIds]=useState<{jobId:string,candidateId:string}|null>(null);
 const[workerClass,setWorkerClass]=useState("1099");
 useEffect(()=>{params.then(async p=>{setIds(p);const[m,j,c]=await Promise.all([api("me"),api("jobs/"+p.jobId),api("candidates/"+p.candidateId)]);setMe(m);setJob(j);setCandidate(c)}).catch(e=>setError(e.message))},[params]);
 const isLocums=job?.division==="Locum Tenens";
 const title=useMemo(()=>job&&candidate?(candidate.canonical_name||"Candidate")+" · "+(job.title||"Job"):"Pay Package",[job,candidate]);

 async function submit(e:FormEvent<HTMLFormElement>){
  e.preventDefault(); if(!ids||!me)return;
  setBusy(true);setError("");setResult(null);
  const f=new FormData(e.currentTarget);
  const base={job_id:ids.jobId,candidate_id:ids.candidateId,recruiter_user_id:me.id,
   customer_type:String(f.get("customer_type")),contract_type:String(f.get("contract_type")),
   candidate_source:String(f.get("candidate_source"))};
  try{
   let endpoint="",payload:any;
   if(isLocums){
    endpoint="margin/locums-pay-package-snapshots";
    payload={...base,worker_classification:workerClass,assignment_type:String(f.get("assignment_type")),
     planned_per_diem_shifts:n(String(f.get("planned_per_diem_shifts")||"0")),shifts_per_week:n(String(f.get("shifts_per_week"))),
     contract_weeks:n(String(f.get("contract_weeks"))),shift_length_hours:n(String(f.get("shift_length_hours"))),
     client_rate_type:String(f.get("client_rate_type")),client_rate_amount:n(String(f.get("client_rate_amount"))),
     provider_rate_type:String(f.get("provider_rate_type")),provider_rate_amount:n(String(f.get("provider_rate_amount"))),
     client_ot_rate:n(String(f.get("client_ot_rate")||"0"))||null,client_dt_rate:n(String(f.get("client_dt_rate")||"0"))||null,
     callback_included:f.get("callback_included")==="on",callback_hours_per_shift:n(String(f.get("callback_hours_per_shift")||"0")),
     callbacks_per_week:n(String(f.get("callbacks_per_week")||"0")),minimum_guaranteed_hours_per_callback:n(String(f.get("minimum_guaranteed_hours_per_callback")||"0")),
     callback_client_bill_rate:n(String(f.get("callback_client_bill_rate")||"0")),callback_provider_pay_rate:n(String(f.get("callback_provider_pay_rate")||"0")),
     standby_included:f.get("standby_included")==="on",standby_rate_type:"hourly",standby_units_per_shift:n(String(f.get("standby_units_per_shift")||"0")),
     client_standby_bill_rate:n(String(f.get("client_standby_bill_rate")||"0")),provider_standby_pay_rate:n(String(f.get("provider_standby_pay_rate")||"0")),
     compensable_standby_hours_per_week:n(String(f.get("compensable_standby_hours_per_week")||"0")),
     orientation_required:f.get("orientation_required")==="on",orientation_hours_assignment:n(String(f.get("orientation_hours_assignment")||"0")),
     orientation_client_bill_rate:n(String(f.get("orientation_client_bill_rate")||"0")),orientation_provider_pay_rate:n(String(f.get("orientation_provider_pay_rate")||"0")),
     employee_benefits_enabled:f.get("employee_benefits_enabled")==="on",
     housing_daily_cost:n(String(f.get("housing_daily_cost")||"0")),housing_days_per_week:n(String(f.get("housing_days_per_week")||"0")),
     meals_incidentals_daily_cost:n(String(f.get("meals_incidentals_daily_cost")||"0")),meals_incidentals_days_per_week:n(String(f.get("meals_incidentals_days_per_week")||"0")),
     rental_car_weekly_cost:n(String(f.get("rental_car_weekly_cost")||"0")),mileage_reimbursement_rate:n(String(f.get("mileage_reimbursement_rate")||"0")),
     approved_miles_per_week:n(String(f.get("approved_miles_per_week")||"0")),airfare:n(String(f.get("airfare")||"0")),
     state_license:n(String(f.get("state_license")||"0")),dea_registration:n(String(f.get("dea_registration")||"0")),
     sign_on_bonus:n(String(f.get("sign_on_bonus")||"0")),completion_bonus:n(String(f.get("completion_bonus")||"0")),
     other_one_time_travel_cost:0,other_weekly_assignment_cost:0,other_one_time_cost:0};
   }else{
    endpoint="margin/w2-pay-package-snapshots";
    payload={...base,contract_weeks:n(String(f.get("contract_weeks"))),shift_length_hours:n(String(f.get("shift_length_hours"))),
     shifts_per_week:n(String(f.get("shifts_per_week"))),regular_client_bill_rate:n(String(f.get("regular_client_bill_rate"))),
     ot_client_bill_rate:n(String(f.get("ot_client_bill_rate")||"0"))||null,double_time_client_bill_rate:n(String(f.get("double_time_client_bill_rate")||"0"))||null,
     holiday_client_bill_rate:n(String(f.get("holiday_client_bill_rate")||"0"))||null,on_call_client_bill_rate:n(String(f.get("on_call_client_bill_rate")||"0"))||null,
     callback_client_bill_rate:n(String(f.get("callback_client_bill_rate")||"0"))||null,taxable_base_hourly_pay:n(String(f.get("taxable_base_hourly_pay"))),
     housing_stipend_per_hour:n(String(f.get("housing_stipend_per_hour")||"0")),meals_incidentals_stipend_per_hour:n(String(f.get("meals_incidentals_stipend_per_hour")||"0")),
     clinician_holiday_pay_rate:n(String(f.get("clinician_holiday_pay_rate")||"0"))||null,clinician_on_call_pay_rate:n(String(f.get("clinician_on_call_pay_rate")||"0")),
     callback_pay_rate:n(String(f.get("callback_pay_rate")||"0"))||null,additional_expected_ot_hours:n(String(f.get("additional_expected_ot_hours")||"0")),
     holiday_hours:n(String(f.get("holiday_hours")||"0")),on_call_hours:n(String(f.get("on_call_hours")||"0")),callback_hours:n(String(f.get("callback_hours")||"0")),
     orientation_hours:n(String(f.get("orientation_hours")||"0")),national_double_time_hours:n(String(f.get("national_double_time_hours")||"0")),
     national_ot_rule:String(f.get("national_ot_rule")||"standard_ot"),employee_benefits_enabled:f.get("employee_benefits_enabled")==="on",
     assignment_stipend:n(String(f.get("assignment_stipend")||"0")),sign_on_bonus:n(String(f.get("sign_on_bonus")||"0")),
     completion_bonus:n(String(f.get("completion_bonus")||"0")),travel_reimbursement:n(String(f.get("travel_reimbursement")||"0")),
     other_reimbursement:n(String(f.get("other_reimbursement")||"0"))};
   }
   const created=await api(endpoint,{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify(payload)});
   setResult(await api("margin/snapshots/"+created.id));
  }catch(err:any){setError(err.message)}finally{setBusy(false)}
 }

 if(error&&!job)return <main className="page"><div className="adminError"><b>Pay Package unavailable</b><span>{error}</span></div></main>;
 if(!job||!candidate||!me)return <main className="page"><div className="adminLoading">Loading Pay Package…</div></main>;
 if(me.role!=="recruiter")return <main className="page"><div className="adminError"><b>Recruiter access required</b><span>Pay package negotiation is owned by the recruiter.</span></div></main>;

 return <main className="page payPackagePage">
  <div className="pageHead"><div><small>{job.division} · {[job.city,job.state].filter(Boolean).join(", ")||"Location pending"}</small><h1>Pay Package & Margin</h1><p>{title}</p></div><div className="pageActions"><a href={"/jobs/"+ids?.jobId}>Back to Job</a></div></div>
  <div className="payContext"><div><span>Candidate</span><b>{candidate.canonical_name||"Candidate"}</b></div><div><span>Job</span><b>{job.title}</b></div><div><span>Division</span><b>{job.division}</b></div><div><span>Calculator</span><b>{isLocums?(workerClass==="w2"?"CA Locums W-2":"Locums 1099"):(job.division==="Rehabilitation"?"Prachi":"Anand")} · automatic</b></div></div>

  <form className="payLayout" onSubmit={submit}>
   <section className="payForm">
    <div className="paySection"><h2>Assignment</h2><p>Enter the terms you are negotiating. Medlivo selects the correct calculator automatically.</p><div className="fieldGrid">
     <Field name="customer_type" label="Customer Type" select options={[["direct","Direct Customer"],["msp_vms","MSP / VMS"]]}/>
     <Field name="contract_type" label="Contract Type" select options={[["new_contract","New Contract"],["extension","Extension"]]}/>
     <Field name="candidate_source" label="Candidate Source" select options={[["internal_database","Medlivo Database"],["vivian","Vivian"],["referral","Referral"],["job_board","Job Board"],["other","Other"]]}/>
     {isLocums&&<label><span>Worker Classification</span><select value={workerClass} onChange={e=>setWorkerClass(e.target.value)}><option value="1099">1099</option><option value="w2">W-2</option></select></label>}
     {isLocums&&<Field name="assignment_type" label="Assignment Type" select options={[["contract","Contract"],["travel_contract","Travel Contract"],["per_diem","Per Diem"]]}/>}
     {isLocums&&<Field name="planned_per_diem_shifts" label="Planned Per Diem Shifts" type="number"/>}
     <Field name="contract_weeks" label="Contract Weeks" type="number" required defaultValue="13"/>
     <Field name="shift_length_hours" label="Shift Length (Hours)" type="number" required defaultValue={isLocums?"10":"12"}/>
     <Field name="shifts_per_week" label="Shifts / Week" type="number" required defaultValue={isLocums?"2":"3"}/>
    </div></div>

    {isLocums?<>
     <div className="paySection"><h2>Client Billing & Provider Pay</h2><div className="fieldGrid">
      <Field name="client_rate_type" label="Client Rate Type" select options={[["hourly","Hourly"],["per_shift","Per Shift"],["daily","Daily"],["24_hour_call","24-Hour Call"]]}/>
      <Field name="client_rate_amount" label="Client Rate" type="number" required/>
      <Field name="provider_rate_type" label="Provider Rate Type" select options={[["hourly","Hourly"],["per_shift","Per Shift"],["daily","Daily"],["24_hour_call","24-Hour Call"]]}/>
      <Field name="provider_rate_amount" label="Provider Pay" type="number" required/>
      {workerClass==="w2"&&<><Field name="client_ot_rate" label="Client OT Rate" type="number"/><Field name="client_dt_rate" label="Client Double-Time Rate" type="number"/></>}
     </div></div>
     <div className="paySection"><h2>Call, Standby & Orientation</h2><div className="fieldGrid">
      <Check name="callback_included" label="Callback applies"/><Field name="callback_hours_per_shift" label="Callback Hours / Shift" type="number"/><Field name="callbacks_per_week" label="Callbacks / Week" type="number"/><Field name="minimum_guaranteed_hours_per_callback" label="Minimum Hours / Callback" type="number"/><Field name="callback_client_bill_rate" label="Callback Client Rate" type="number"/><Field name="callback_provider_pay_rate" label="Callback Provider Pay" type="number"/>
      <Check name="standby_included" label="Standby applies"/><Field name="standby_units_per_shift" label="Standby Units / Shift" type="number"/><Field name="client_standby_bill_rate" label="Standby Client Rate" type="number"/><Field name="provider_standby_pay_rate" label="Standby Provider Pay" type="number"/><Field name="compensable_standby_hours_per_week" label="Compensable Standby Hours / Week" type="number"/>
      <Check name="orientation_required" label="Orientation required"/><Field name="orientation_hours_assignment" label="Orientation Hours" type="number"/><Field name="orientation_client_bill_rate" label="Orientation Client Rate" type="number"/><Field name="orientation_provider_pay_rate" label="Orientation Provider Pay" type="number"/>
     </div></div>
     <div className="paySection"><h2>Travel & One-Time Costs</h2><div className="fieldGrid"><Field name="housing_daily_cost" label="Housing / Day" type="number"/><Field name="housing_days_per_week" label="Housing Days / Week" type="number"/><Field name="meals_incidentals_daily_cost" label="M&I / Day" type="number"/><Field name="meals_incidentals_days_per_week" label="M&I Days / Week" type="number"/><Field name="rental_car_weekly_cost" label="Rental Car / Week" type="number"/><Field name="mileage_reimbursement_rate" label="Mileage Rate" type="number"/><Field name="approved_miles_per_week" label="Approved Miles / Week" type="number"/><Field name="airfare" label="Airfare" type="number"/><Field name="state_license" label="State License" type="number"/><Field name="dea_registration" label="DEA Registration" type="number"/><Field name="sign_on_bonus" label="Sign-On Bonus" type="number"/><Field name="completion_bonus" label="Completion Bonus" type="number"/></div></div>
    </>:<>
     <div className="paySection"><h2>Client Billing</h2><div className="fieldGrid"><Field name="regular_client_bill_rate" label="Regular Bill Rate" type="number" required/><Field name="ot_client_bill_rate" label="OT Bill Rate" type="number"/><Field name="double_time_client_bill_rate" label="Double-Time Bill Rate" type="number"/><Field name="holiday_client_bill_rate" label="Holiday Bill Rate" type="number"/><Field name="on_call_client_bill_rate" label="On-Call Bill Rate" type="number"/><Field name="callback_client_bill_rate" label="Callback Bill Rate" type="number"/></div></div>
     <div className="paySection"><h2>Clinician Compensation</h2><div className="fieldGrid"><Field name="taxable_base_hourly_pay" label="Taxable Base Pay / Hour" type="number" required/><Field name="housing_stipend_per_hour" label="Housing Stipend / Hour" type="number"/><Field name="meals_incidentals_stipend_per_hour" label="M&I Stipend / Hour" type="number"/><Field name="clinician_holiday_pay_rate" label="Holiday Pay Rate" type="number"/><Field name="clinician_on_call_pay_rate" label="On-Call Pay Rate" type="number"/><Field name="callback_pay_rate" label="Callback Pay Rate" type="number"/></div></div>
     <div className="paySection"><h2>Expected Hours & One-Time Payments</h2><div className="fieldGrid"><Field name="additional_expected_ot_hours" label="Additional Expected OT Hours" type="number"/><Field name="holiday_hours" label="Holiday Hours" type="number"/><Field name="on_call_hours" label="On-Call Hours" type="number"/><Field name="callback_hours" label="Callback Hours" type="number"/><Field name="orientation_hours" label="Orientation Hours" type="number"/>{job.state!=="CA"&&<Field name="national_double_time_hours" label="Expected Double-Time Hours" type="number"/>}{job.state!=="CA"&&<Field name="national_ot_rule" label="Weekly OT Rule" select options={[["standard_ot","Standard OT"],["48_regular_no_ot","48 Regular / No OT"]]}/>}<Field name="assignment_stipend" label="Assignment Stipend" type="number"/><Field name="sign_on_bonus" label="Sign-On Bonus" type="number"/><Field name="completion_bonus" label="Completion Bonus" type="number"/><Field name="travel_reimbursement" label="Travel Reimbursement" type="number"/><Field name="other_reimbursement" label="Other Reimbursement" type="number"/><Check name="employee_benefits_enabled" label="Employer benefits apply"/></div></div>
    </>}
    {error&&<div className="payError">{error}</div>}
    <div className="payActions"><button type="submit" disabled={busy}>{busy?"Calculating…":"Calculate Margin"}</button><span>No spreadsheet calculation required.</span></div>
   </section>

   <aside className="marginPanel">
    <small>MARGIN SNAPSHOT</small>
    {!result?<div className="emptyMargin"><b>Ready to calculate</b><p>Complete the package. Medlivo will apply the correct division calculator, customer rules, costs and margin guideline.</p></div>:<MarginResult data={result} onUpdate={setResult}/>}
   </aside>
  </form>
 </main>
}

function Field({name,label,type="text",required=false,defaultValue="",select=false,options=[]}:{name:string,label:string,type?:string,required?:boolean,defaultValue?:string,select?:boolean,options?:string[][]}){
 return <label><span>{label}</span>{select?<select name={name} defaultValue={options[0]?.[0]}>{options.map(o=><option key={o[0]} value={o[0]}>{o[1]}</option>)}</select>:<input name={name} type={type} step={type==="number"?"0.01":undefined} min={type==="number"?"0":undefined} required={required} defaultValue={defaultValue}/>}</label>
}
function Check({name,label}:{name:string,label:string}){return <label className="checkField"><input name={name} type="checkbox"/><span>{label}</span></label>}
function MarginResult({data,onUpdate}:{data:any,onUpdate:(v:any)=>void}){
 const r=data.result_payload||{},p=r.pay_package||{};
 const[note,setNote]=useState(""),[working,setWorking]=useState(false),[message,setMessage]=useState("");
 const canFinalize=["within_guideline","exception_approved"].includes(data.lifecycle_status)||data.guideline_status==="within_guideline";
 async function refresh(){onUpdate(await api("margin/snapshots/"+data.id))}
 async function discuss(role:"delivery_manager"|"designated_leadership"){
  if(note.trim().length<3){setMessage("Add a short note about the discussion.");return}
  setWorking(true);setMessage("");
  try{
   await api("margin/snapshots/"+data.id+"/discussions",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({
    participant_role:role,
    discussion_type:role==="delivery_manager"?"rate_guidance":"commercial_exception",
    notes:note.trim()
   })});
   setMessage("Discussion recorded.");setNote("");await refresh();
  }catch(e:any){setMessage(e.message)}finally{setWorking(false)}
 }
 async function finalize(){
  setWorking(true);setMessage("");
  try{
   await api("margin/snapshots/"+data.id+"/finalize",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({expected_version:data.version})});
   setMessage("Rate finalized.");await refresh();
  }catch(e:any){setMessage(e.message)}finally{setWorking(false)}
 }
 return <div className="marginResult">
  <div className={"marginStatus "+(data.guideline_status||"")}><span>Margin Status</span><b>{statusLabel(data.guideline_status||"")}</b></div>
  <div className="marginNumbers"><div><span>Net Billing / Week</span><b>{money(r.net_client_billing_per_week)}</b></div><div><span>Total Cost / Week</span><b>{money(r.total_cost_per_week)}</b></div><div><span>GM / Week</span><b>{money(r.gross_margin_per_week)}</b></div><div><span>Gross Margin</span><b>{pct(r.gross_margin_percent)}</b></div><div><span>Full Assignment GM</span><b>{money(r.gross_margin_assignment)}</b></div><div><span>Projected Commission</span><b>{money(data.commission_projection?.projected_amount)}</b></div></div>
  <div className="calculatorNote"><span>Calculator used</span><b>{r.calculator_source||data.calculation_profile}</b><p>Profile and customer economic rules were selected by Medlivo automatically.</p></div>
  {data.lifecycle_status==="finalized"&&<div className="nextStep good"><b>Rate finalized.</b><span>This version is locked as the finalized recruiter package.</span></div>}
  {data.lifecycle_status!=="finalized"&&data.guideline_status==="within_guideline"&&<div className="nextStep good"><b>You can finalize this rate.</b><span>The package is within the configured recruiter guideline.</span></div>}
  {data.guideline_status==="discuss_delivery_manager"&&<div className="nextStep warn"><b>Discuss with Delivery Manager.</b><span>Record the discussion before finalizing. You remain the rate owner.</span></div>}
  {data.guideline_status==="discuss_leadership"&&<div className="nextStep warn"><b>Discuss with leadership.</b><span>Record the discussion before finalizing. You remain the rate owner.</span></div>}
  {data.guideline_status==="negative_gm"&&data.lifecycle_status!=="exception_approved"&&<div className="nextStep danger"><b>Executive exception required.</b><span>This package cannot be finalized until an Executive approves the negative GM exception.</span></div>}
  {data.lifecycle_status==="exception_approved"&&<div className="nextStep good"><b>Executive exception approved.</b><span>You remain the rate owner and may now finalize this package.</span></div>}
  {data.lifecycle_status==="exception_rejected"&&<div className="nextStep danger"><b>Executive exception rejected.</b><span>Revise the package and calculate a new version.</span></div>}
  {(data.guideline_status==="discuss_delivery_manager"||data.guideline_status==="discuss_leadership")&&data.lifecycle_status!=="finalized"&&<div className="discussionBox"><span>Discussion note</span><textarea value={note} onChange={e=>setNote(e.target.value)} placeholder="What was discussed and what guidance was given?"/><button type="button" disabled={working} onClick={()=>discuss(data.guideline_status==="discuss_delivery_manager"?"delivery_manager":"designated_leadership")}>{working?"Saving…":"Record Discussion"}</button></div>}
  {data.lifecycle_status!=="finalized"&&data.lifecycle_status!=="exception_rejected"&&(canFinalize||data.guideline_status==="discuss_delivery_manager"||data.guideline_status==="discuss_leadership")&&<button className="finalizeButton" type="button" disabled={working} onClick={finalize}>{working?"Working…":"Finalize Rate"}</button>}
  {message&&<div className="actionMessage">{message}</div>}
  {p.weekly_clinician_package!=null&&<div className="packageLine"><span>Estimated Weekly Clinician Package</span><b>{money(p.weekly_clinician_package)}</b></div>}
 </div>
}
