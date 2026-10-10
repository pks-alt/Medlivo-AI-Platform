"use client";

import { useEffect, useState } from "react";

type Json = any;
const sections=[["overview","Overview"],["jobdiva","JobDiva Data"],["users","Users & Access"],["teams","Teams"],["intake","Job Intake"],["mappings","Mappings"],["approvals","Job Approvals"],["performance","Recruiter Performance"],["quality","Match Quality"],["audit","Audit"]];

async function load(path:string){
  const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});
  if(!r.ok) throw new Error(path+" HTTP "+r.status);
  return r.json();
}

export default function AdminPage(){
  const [data,setData]=useState<Json|null>(null);
  const [error,setError]=useState("");
  const [tab,setTab]=useState("overview");
  const [period,setPeriod]=useState("Today");
  useEffect(()=>{(async()=>{try{
    const [ops,users,teams,audit,overview,batches,mappings,pubs,quality]=await Promise.all([
      load("admin/operations"),load("admin/users"),load("admin/teams"),load("admin/audit?limit=25"),
      load("manager/overview"),load("job-intake/batches?limit=25"),load("job-intake/mappings"),
      load("job-publications?limit=25"),load("manager/match-quality")
    ]);
    setData({ops,users,teams,audit,overview,batches,mappings,pubs,quality});
  }catch(e:any){setError(e?.message||"Admin data could not be loaded");}})()},[]);

  if(error)return <main className="adminShell"><div className="adminError"><b>Admin console unavailable</b><span>{error}</span><p>Sign in with a provisioned Medlivo administrator account and confirm the private team API is reachable.</p></div></main>;
  if(!data)return <main className="adminShell"><div className="adminLoading">Loading Medlivo Admin…</div></main>;

  const o=data.ops||{},canon=o.canonical||{},src=o.source_counts||{},totals=data.overview?.totals||{};
  const latestRuns=o.latest_runs||[];
  const latestFailed=latestRuns.filter((x:any)=>x.status==="failed").length;
  const enrichmentErrors=(src.job_enrichment_errors??0)+(src.candidate_enrichment_errors??0);
  const overdue=totals.overdue_followups??0;
  const platformHealth=latestFailed>0||enrichmentErrors>0?"Needs attention":"Healthy";
  const cards=[
    {label:"Active Jobs",value:canon.open_jobs??0,detail:"Jobs currently open for recruiting",action:"jobdiva"},
    {label:"Weekly Submissions",value:null,detail:"JobDiva submission feed not connected yet",pending:true},
    {label:"Interviews",value:null,detail:"Interview feed not connected yet",pending:true},
    {label:"Placements",value:null,detail:"Placement feed not connected yet",pending:true},
    {label:"Starts",value:null,detail:"Start / placement feed not connected yet",pending:true},
    {label:"Strong Matches 9+",value:canon.strong_matches??0,detail:"High-confidence matches available for review",action:"quality"},
    {label:"Overdue Actions",value:overdue,detail:overdue?String(overdue)+" recruiter actions need follow-up":"No overdue recruiter actions",action:"performance"},
    {label:"Platform Health",value:platformHealth,detail:latestFailed?String(latestFailed)+" JobDiva stream needs attention":enrichmentErrors?String(enrichmentErrors)+" records need data review":"JobDiva and Medlivo data services look healthy",action:"jobdiva"}
  ];

  const briefItems:any[]=[];
  if(latestFailed>0)briefItems.push({level:"critical",title:"Job data needs attention",body:String(latestFailed)+" JobDiva data stream"+(latestFailed===1?" is":"s are")+" not healthy. Existing data remains available.",action:"Review data health",tab:"jobdiva"});
  if(overdue>0)briefItems.push({level:"high",title:"Recruiter follow-up is overdue",body:String(overdue)+" recruiter action"+(overdue===1?" is":"s are")+" overdue and should be reviewed.",action:"Review overdue work",tab:"performance"});
  if(enrichmentErrors>0)briefItems.push({level:"high",title:"Some profiles need data review",body:String(enrichmentErrors)+" JobDiva record"+(enrichmentErrors===1?" has":"s have")+" incomplete enrichment, which can affect matching quality.",action:"Review data issues",tab:"jobdiva"});
  const unclassified=(o.divisions||[]).find((x:any)=>x.division==="Unclassified");
  if((unclassified?.jobs??0)>0)briefItems.push({level:"medium",title:"Some jobs are not classified",body:String(unclassified.jobs)+" job"+(unclassified.jobs===1?" is":"s are")+" missing a Medlivo division and should be reviewed.",action:"Review jobs",tab:"jobdiva"});
  if(!briefItems.length)briefItems.push({level:"good",title:"No immediate operational exceptions",body:"Current JobDiva-backed jobs, matching and recruiter follow-up signals do not show an urgent issue.",action:"View platform health",tab:"jobdiva"});

  return <main className="adminShell">
    <aside className="adminNav">
      <div className="adminBrand"><b>medlivo</b><span>ADMIN</span></div>
      {sections.map(([id,label])=><button key={id} className={tab===id?"active":""} onClick={()=>setTab(id)}>{label}</button>)}
      <a className="adminUtilityLink" href="/executive/margin">Executive GM</a>
      <a className="adminUtilityLink" href="/admin/gm-config">GM Configuration</a>
      <a className="adminUtilityLink" href="/admin/submission-studio">Submission Templates</a>
      <a href="/">Recruiter workspace</a>
    </aside>
    <section className="adminMain">
      <header className="adminHead"><div><small>MEDLIVO AI PLATFORM</small><h1>Administration</h1><p>Operational control, JobDiva visibility, teams, intake, quality and governance.</p></div><span className="readOnly">JOBDIVA READ-ONLY</span></header>

      {tab==="overview" && <>
        <div className="overviewIntro">
          <div><small>EXECUTIVE OVERVIEW</small><h2>What needs your attention today</h2><p>Company-wide recruiting activity and operating health in plain language.</p></div>
          <div className="periodPicker" aria-label="Reporting period">{["Today","7 Days","15 Days","30 Days","Custom"].map(x=><button key={x} className={period===x?"active":""} onClick={()=>setPeriod(x)}>{x}</button>)}</div>
        </div>

        <div className="executiveMetricGrid">{cards.map((card:any)=><button key={card.label} className={"executiveMetricCard"+(card.pending?" pending":"")} onClick={()=>card.action&&setTab(card.action)} disabled={!card.action}>
          <div className="metricTop"><b>{card.label}</b>{card.pending?<span className="dataPending">DATA PENDING</span>:null}</div>
          <strong>{card.pending?"—":card.value}</strong>
          <span>{card.detail}</span>
          {card.action?<em>View details →</em>:<em>Available after JobDiva funnel mapping</em>}
        </button>)}</div>

        <section className="aiBrief">
          <div className="aiBriefHead"><div><small>MEDLIVO AI OPERATIONAL BRIEF</small><h2>Management focus</h2></div><span>Based only on current Medlivo data</span></div>
          <div className="aiBriefQuestionGrid">
            <article><small>WHAT CHANGED?</small><b>{canon.open_jobs??0} active jobs and {canon.strong_matches??0} strong matches are currently visible.</b><p>Weekly submission, interview and placement trends will appear here once those JobDiva feeds are connected.</p></article>
            <article><small>WHAT NEEDS ATTENTION?</small><b>{briefItems[0]?.title}</b><p>{briefItems[0]?.body}</p></article>
            <article><small>WHAT SHOULD MANAGEMENT DO NEXT?</small><b>{briefItems[0]?.action}</b><p>Start with the highest-impact exception, then work down the list below.</p></article>
          </div>
          <div className="attentionList">{briefItems.map((item:any,i:number)=><button key={i} className={"attentionItem "+item.level} onClick={()=>setTab(item.tab)}>
            <span className="attentionLevel">{item.level==="good"?"ALL CLEAR":item.level.toUpperCase()}</span>
            <div><b>{item.title}</b><p>{item.body}</p></div>
            <strong>{item.action} →</strong>
          </button>)}</div>
        </section>

        <div className="adminTwo">
          <Panel title="Division snapshot">{(o.divisions||[]).length?<table className="adminTable"><thead><tr><th>Division</th><th>Jobs</th><th>Open</th></tr></thead><tbody>{o.divisions.map((x:any)=><tr key={x.division}><td>{x.division}</td><td>{x.jobs}</td><td>{x.open_jobs}</td></tr>)}</tbody></table>:<Empty/>}</Panel>
          <Panel title="Data readiness"><Rows rows={[
            ["Jobs available",String(canon.jobs??0)],
            ["Candidates available",String(canon.candidates??0)],
            ["Jobs enriched",String(src.jobs_enriched??0)+" / "+String(src.jobs??0)],
            ["Candidates enriched",String(src.candidates_enriched??0)+" / "+String(src.candidates??0)],
            ["Recruiting funnel","Submissions, interviews, offers and starts pending JobDiva mapping"]
          ]}/></Panel>
        </div>
      </>}

      {tab==="jobdiva" && <>
        <div className="adminMetricGrid">{[
          ["Job records",src.jobs??0,"Landed from JobDiva"],["Candidate records",src.candidates??0,"Landed from JobDiva"],
          ["Jobs enriched",src.jobs_enriched??0,"JobsDetail completed"],["Candidates enriched",src.candidates_enriched??0,"Profile/credentials/resume completed"],
          ["Matches",canon.matches??0,"Persisted match records"],["Excluded",canon.excluded_matches??0,"Hard-gate exclusions"]
        ].map(c=><article key={String(c[0])}><strong>{c[1]}</strong><b>{c[0]}</b><span>{c[2]}</span></article>)}</div>
        <Panel title="Latest sync by stream"><table className="adminTable"><thead><tr><th>Stream</th><th>Status</th><th>Seen</th><th>Upserted</th><th>Started</th></tr></thead><tbody>{(o.latest_runs||[]).map((x:any)=><tr key={x.stream}><td>{x.stream}</td><td><Badge v={x.status}/></td><td>{x.records_seen}</td><td>{x.records_upserted}</td><td>{fmt(x.started_at)}</td></tr>)}</tbody></table></Panel>
        <Panel title="Recent failures">{(o.recent_failures||[]).length?<table className="adminTable"><tbody>{o.recent_failures.map((x:any,i:number)=><tr key={i}><td>{x.stream}</td><td>{x.error_code||"Unknown"}</td><td>{fmt(x.started_at)}</td></tr>)}</tbody></table>:<div className="goodState">No recent JobDiva sync failures.</div>}</Panel>
      </>}

      {tab==="users" && <Panel title="Users & access"><table className="adminTable"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Team</th><th>Google identity</th><th>Status</th></tr></thead><tbody>{(data.users.items||[]).map((x:any)=><tr key={x.id}><td>{x.display_name||"—"}</td><td>{x.email}</td><td>{x.role}</td><td>{x.team_id||"—"}</td><td>{x.identity_bound?"Bound":"Not bound"}</td><td><Badge v={x.is_active?"active":"inactive"}/></td></tr>)}</tbody></table></Panel>}
      {tab==="teams" && <><Panel title="Teams"><table className="adminTable"><thead><tr><th>Team</th><th>Division</th><th>Manager</th></tr></thead><tbody>{(data.teams.items||[]).map((x:any)=><tr key={x.id}><td>{x.name}</td><td>{x.division}</td><td>{x.manager_user_id||"Unassigned"}</td></tr>)}</tbody></table></Panel><Panel title="Recruiter workload"><table className="adminTable"><thead><tr><th>Recruiter</th><th>Work</th><th>Open follow-ups</th><th>Overdue</th></tr></thead><tbody>{(data.overview.recruiters||[]).map((x:any)=><tr key={x.id}><td>{x.display_name}</td><td>{x.work_items}</td><td>{x.open_followups}</td><td>{x.overdue_followups}</td></tr>)}</tbody></table></Panel></>}
      {tab==="intake" && <Panel title="Direct customer job intake"><table className="adminTable"><thead><tr><th>Customer</th><th>Division</th><th>File</th><th>Rows</th><th>Ready</th><th>Review</th><th>Duplicate</th><th>Status</th></tr></thead><tbody>{(data.batches.items||[]).map((x:any)=><tr key={x.id}><td>{x.customer_name}</td><td>{x.division}</td><td>{x.source_filename}</td><td>{x.row_count}</td><td>{x.ready_count}</td><td>{x.review_count}</td><td>{x.duplicate_count}</td><td><Badge v={x.status}/></td></tr>)}</tbody></table></Panel>}
      {tab==="mappings" && <Panel title="Customer mappings">{(data.mappings.items||[]).length?(data.mappings.items||[]).map((x:any)=><div className="mappingCard" key={x.id}><b>{x.customer_name}</b><span>{x.division}</span><pre>{JSON.stringify(x.mapping,null,2)}</pre></div>):<Empty/>}</Panel>}
      {tab==="approvals" && <Panel title="Job approval / publication"><table className="adminTable"><thead><tr><th>Readiness</th><th>Recruiting</th><th>Website</th><th>Updated</th></tr></thead><tbody>{(data.pubs.items||[]).map((x:any)=><tr key={x.id}><td>{x.readiness}</td><td><Badge v={x.recruiting_status}/></td><td><Badge v={x.website_status}/></td><td>{fmt(x.updated_at)}</td></tr>)}</tbody></table></Panel>}
      {tab==="performance" && <Panel title="Recruiter operations"><table className="adminTable"><thead><tr><th>Recruiter</th><th>Work items</th><th>Open</th><th>Overdue</th></tr></thead><tbody>{(data.overview.recruiters||[]).map((x:any)=><tr key={x.id}><td>{x.display_name}</td><td>{x.work_items}</td><td>{x.open_followups}</td><td>{x.overdue_followups}</td></tr>)}</tbody></table></Panel>}
      {tab==="quality" && <Panel title="Match quality"><pre className="jsonBlock">{JSON.stringify(data.quality,null,2)}</pre></Panel>}
      {tab==="audit" && <Panel title="Administrator audit"><table className="adminTable"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th></tr></thead><tbody>{(data.audit.items||[]).map((x:any)=><tr key={x.id}><td>{fmt(x.created_at)}</td><td>{x.actor_display_name}</td><td>{x.action}</td><td>{x.target_display_name||x.target_email}</td></tr>)}</tbody></table></Panel>}
    </section>
  </main>
}

function Panel({title,children}:{title:string,children:any}){return <section className="adminPanel"><h2>{title}</h2>{children}</section>}
function Rows({rows}:{rows:any[]}){return <div className="adminRows">{rows.map((r:any)=><div key={r[0]}><span>{r[0]}</span><b>{r[1]}</b></div>)}</div>}
function Badge({v}:{v:any}){return <span className={"statusBadge "+String(v).toLowerCase().replaceAll(" ","-")}>{String(v)}</span>}
function Empty(){return <div className="emptyState">No records yet.</div>}
function fmt(v:any){if(!v)return "—";try{return new Date(v).toLocaleString()}catch{return String(v)}}
