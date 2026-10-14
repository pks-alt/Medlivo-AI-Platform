"use client";

import { useEffect, useMemo, useState } from "react";

type Json = any;
type NavItem = {id:string,label:string};
type NavGroup = {label:string,items:NavItem[]};

const navGroups:NavGroup[]=[
  {label:"Control Center",items:[{id:"home",label:"Admin Home"}]},
  {label:"People & Organization",items:[{id:"users",label:"Users & Access"},{id:"organization",label:"Organization"}]},
  {label:"Platform Operations",items:[{id:"integrations",label:"Integrations"},{id:"data",label:"Data Operations"}]},
  {label:"Configuration",items:[{id:"recruiting",label:"Recruiting Configuration"},{id:"commercial",label:"Commercial Configuration"},{id:"ai",label:"AI Governance"}]},
  {label:"Governance",items:[{id:"audit",label:"Audit & Security"},{id:"settings",label:"Platform Settings"}]},
];

async function load(path:string){
  const r=await fetch("/api/team/"+path,{cache:"no-store",credentials:"same-origin"});
  const body=await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(body.detail||path+" HTTP "+r.status);
  return body;
}

const titleCase=(value:any)=>String(value||"").replaceAll("_"," ").replace(/\b\w/g,m=>m.toUpperCase());
const roleLabel=(u:any)=>{
  const business=titleCase(u.business_role);
  if(u.system_admin&&u.business_role==="executive")return "Executive + System Admin";
  if(u.system_admin)return business&&business!=="Admin" ? business+" + System Admin" : "System Admin";
  if(business)return business;
  return u.role==="manager"?"Management":titleCase(u.role);
};

