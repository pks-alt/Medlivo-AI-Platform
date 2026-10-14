"use client";
import {useEffect,useMemo,useState} from "react";
import {useSearchParams,useRouter} from "next/navigation";

async function getMe(){
  const r=await fetch("/api/team/me",{cache:"no-store",credentials:"same-origin"});
  const b=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(b.detail||"Workspace identity unavailable");
  return b;
}

const sections=[
  ["today","Today"],["jobs","Jobs"],["candidates","Candidates"],["matching","Matching"],
  ["conversations","Conversations"],["interviews","Interviews"],["pay-gm","Pay & GM"],
  ["submissions","Submissions"],["my-week","My Week"]
] as const;

const jobs=[
 {title:"Physical Therapist",location:"Portland, OR",priority:"Priority 1",matches:7,status:"Protected",next:"Review 3 strong matches"},
 {title:"Occupational Therapist",location:"Seattle, WA",priority:"Priority 1",matches:5,status:"Working",next:"Candidate follow-up due"},
 {title:"Speech-Language Pathologist",location:"Tacoma, WA",priority:"Priority 2",matches:4,status:"Division opportunity",next:"Evidence-backed support available"}
];
const candidates=[
 {name:"Jamie Carter",role:"Physical Therapist",state:"OR",score:"9.2",relationship:"Active with you",evidence:"License · care setting · 5 yrs"},
 {name:"Taylor Morgan",role:"Occupational Therapist",state:"WA",score:"8.8",relationship:"No active relationship",evidence:"License · specialty · availability"},
 {name:"Avery Lee",role:"Speech-Language Pathologist",state:"WA",score:"8.5",relationship:"Active with another recruiter",evidence:"License · setting · certification"}
];

function Pill({children}:{children:any}){return <span className="rrPill">{children}</span>}
function Panel({title,kicker,children}:{title:string,kicker?:string,children:any}){return <section className="panelBox rrPanel">{kicker&&<small>{kicker}</small>}<h2>{title}</h2>{children}</section>}