export default function AdminPage(){
  const[data,setData]=useState<Json|null>(null);
  const[error,setError]=useState("");
  const[tab,setTab]=useState("home");
  const[search,setSearch]=useState("");
  const[roleFilter,setRoleFilter]=useState("all");
  const[statusFilter,setStatusFilter]=useState("all");

  useEffect(()=>{(async()=>{try{
    const me=await load("me");
    if(!me.system_admin)throw new Error("System Administrator access required");
    const specs=[
      ["ops","admin/operations",{}],["users","admin/users",{items:[]}],["teams","admin/teams",{items:[]}],["audit","admin/audit?limit=50",{items:[]}],
      ["batches","job-intake/batches?limit=25",{items:[]}],["mappings","job-intake/mappings",{items:[]}],["pubs","job-publications?limit=25",{items:[]}]
    ] as const;
    const settled=await Promise.all(specs.map(async([key,path,fallback])=>{try{return {key,value:await load(path),error:""}}catch(e:any){return {key,value:fallback,error:e?.message||"Unavailable"}}}));
    const values:any={me,warnings:[]};
    for(const item of settled){values[item.key]=item.value;if(item.error)values.warnings.push(item.key+": "+item.error)}
    setData(values);
  }catch(e:any){setError(e?.message||"Admin data could not be loaded");}})()},[]);

  const users=data?.users?.items||[];
  const teams=data?.teams?.items||[];
  const userById=useMemo(()=>new Map(users.map((u:any)=>[u.id,u])),[users]);
  const teamById=useMemo(()=>new Map(teams.map((t:any)=>[t.id,t])),[teams]);

  const filteredUsers=useMemo(()=>users.filter((u:any)=>{
    const team:any=teamById.get(u.team_id);
    const hay=[u.display_name,u.email,roleLabel(u),team?.name,team?.division].filter(Boolean).join(" ").toLowerCase();
    if(search.trim()&&!hay.includes(search.trim().toLowerCase()))return false;
    if(roleFilter!=="all"&&String(u.business_role||u.role)!==roleFilter)return false;
    if(statusFilter==="active"&&!u.is_active)return false;
    if(statusFilter==="inactive"&&u.is_active)return false;
    if(statusFilter==="pending"&&u.identity_bound)return false;
    return true;
  }),[users,teamById,search,roleFilter,statusFilter]);

  if(error)return <main className="adminShell"><div className="adminError"><b>Admin console unavailable</b><span>{error}</span><p>Use a provisioned Medlivo System Admin account and confirm the private team API is reachable.</p></div></main>;
  if(!data)return <main className="adminShell"><div className="adminLoading">Loading Medlivo Admin...</div></main>;

  const o=data.ops||{},canon=o.canonical||{},src=o.source_counts||{},latestRuns=o.latest_runs||[];
  const activeUsers=users.filter((u:any)=>u.is_active).length;
  const pendingIdentity=users.filter((u:any)=>u.is_active&&!u.identity_bound).length;
  const inactiveUsers=users.filter((u:any)=>!u.is_active).length;
  const unassignedTeams=teams.filter((t:any)=>!t.manager_user_id).length;
  const latestFailed=latestRuns.filter((x:any)=>x.status==="failed").length;
  const enrichmentErrors=(src.job_enrichment_errors??0)+(src.candidate_enrichment_errors??0);
  const platformHealth=latestFailed||enrichmentErrors?"Needs attention":"Healthy";
  const unclassified=(o.divisions||[]).find((x:any)=>x.division==="Unclassified");
  const unclassifiedJobs=unclassified?.jobs??0;

  const attention:any[]=[];
  if(pendingIdentity)attention.push({level:"medium",title:pendingIdentity+" active user"+(pendingIdentity===1?" is":"s are")+" awaiting Google identity binding",body:"These accounts are provisioned but have not completed a successful first Medlivo sign-in.",action:"Review users",tab:"users"});
  if(unassignedTeams)attention.push({level:"high",title:unassignedTeams+" team"+(unassignedTeams===1?" has":"s have")+" no manager assigned",body:"Assign an accountable manager so the organization structure is complete.",action:"Review organization",tab:"organization"});
  if(latestFailed)attention.push({level:"critical",title:"JobDiva integration needs attention",body:latestFailed+" synchronization stream"+(latestFailed===1?" is":"s are")+" reporting a failed latest run.",action:"Review integrations",tab:"integrations"});
  if(enrichmentErrors)attention.push({level:"high",title:"Some JobDiva records need data review",body:enrichmentErrors+" enrichment error"+(enrichmentErrors===1?" is":"s are")+" affecting job or candidate readiness.",action:"Review data operations",tab:"data"});
  if(unclassifiedJobs)attention.push({level:"medium",title:unclassifiedJobs+" job"+(unclassifiedJobs===1?" is":"s are")+" missing a Medlivo division",body:"Unclassified jobs should be corrected before division-scoped workflows depend on them.",action:"Review data operations",tab:"data"});
  if(!attention.length)attention.push({level:"good",title:"No immediate administration exceptions",body:"Identity, organization, JobDiva integration and data-readiness signals do not show an urgent administration issue.",action:"Review integrations",tab:"integrations"});

  return <main className="adminShell enterpriseAdmin">
    <aside className="adminNav enterpriseAdminNav">
      <div className="adminBrand"><b>medlivo</b><span>SYSTEM ADMIN</span></div>
      {navGroups.map(group=><div className="adminNavGroup" key={group.label}>
        <small>{group.label}</small>
        {group.items.map(item=><button key={item.id} className={tab===item.id?"active":""} onClick={()=>setTab(item.id)}>{item.label}</button>)}
      </div>)}
      <div className="adminNavUtilities">
        <small>Workspaces</small>
        {data.me.business_role==="executive"&&<a href="/">Executive / Today</a>}
        <a href="/manager">Manager</a>
        <a href="/recruiter-review">Recruiter UX Review</a>
        <a href="/jobs">Recruiting Workspace</a>
      </div>
    </aside>

    <section className="adminMain enterpriseAdminMain">
      <header className="adminHead enterpriseAdminHead">
        <div><small>MEDLIVO RECRUIT AI · ENTERPRISE CONTROL</small><h1>{navGroups.flatMap(g=>g.items).find(x=>x.id===tab)?.label||"Administration"}</h1><p>System administration, access, integrations, configuration and governance. Recruiting performance remains in the operating workspaces.</p></div>
        <div className="adminIdentity"><span>Signed in as</span><b>{data.me.display_name||"System Admin"}</b><small>{data.me.business_role==="executive"?"Executive + ":""}System Admin</small></div>
      </header>

      {(data.warnings||[]).length>0&&<div className="adminError"><b>Some administration data is temporarily unavailable</b><span>{data.warnings.join(" · ")}</span><p>The console remains available. Only the affected panels are using empty fallback data.</p></div>}

      {tab==="home"&&<>
        <section className="adminWelcome">
          <div><small>ADMIN CONTROL CENTER</small><h2>Is Medlivo configured and operating correctly?</h2><p>Start here for account readiness, organization coverage, integration health and governed configuration. Daily recruiting KPIs belong in Executive and Manager workspaces.</p></div>
          <span className={"platformState "+(platformHealth==="Healthy"?"healthy":"attention")}>{platformHealth}</span>
        </section>

        <div className="adminControlGrid">
          <button onClick={()=>setTab("users")}><small>IDENTITY & ACCESS</small><strong>{activeUsers}</strong><b>Active users</b><span>{pendingIdentity} awaiting first identity binding · {inactiveUsers} inactive</span></button>
          <button onClick={()=>setTab("organization")}><small>ORGANIZATION</small><strong>{teams.length}</strong><b>Configured teams</b><span>{unassignedTeams?unassignedTeams+" without an assigned manager":"All teams have assigned managers"}</span></button>
          <button onClick={()=>setTab("integrations")}><small>INTEGRATIONS</small><strong>{platformHealth}</strong><b>JobDiva status</b><span>{latestFailed?latestFailed+" failed latest stream":"No latest stream failures detected"}</span></button>
          <button onClick={()=>setTab("data")}><small>DATA READINESS</small><strong>{canon.jobs??0}</strong><b>Canonical jobs</b><span>{enrichmentErrors?enrichmentErrors+" enrichment issues":"Job and candidate enrichment has no reported errors"}</span></button>
        </div>

        <section className="adminAttentionPanel">
          <div className="adminSectionHead"><div><small>ADMINISTRATION ATTENTION</small><h2>What requires an administrator?</h2></div><span>{attention.length} item{attention.length===1?"":"s"}</span></div>
          <div className="attentionList">{attention.map((item:any,i:number)=><button key={i} className={"attentionItem "+item.level} onClick={()=>setTab(item.tab)}>
            <span className="attentionLevel">{item.level==="good"?"ALL CLEAR":item.level.toUpperCase()}</span>
            <div><b>{item.title}</b><p>{item.body}</p></div><strong>{item.action} →</strong>
          </button>)}</div>
        </section>

        <div className="adminTwo">
          <Panel title="Organization coverage">
            {(o.divisions||[]).length?<table className="adminTable"><thead><tr><th>Division</th><th>Jobs</th><th>Open</th></tr></thead><tbody>{o.divisions.map((x:any)=><tr key={x.division}><td>{x.division}</td><td>{x.jobs}</td><td>{x.open_jobs}</td></tr>)}</tbody></table>:<Empty/>}
          </Panel>
          <Panel title="Platform readiness"><Rows rows={[
            ["Google identities bound",String(users.filter((u:any)=>u.identity_bound).length)+" / "+String(users.length)],
            ["Jobs enriched",String(src.jobs_enriched??0)+" / "+String(src.jobs??0)],
            ["Candidates enriched",String(src.candidates_enriched??0)+" / "+String(src.candidates??0)],
            ["Audit records loaded",String(data.audit?.items?.length??0)],
            ["JobDiva mode","Read only"]
          ]}/></Panel>
        </div>
      </>}

      {tab==="users"&&<>
        <section className="adminPageIntro"><div><small>IDENTITY & ACCESS</small><h2>People, roles and effective access</h2><p>Review who can enter Recruit AI, what business role they hold, where they are assigned, and whether Google identity binding is complete.</p></div><div className="adminSummaryPills"><span>{activeUsers} active</span><span>{pendingIdentity} pending first sign-in</span><span>{inactiveUsers} inactive</span></div></section>
        <div className="adminFilters">
          <input aria-label="Search users" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search name, email, role, team or division"/>
          <select aria-label="Filter role" value={roleFilter} onChange={e=>setRoleFilter(e.target.value)}>
            <option value="all">All roles</option><option value="executive">Executive</option><option value="delivery_manager">Delivery Manager</option><option value="recruiter">Recruiter</option><option value="operations">Operations</option><option value="compliance">Compliance</option><option value="read_only">Read Only</option><option value="admin">Legacy Admin</option><option value="manager">Legacy Manager</option>
          </select>
          <select aria-label="Filter status" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}>
            <option value="all">All status</option><option value="active">Active</option><option value="pending">Pending first sign-in</option><option value="inactive">Inactive</option>
          </select>
        </div>
        <Panel title={"Users & Access · "+filteredUsers.length+" shown"}>
          <div className="adminTableWrap"><table className="adminTable enterpriseUserTable"><thead><tr><th>User</th><th>Role</th><th>Scope / Team</th><th>Google identity</th><th>Status</th></tr></thead><tbody>{filteredUsers.map((u:any)=>{
            const team:any=teamById.get(u.team_id);
            const scope=team?[team.division,team.name].filter(Boolean).join(" · "):u.business_role==="executive"?"Company-wide":u.system_admin?"Platform administration":"Not assigned";
            return <tr key={u.id}><td><div className="userIdentity"><b>{u.display_name||"Unnamed user"}</b><span>{u.email}</span></div></td><td><b className="roleText">{roleLabel(u)}</b></td><td><div className="scopeText"><b>{scope}</b>{team?.manager_user_id&&<span>Manager: {(userById.get(team.manager_user_id) as any)?.display_name||"Assigned"}</span>}</div></td><td><Badge v={u.identity_bound?"Bound":"Pending First Sign-In"}/></td><td><Badge v={u.is_active?"Active":"Inactive"}/></td></tr>
          })}</tbody></table></div>
          {!filteredUsers.length&&<Empty text="No users match the selected filters."/>}
          {data.users.truncated&&<div className="adminFootnote">More users exist than this view currently returns. Pagination will be added before production scale.</div>}
        </Panel>
        <div className="adminBoundary"><b>Enterprise access model</b><span>This page now displays the existing business role and System Admin profile. Editing role + scope with effective-access preview is the next implementation step; the current legacy mutation API remains unchanged in this slice.</span></div>
      </>}

      {tab==="organization"&&<>
        <section className="adminPageIntro"><div><small>ORGANIZATION</small><h2>Divisions, teams and accountable managers</h2><p>Phase 1 keeps Delivery Managers and Recruiters isolated to their assigned division. Executive and approved management scope is broader only when explicitly assigned.</p></div></section>
        <div className="organizationGrid">{["Rehabilitation","Nursing & Allied","Locum Tenens"].map(division=>{
          const divisionTeams=teams.filter((t:any)=>t.division===division);
          const divisionUsers=users.filter((u:any)=>divisionTeams.some((t:any)=>t.id===u.team_id));
          return <section className="orgDivisionCard" key={division}><div className="orgDivisionHead"><div><small>DIVISION</small><h2>{division}</h2></div><strong>{divisionUsers.length}</strong></div>
            {divisionTeams.length?divisionTeams.map((team:any)=><article className="orgTeam" key={team.id}><div><b>{team.name}</b><span>Delivery Manager: {team.manager_user_id?(userById.get(team.manager_user_id) as any)?.display_name||"Assigned":"Not assigned"}</span></div><small>{users.filter((u:any)=>u.team_id===team.id&&u.business_role==="recruiter").length} recruiters</small></article>):<div className="emptyState">No team configured for this division.</div>}
          </section>
        })}</div>
        <Panel title="All configured teams"><table className="adminTable"><thead><tr><th>Team</th><th>Division</th><th>Delivery Manager</th><th>Assigned users</th></tr></thead><tbody>{teams.map((team:any)=><tr key={team.id}><td>{team.name}</td><td>{team.division}</td><td>{team.manager_user_id?(userById.get(team.manager_user_id) as any)?.display_name||"Assigned user":"Not assigned"}</td><td>{users.filter((u:any)=>u.team_id===team.id).length}</td></tr>)}</tbody></table></Panel>
      </>}

      {tab==="integrations"&&<>
        <section className="adminPageIntro"><div><small>INTEGRATIONS</small><h2>JobDiva connection and data freshness</h2><p>Business-level health first. Technical stream details remain available below for System Admin troubleshooting.</p></div><span className="readOnly">JOBDIVA · READ ONLY</span></section>
        <div className="adminMetricGrid">{[
          ["Job records",src.jobs??0,"Landed from JobDiva"],["Candidate records",src.candidates??0,"Landed from JobDiva"],
          ["Jobs enriched",src.jobs_enriched??0,"JobsDetail completed"],["Candidates enriched",src.candidates_enriched??0,"Profile, credentials and resume completed"],
          ["Latest stream failures",latestFailed,"Streams requiring administrator review"],["Platform status",platformHealth,"Current integration and enrichment signal"]
        ].map(c=><article key={String(c[0])}><strong>{c[1]}</strong><b>{c[0]}</b><span>{c[2]}</span></article>)}</div>
        <Panel title="Latest synchronization by stream"><table className="adminTable"><thead><tr><th>Stream</th><th>Status</th><th>Records seen</th><th>Updated</th><th>Started</th></tr></thead><tbody>{latestRuns.map((x:any)=><tr key={x.stream}><td>{titleCase(x.stream)}</td><td><Badge v={x.status}/></td><td>{x.records_seen}</td><td>{x.records_upserted}</td><td>{fmt(x.started_at)}</td></tr>)}</tbody></table></Panel>
        <Panel title="Recent failures">{(o.recent_failures||[]).length?<table className="adminTable"><thead><tr><th>Stream</th><th>Issue</th><th>Time</th></tr></thead><tbody>{o.recent_failures.map((x:any,i:number)=><tr key={i}><td>{titleCase(x.stream)}</td><td>{x.error_code||"Synchronization failed"}</td><td>{fmt(x.started_at)}</td></tr>)}</tbody></table>:<div className="goodState">No recent JobDiva synchronization failures.</div>}</Panel>
      </>}

      {tab==="data"&&<>
        <section className="adminPageIntro"><div><small>DATA OPERATIONS</small><h2>Intake, mapping, normalization and approval</h2><p>Incoming recruiting data moves through mapping, review and approval before it becomes dependable operational data.</p></div></section>
        <Panel title="Direct customer job intake"><table className="adminTable"><thead><tr><th>Customer</th><th>Division</th><th>File</th><th>Rows</th><th>Ready</th><th>Review</th><th>Duplicate</th><th>Status</th></tr></thead><tbody>{(data.batches.items||[]).map((x:any)=><tr key={x.id}><td>{x.customer_name}</td><td>{x.division}</td><td>{x.source_filename}</td><td>{x.row_count}</td><td>{x.ready_count}</td><td>{x.review_count}</td><td>{x.duplicate_count}</td><td><Badge v={x.status}/></td></tr>)}</tbody></table></Panel>
        <div className="adminTwo">
          <Panel title="Customer mappings">{(data.mappings.items||[]).length?(data.mappings.items||[]).map((x:any)=><div className="mappingCard" key={x.id}><b>{x.customer_name}</b><span>{x.division}</span><pre>{JSON.stringify(x.mapping,null,2)}</pre></div>):<Empty/>}</Panel>
          <Panel title="Job approval / publication"><table className="adminTable"><thead><tr><th>Readiness</th><th>Recruiting</th><th>Website</th><th>Updated</th></tr></thead><tbody>{(data.pubs.items||[]).map((x:any)=><tr key={x.id}><td>{titleCase(x.readiness)}</td><td><Badge v={x.recruiting_status}/></td><td><Badge v={x.website_status}/></td><td>{fmt(x.updated_at)}</td></tr>)}</tbody></table></Panel>
        </div>
      </>}

      {tab==="recruiting"&&<>
        <section className="adminPageIntro"><div><small>RECRUITING CONFIGURATION</small><h2>Govern how recruiting workflows behave</h2><p>Configuration belongs here; recruiter performance belongs in Manager. Reuse the existing governed workflow services rather than creating parallel rules.</p></div></section>
        <div className="adminConfigCards">
          <a href="/admin/submission-studio"><small>SUBMISSION STUDIO</small><b>Customer & Program Templates</b><span>Manage submission requirements, template versions and document expectations.</span><em>Open configuration →</em></a>
          <button onClick={()=>setTab("data")}><small>JOB READINESS</small><b>Intake & Publication Controls</b><span>Review the existing intake, mapping and recruiting-publication workflow.</span><em>Open data operations →</em></button>
          <a href="/manager"><small>MATCH QUALITY</small><b>Operational measurement</b><span>Match feedback and recruiter performance are intentionally managed outside System Admin.</span><em>Open Manager →</em></a>
        </div>
      </>}

      {tab==="commercial"&&<>
        <section className="adminPageIntro"><div><small>COMMERCIAL CONFIGURATION</small><h2>Economic rules and commercial policy</h2><p>Configure the rules here. Actual business exceptions and executive decisions remain in the Executive GM workflow.</p></div></section>
        <div className="adminConfigCards">
          <a href="/admin/gm-config"><small>GM POLICY</small><b>Gross Margin Configuration</b><span>Customer economics, cost assumptions and guideline configuration.</span><em>Open GM configuration →</em></a>
          <a href="/executive/margin"><small>EXECUTIVE WORKFLOW</small><b>Negative-GM Exceptions</b><span>Separate decision workflow for company-level commercial exceptions.</span><em>Open Executive GM →</em></a>
        </div>
      </>}

      {tab==="ai"&&<>
        <section className="adminPageIntro"><div><small>AI GOVERNANCE</small><h2>Approved AI capabilities and human control</h2><p>AI settings must make autonomous boundaries visible. Unsupported Phase 2 actions remain disabled rather than appearing operational.</p></div></section>
        <div className="aiGovernanceGrid">
          <GovernanceCard name="Candidate Matching" state="Enabled foundation" detail="Explainable matching and hard-gate evidence are available. Recruiting decisions remain human."/>
          <GovernanceCard name="Submission Composer" state={data.me.submission_ai_enabled?"Enabled":"Not enabled"} detail="AI can prepare grounded drafts when configured. Recruiter review and finalization remain required."/>
          <GovernanceCard name="Automated Outreach" state="Phase 2 · Disabled" detail="No autonomous SMS, email or voice outreach is enabled in this Phase 1 Admin module."/>
          <GovernanceCard name="JobDiva Writeback" state="Disabled" detail="Current JobDiva integration remains read-only until controlled writeback is separately approved."/>
        </div>
        <div className="adminBoundary"><b>Governance rule</b><span>System Admin visibility does not authorize an AI capability by itself. Each action type requires explicit product, security and business approval before it can become enabled.</span></div>
      </>}

      {tab==="audit"&&<>
        <section className="adminPageIntro"><div><small>AUDIT & SECURITY</small><h2>Who changed what, and when?</h2><p>Administrative history remains immutable. Sensitive identity subjects and credentials are not exposed in this UI.</p></div></section>
        <Panel title="Administrator audit"><table className="adminTable"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th></tr></thead><tbody>{(data.audit.items||[]).map((x:any)=><tr key={x.id}><td>{fmt(x.created_at)}</td><td>{x.actor_display_name||"System"}</td><td>{titleCase(x.action)}</td><td>{x.target_display_name||x.target_email||"—"}</td></tr>)}</tbody></table></Panel>
      </>}

      {tab==="settings"&&<>
        <section className="adminPageIntro"><div><small>PLATFORM SETTINGS</small><h2>Enterprise administration boundaries</h2><p>Only settings with a safe, governed backend belong here. Infrastructure secrets and credentials are never exposed through normal Admin screens.</p></div></section>
        <Panel title="Phase 1 platform policy"><Rows rows={[
          ["Canonical codebase","Single Medlivo Recruit AI repository"],
          ["Access model","Role + scope"],
          ["Division rule","Delivery Managers and Recruiters remain division-specific"],
          ["JobDiva","Read only"],
          ["Autonomous outreach","Disabled in Phase 1"],
          ["Deployment","PR, CI, guarded staging promotion"]
        ]}/></Panel>
        <div className="adminBoundary"><b>No shadow configuration</b><span>Platform settings will extend the existing RBAC, audit, migration and deployment foundations. We will not create a second permission system or parallel Admin backend.</span></div>
      </>}
    </section>
  </main>
}

function Panel({title,children}:{title:string,children:any}){return <section className="adminPanel"><h2>{title}</h2>{children}</section>}
function Rows({rows}:{rows:any[]}){return <div className="adminRows">{rows.map((r:any)=><div key={r[0]}><span>{r[0]}</span><b>{r[1]}</b></div>)}</div>}
function Badge({v}:{v:any}){return <span className={"statusBadge "+String(v).toLowerCase().replaceAll(" ","-")}>{String(v)}</span>}
function Empty({text="No records yet."}:{text?:string}){return <div className="emptyState">{text}</div>}
function fmt(v:any){if(!v)return "—";try{return new Date(v).toLocaleString()}catch{return String(v)}}
function GovernanceCard({name,state,detail}:{name:string,state:string,detail:string}){return <article><div><small>AI CAPABILITY</small><b>{name}</b></div><strong>{state}</strong><p>{detail}</p></article>}