export default function RecruiterReview(){
 const[me,setMe]=useState<any>(null),[error,setError]=useState("");
 const params=useSearchParams(); const router=useRouter();
 const section=params.get("section")||"today";
 useEffect(()=>{getMe().then(x=>{if(!x.system_admin)throw new Error("System Administrator access required");setMe(x)}).catch(e=>setError(e.message))},[]);
 const nav=(id:string)=>router.push("/recruiter-review?section="+id);
 const title=sections.find(x=>x[0]===section)?.[1]||"Today";

 if(error)return <main className="page"><div className="adminError"><b>Recruiter UX review unavailable</b><span>{error}</span></div></main>;
 if(!me)return <main className="page"><div className="adminLoading">Loading full recruiter UX review…</div></main>;

 return <main className="page rrPage">
  <div className="recruiterPreviewBanner"><b>FULL RECRUITER UX REVIEW</b><span>System Admin read-only review of the finalized recruiter experience from PR #115 through Phase 2 PR #120. This surface never sends outreach, changes ownership, or writes to JobDiva.</span></div>
  <div className="rrReviewShell">
   <aside className="rrSidebar">
    <div className="rrBrand"><b>medlivo</b><span>RECRUIT AI</span></div>
    <div className="rrWorkspace"><small>WORKSPACE</small><b>Recruiter Workspace</b><span>Rehabilitation</span></div>
    <nav>{sections.map(([id,label])=><button key={id} onClick={()=>nav(id)} className={section===id?"active":""}>{label}</button>)}</nav>
    <div className="rrFoot"><b>Recruiter Preview</b><span>Read-only System Admin review</span></div>
   </aside>
   <section className="rrCanvas">
    <div className="pageHead"><div><small>Recruiter command center · {title}</small><h1>{title}</h1><p>Finalized recruiter operating model: action first, evidence-backed matching, recruiter-controlled communication, and human approval at every protected action.</p></div><Pill>PR 115 → PR 120</Pill></div>

    {section==="today"&&<>
      <section className="todayWelcome recruiterTodayHero"><small>YOUR DAY</small><h2>What should you work on next?</h2><p>Urgent replies and follow-ups first. Then assigned Priority 1 work, schedule, starts, strong matches, and evidence-backed Priority 2 opportunities.</p></section>
      <div className="todayMetricGrid">
       <article className="attention"><strong>3</strong><b>Needs attention</b><span>Replies, overdue follow-ups and urgent actions</span></article>
       <article><strong>5</strong><b>My Priority 1</b><span>Assigned jobs</span></article>
       <article><strong>6</strong><b>Strong new matches</b><span>Evidence-backed on assigned work</span></article>
       <article><strong>2</strong><b>Upcoming starts</b><span>Next 14 days</span></article>
      </div>
      <div className="rrGrid2">
       <Panel kicker="NEEDS YOUR ATTENTION" title="Handle these before routine queue work">
        <div className="rrList"><article><b>Jamie Carter replied</b><span>Available Monday afternoon · Physical Therapist</span><Pill>Open conversation</Pill></article><article><b>Follow-up overdue</b><span>Taylor Morgan · 1 day overdue</span><Pill>Review</Pill></article></div>
       </Panel>
       <Panel kicker="CONTINUE WHERE YOU LEFT OFF" title="Physical Therapist · Portland"><p>Resume your highest-ranked current work item.</p><Pill>Continue work</Pill></Panel>
      </div>
      <Panel kicker="TIME-SENSITIVE ASSIGNED WORK" title="Protected first-action window">
       <div className="rrCards">{jobs.slice(0,2).map(j=><article key={j.title}><Pill>{j.priority}</Pill><h3>{j.title}</h3><p>{j.location}</p><b>{j.status}</b><span>{j.next}</span></article>)}</div>
      </Panel>
      <Panel kicker="MY PRIORITY 1 WORK" title="Assigned jobs ranked by next action"><div className="rrCards">{jobs.slice(0,2).map(j=><article key={j.title}><h3>{j.title}</h3><p>{j.location}</p><strong>{j.matches}</strong><span>candidate matches</span></article>)}</div></Panel>
      <div className="rrGrid2"><Panel kicker="TODAY'S SCHEDULE" title="Interviews"><div className="rrList"><article><b>10:30 AM · Jamie Carter</b><span>Physical Therapist · Teams</span></article><article><b>2:00 PM · Taylor Morgan</b><span>Occupational Therapist · Client interview</span></article></div></Panel><Panel kicker="UPCOMING STARTS" title="Start readiness"><div className="rrList"><article><b>Taylor Morgan · 6 days</b><span>Credentialing review</span><Pill>HIGH RISK</Pill></article><article><b>Avery Lee · 11 days</b><span>Ready</span><Pill>LOW RISK</Pill></article></div></Panel></div>
    </>}

    {section==="jobs"&&<>
      <Panel kicker="MY JOBS · PRIORITY 1" title="Assigned accountability"><p>Delivery Manager assignment remains the accountability boundary. Recruiters work their assigned jobs first.</p><div className="rrTable">{jobs.slice(0,2).map(j=><article key={j.title}><div><b>{j.title}</b><span>{j.location}</span></div><Pill>{j.status}</Pill><strong>{j.matches} matches</strong><span>{j.next}</span></article>)}</div></Panel>
      <Panel kicker="DIVISION OPPORTUNITIES · PRIORITY 2" title="Evidence-backed opportunities you can help with"><p>Shown only when Medlivo finds eligible same-division candidate opportunities. Primary assignment stays unchanged.</p><div className="rrTable">{jobs.slice(2).map(j=><article key={j.title}><div><b>{j.title}</b><span>{j.location}</span></div><Pill>{j.priority}</Pill><strong>{j.matches} opportunities</strong><span>{j.next}</span></article>)}</div></Panel>
    </>}

    {section==="candidates"&&<>
      <Panel kicker="CANDIDATE 360" title="One trusted candidate identity"><p>Resume, licenses, certifications, availability, rates, compliance readiness, distance, ATS history and relationship continuity.</p><div className="rrCards">{candidates.map(c=><article key={c.name}><h3>{c.name}</h3><p>{c.role} · {c.state}</p><strong>{c.score}</strong><span>match score</span><Pill>{c.relationship}</Pill><small>{c.evidence}</small></article>)}</div></Panel>
      <Panel kicker="RELATIONSHIP CONTINUITY" title="Candidate is company-owned; active recruiter relationship is protected"><p>Meaningful candidate replies establish continuity. Profile views, unanswered outreach and internal notes do not.</p></Panel>
    </>}

    {section==="matching"&&<>
      <Panel kicker="MATCHING WORKBENCH" title="Eligibility before ranking"><p>Hard gates first: license, specialty, care setting, certifications, contract type, availability, distance, rate and compliance readiness. Only eligible candidates are ranked.</p>
       <div className="rrTable">{candidates.map(c=><article key={c.name}><div><b>{c.name}</b><span>{c.role}</span></div><strong>{c.score}/10</strong><span>{c.evidence}</span><Pill>Review evidence</Pill></article>)}</div>
      </Panel>
      <div className="rrGrid2"><Panel kicker="RECRUITER FEEDBACK" title="Strong / Good / Weak / Not a Match"><p>Recruiter feedback becomes quality data for later model tuning and manager visibility.</p></Panel><Panel kicker="EVIDENCE" title="Every qualification keeps its source"><p>Resume, ATS, license, certification, recruiter confirmation or other authoritative evidence remains visible.</p></Panel></div>
    </>}

    {section==="conversations"&&<>
      <Panel kicker="PHASE 2 · PR 116–120" title="Recruiter-controlled Conversations"><p>This is the development that was not visible in the earlier one-page preview.</p>
       <div className="rrFeatureGrid"><article><b>AI-assisted draft</b><span>Email and future SMS copy drafted from candidate + job context.</span></article><article><b>Human approval</b><span>Nothing sends automatically. Recruiter reviews and approves.</span></article><article><b>Gmail pilot</b><span>Recruiter connects their own Medlivo Gmail identity.</span></article><article><b>Reply sync</b><span>Inbound Gmail replies match only to Medlivo-sent candidate threads.</span></article><article><b>3 / 7 / 14 follow-up</b><span>Recruiter can start, pause, resume or stop a sequence.</span></article><article><b>Due preparation worker</b><span>System prepares review-ready drafts; it cannot send them.</span></article></div>
      </Panel>
      <Panel kicker="CURRENT CONVERSATION" title="Jamie Carter · Physical Therapist"><div className="rrConversation"><div className="out"><b>You · Medlivo</b><p>Hi Jamie, I wanted to follow up on the Portland PT opportunity. Would Monday afternoon work for a quick conversation?</p></div><div className="in"><b>Jamie</b><p>Yes, Monday afternoon works for me.</p></div></div><div className="rrComposer"><b>AI draft ready for review</b><span>Reply detected · follow-up sequence automatically stops on meaningful engagement</span><button disabled>Approve & Send Email</button></div></Panel>
    </>}

    {section==="interviews"&&<>
      <Panel kicker="INTERVIEWS" title="Recruiter schedule and next actions"><div className="rrTable"><article><div><b>Jamie Carter</b><span>Physical Therapist</span></div><strong>Today · 10:30 AM</strong><Pill>Confirmed</Pill><span>Teams</span></article><article><div><b>Taylor Morgan</b><span>Occupational Therapist</span></div><strong>Today · 2:00 PM</strong><Pill>Client interview</Pill><span>Hiring manager</span></article></div></Panel>
    </>}

    {section==="pay-gm"&&<>
      <Panel kicker="PAY & GM" title="Recruiter finalizes pay rate with governed margin visibility"><div className="rrFeatureGrid"><article><b>Bill rate</b><strong>$95.00/hr</strong></article><article><b>Candidate pay</b><strong>$56.00/hr</strong></article><article><b>Estimated GM</b><strong>24.6%</strong></article><article><b>Guideline</b><Pill>Within guideline</Pill></article></div><p>Negative GM remains the hard executive approval boundary. Normal recruiter packages follow configured guideline bands.</p></Panel>
    </>}

    {section==="submissions"&&<>
      <Panel kicker="SUBMISSION TO START" title="Recruiting delivery pipeline"><div className="rrPipeline"><span>Submitted <b>8</b></span><span>Interview <b>4</b></span><span>Offer <b>2</b></span><span>Placement <b>2</b></span><span>Started <b>1</b></span><span>At Risk <b>1</b></span></div></Panel>
      <Panel kicker="SUBMISSION STUDIO" title="Evidence-ready candidate package"><p>Assigned recruiter prepares the packet. Readiness gaps remain visible before submission.</p></Panel>
    </>}

    {section==="my-week"&&<>
      <Panel kicker="MONDAY GOAL MEETING" title="Set recruiter commitments"><div className="rrWeek"><article><b>Submissions</b><strong>8</strong></article><article><b>Interviews</b><strong>4</strong></article><article><b>Closures</b><strong>2</strong></article><article><b>Priority Jobs</b><strong>5</strong></article></div></Panel>
      <Panel kicker="FRIDAY STATUS MEETING" title="Actuals come from Medlivo + JobDiva"><div className="rrWeek"><article><b>Submissions</b><strong>5 / 8</strong></article><article><b>Interviews</b><strong>3 / 4</strong></article><article><b>Closures</b><strong>1 / 2</strong></article><article><b>Starts</b><strong>1</strong></article><article><b>Qualified</b><strong>9</strong></article><article><b>Responses</b><strong>14</strong></article></div><p>Recruiters do not manually type Friday actuals.</p></Panel>
    </>}
   </section>
  </div>
 </main>
}
