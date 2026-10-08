import {createHash} from 'node:crypto';
import {securityHeaders} from './core.mjs';
const CSS = `
:root{--navy:#102641;--ink:#172d42;--muted:#65798d;--line:#dfe7ed;--lime:#a8df74;--bg:#f4f7f9;--teal:#21616b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font:14px/1.55 Inter,system-ui,-apple-system,'Segoe UI',sans-serif;color:var(--ink)}
button,input,select,textarea{font:inherit}button,a{touch-action:manipulation}button{cursor:pointer}button:disabled{cursor:wait;opacity:.55}a{color:var(--teal)}
a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid #76a9cd;outline-offset:3px}
[hidden]{display:none!important}h1,h2,h3,p{margin-top:0}h1,h2,h3{line-height:1.2}h1{font-size:28px;letter-spacing:-.8px}h2{font-size:23px;letter-spacing:-.5px}h3{font-size:16px}
.eyebrow{font-size:10px;letter-spacing:.13em;text-transform:uppercase;font-weight:700;color:var(--muted);margin-bottom:8px}.muted{color:var(--muted)}.small{font-size:12px}.skip{position:absolute;left:10px;top:-80px;z-index:10;background:#fff;padding:10px}.skip:focus{top:10px}
.login-layout{min-height:100vh;display:grid;grid-template-columns:1.05fr 1fr}.login-story{background:var(--navy);color:#fff;padding:54px 64px;display:flex;flex-direction:column;justify-content:space-between}.brand{font-size:34px;letter-spacing:-1.3px;font-weight:750}.brand small{display:block;font-size:10px;letter-spacing:.24em;color:#b7d79e;margin-top:2px}.login-story h1{font-size:48px;letter-spacing:-1.8px;line-height:1.12;max-width:480px;margin:30px 0 24px}.login-story p{color:#b9cbdc;max-width:420px;font-size:16px;line-height:1.8}.story-foot{font-size:11px;color:#92acc2;letter-spacing:.06em}.login-form{display:flex;align-items:center;justify-content:center;padding:45px}.login-card{width:100%;max-width:410px}.login-card h2{font-size:32px}.login-card>p{color:var(--muted);line-height:1.8;margin-bottom:26px}.button{border-radius:7px;border:1px solid var(--line);padding:10px 16px;background:white;color:var(--ink);font-size:13px;font-weight:650;text-decoration:none;display:inline-flex;justify-content:center;align-items:center;gap:10px}.button.primary{background:var(--navy);border-color:var(--navy);color:white}.button.lime{background:var(--lime);color:#214022;border-color:var(--lime)}.button.full{width:100%;padding:14px}.google-letter{font-weight:800;font-size:18px}.login-detail{margin-top:28px;padding-top:22px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);line-height:1.8}.notice{padding:12px 15px;border:1px solid #e7d7b3;background:#fff8eb;border-radius:8px;font-size:13px;margin:0 0 18px}.notice.error{border-color:#edc5c5;background:#fff2f2;color:#8a3333}.notice.success{border-color:#c9dfbb;background:#f1f8ec;color:#365c26}.pill{font-size:10px;letter-spacing:.06em;font-weight:700;padding:5px 8px;border-radius:5px;background:#ecf4e6;color:#436238}
.workspace{display:grid;grid-template-columns:216px minmax(0,1fr);min-height:100vh}.sidebar{background:var(--navy);color:white;padding:28px 18px;display:flex;flex-direction:column;position:sticky;top:0;height:100vh}.sidebar .brand{font-size:28px;margin:0 8px 44px}.sidebar .brand small{font-size:9px}.nav-label{font-size:9px;letter-spacing:.15em;color:#819ab0;margin:0 12px 13px}.nav-item{border:0;background:none;color:#bdcddd;text-align:left;padding:12px 13px;font-size:13px;border-radius:7px;width:100%;margin-bottom:5px}.nav-item.active{background:#ffffff12;color:#fff;border-left:3px solid var(--lime)}.sidebar-footer{margin-top:auto;font-size:11px;color:#92acc2;border-top:1px solid #ffffff18;padding:20px 8px 0}.status-line{display:flex;gap:8px;align-items:center}.status-dot{width:6px;height:6px;border-radius:50%;background:var(--lime)}.main-shell{min-width:0}.topbar{background:#f9fbfc;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:20px;padding:22px 32px}.topbar h1{font-size:24px;margin:3px 0 0}.topbar .eyebrow{margin:0}.account{display:flex;align-items:center;gap:20px}.account-name{display:block;font-size:12px;font-weight:700}.account-role{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.signout{border:1px solid var(--line);background:white;border-radius:6px;padding:8px 12px;color:var(--ink);font-size:11px}.content{padding:28px 32px;outline:0}.hero{background:var(--navy);border-radius:13px;padding:27px 30px;color:white;display:flex;justify-content:space-between;gap:30px;align-items:center}.hero h2{margin-bottom:11px;font-size:29px}.hero .eyebrow{color:#b9d3a6}.hero p{color:#aec4d7;font-size:13px;max-width:600px;margin:0}.hero-number{text-align:center;min-width:120px;border-left:1px solid #ffffff20;padding-left:27px}.hero-number b{font-size:38px;font-weight:600;display:block}.hero-number small{color:#aec4d7;font-size:10px}.section-title{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:27px 0 16px}.section-title h2{font-size:20px;margin:0}.work-layout{display:grid;grid-template-columns:minmax(230px,290px) minmax(0,1fr);gap:18px}.panel{background:white;border:1px solid var(--line);border-radius:11px;padding:21px;min-width:0}.work-list{display:grid;gap:8px;align-content:start}.case-card{display:block;text-align:left;background:white;border:1px solid var(--line);border-radius:9px;padding:16px;width:100%;color:var(--ink)}.case-card.active{border-color:#88aabe;background:#eef5f8;box-shadow:inset 3px 0 #21616b}.case-card strong{display:block;font-size:13px;margin-bottom:5px}.case-card small{display:block;color:var(--muted);font-size:10px}.detail-heading{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}.detail-heading h2{font-size:22px;margin:5px 0 9px}.tabs{display:flex;gap:18px;border-bottom:1px solid var(--line);margin:24px 0 20px;overflow-x:auto}.tab{background:transparent;border:0;border-bottom:2px solid transparent;padding:0 0 12px;font-weight:600;color:var(--muted);font-size:12px;white-space:nowrap}.tab.active{color:var(--teal);border-color:var(--teal)}label{display:block;font-size:12px;font-weight:650;margin:12px 0 6px}textarea,input,select{border:1px solid #cfdbe4;border-radius:7px;padding:10px 12px;background:white;width:100%;color:var(--ink)}textarea{resize:vertical;min-height:96px;font-size:13px}input,select{font-size:13px}.form-footer{display:flex;justify-content:space-between;align-items:center;gap:14px;margin-top:12px}.form-footer small{color:var(--muted);font-size:11px}.section-rule{border:0;border-top:1px solid var(--line);margin:25px 0}.entry{padding:15px 0;border-top:1px solid #e8eef2}.entry:first-child{border-top:0}.entry p{font-size:13px;margin:0 0 7px;white-space:pre-wrap;overflow-wrap:anywhere}.entry-meta{font-size:10px;color:var(--muted);display:flex;justify-content:space-between;gap:10px}.entry strong{font-size:12px}.task-row{display:flex;justify-content:space-between;align-items:center;gap:14px}.task-row p{margin-top:5px;color:var(--muted);font-size:11px}.task-row.done strong{text-decoration:line-through;color:var(--muted)}.grid-two{display:grid;grid-template-columns:1fr 1fr;gap:16px}.empty{padding:25px 5px;color:var(--muted);font-size:13px;line-height:1.8}.footer{font-size:10px;color:#8193a2;display:flex;justify-content:space-between;gap:15px;margin-top:26px}.audit-badge{font-size:10px;background:#eef4f8;border-radius:5px;padding:3px 6px;color:#456982;display:inline-block;margin-bottom:5px}.loading{padding:36px;color:var(--muted)}.danger-text{color:#8a3333}.pager{margin-top:15px}.status-message:empty{display:none}.admin-grid{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(300px,.75fr);gap:18px}.admin-table-wrap{overflow:auto}.admin-table{width:100%;border-collapse:collapse}.admin-table th,.admin-table td{text-align:left;border-bottom:1px solid var(--line);padding:11px 9px;font-size:12px;vertical-align:top}.admin-table th{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);background:#f8fafb}.admin-table td small{display:block;color:var(--muted);margin-top:3px}.status-chip{display:inline-block;border-radius:5px;padding:4px 7px;font-size:9px;font-weight:750;letter-spacing:.05em;text-transform:uppercase;background:#edf5e8;color:#3f6534}.status-chip.off{background:#fff0f0;color:#8a3333}.admin-note{font-size:11px;color:var(--muted);line-height:1.7}.admin-form-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:15px}.admin-actions{display:flex;gap:7px;align-items:center}.button.compact{padding:6px 9px;font-size:10px}.admin-audit{margin-top:18px}.admin-audit .entry p{margin:4px 0}.admin-current{font-size:10px;color:var(--muted)}.admin-tools{display:grid;grid-template-columns:minmax(200px,1fr) 180px;gap:10px;margin-bottom:14px}.identity-chip{display:inline-block;border-radius:5px;padding:4px 7px;font-size:9px;font-weight:700;background:#eef4f8;color:#456982}.identity-chip.pending{background:#fff8eb;color:#7d6325}.manager-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}.metric-card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:18px}.metric-card b{display:block;font-size:26px;line-height:1.1;margin-bottom:5px}.metric-card span{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700}.metric-card.attention b{color:#8a3333}.manager-table{width:100%;border-collapse:collapse}.manager-table th,.manager-table td{text-align:left;border-bottom:1px solid var(--line);padding:11px 9px;font-size:12px}.manager-table th{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);background:#f8fafb}.manager-split{display:grid;grid-template-columns:minmax(0,1fr);gap:18px}.manager-team-label{font-size:11px;color:var(--muted);margin:-5px 0 0}.jobs-layout{display:grid;grid-template-columns:minmax(300px,.9fr) minmax(0,1.1fr);gap:18px}.job-list{display:grid;gap:8px}.job-card{display:block;width:100%;text-align:left;border:1px solid var(--line);background:#fff;border-radius:9px;padding:15px;color:var(--ink)}.job-card.active{border-color:#88aabe;background:#eef5f8;box-shadow:inset 3px 0 #21616b}.job-card strong{display:block;font-size:13px;margin-bottom:5px}.job-card small{font-size:10px;color:var(--muted)}.job-detail-id{font:11px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted);overflow-wrap:anywhere}.jobs-tools{display:flex;gap:10px;align-items:end}.jobs-tools>div{flex:1}.candidate-card{display:block;width:100%;text-align:left;border:1px solid var(--line);background:#fff;border-radius:9px;padding:15px;color:var(--ink)}.candidate-card.active{border-color:#88aabe;background:#eef5f8;box-shadow:inset 3px 0 #21616b}.candidate-card strong{display:block;font-size:13px;margin-bottom:5px}.candidate-card small{font-size:10px;color:var(--muted)}
@media(max-width:1000px){.manager-metrics{grid-template-columns:1fr 1fr}.jobs-layout{grid-template-columns:1fr}.login-story{padding:40px}.login-story h1{font-size:38px}.workspace{grid-template-columns:180px minmax(0,1fr)}.sidebar{padding:25px 12px}.content{padding:23px}.topbar{padding:20px 23px}.work-layout{grid-template-columns:220px minmax(0,1fr)}}
@media(max-width:760px){.login-layout{display:block}.login-story{padding:26px}.login-story h1{font-size:31px;margin:30px 0 15px}.login-story p{font-size:14px}.story-foot{display:none}.login-form{padding:30px 24px}.workspace{display:block}.sidebar{position:static;height:auto;padding:13px 18px;flex-direction:row;gap:20px;align-items:center;flex-wrap:wrap}.sidebar .brand{font-size:22px;margin:0}.sidebar .brand small{font-size:8px}.sidebar nav{display:flex;gap:5px}.nav-item{width:auto;margin:0;padding:8px 11px;font-size:11px}.nav-label,.sidebar-footer{display:none}.topbar{padding:19px}.topbar h1{font-size:21px}.account{gap:10px}.account-name{font-size:11px;max-width:125px;overflow-wrap:anywhere}.content{padding:20px 15px}.hero{padding:23px}.hero h2{font-size:25px}.hero-number{display:none}.work-layout{grid-template-columns:1fr}.work-list{grid-template-columns:1fr 1fr}.case-card{padding:12px}.panel{padding:18px}.grid-two{grid-template-columns:1fr}.footer{flex-direction:column}.form-footer{align-items:flex-start}.tabs{gap:15px}.section-title{flex-wrap:wrap}.admin-grid{grid-template-columns:1fr}.admin-table{min-width:650px}}
`;
const SCRIPT=String.raw`
(()=>{'use strict';
const $=s=>document.querySelector(s), root=$('#app');
let session=null,cases=[],active=null,tab='notes',nextCase=null,expiryTimer=null,adminUsers=[],adminTeams=[],adminQuery='',adminStatus='all',jobs=[],nextJob=null,activeJob=null,jobQuery='',candidates=[],nextCandidate=null,activeCandidate=null,candidateQuery='',intakeBatches=[],activeIntake=null,weeklyReview=null,weeklyWeek='',publications=[],activePublication=null;
const pending=new Map();
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=v=>new Date(v).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});
const ymdLocal=d=>[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
const currentMonday=()=>{const d=new Date(),delta=(d.getDay()+6)%7;d.setHours(12,0,0,0);d.setDate(d.getDate()-delta);return ymdLocal(d);};
const msg=(text,kind='error')=>{const el=$('#message');if(el){el.className='notice status-message '+kind;el.textContent=text;el.hidden=!text;}};
const managed=()=>session&&['manager','admin'].includes(session.member.role);
function login(message='',kind='error'){
 clearTimeout(expiryTimer);session=null;cases=[];active=null;
 root.innerHTML='<div class="login-layout"><section class="login-story"><div class="brand">medlivo<small>RECRUIT AI</small></div><div><p class="eyebrow">YOUR TEAM. ONE WORKSPACE.</p><h1>Good recruiting<br>starts with<br>shared context.</h1><p>Keep the next action clear. Review assigned work, leave useful notes, and keep follow-ups moving together.</p></div><div class="story-foot">NURSING &amp; ALLIED &nbsp; / &nbsp; REHABILITATION &nbsp; / &nbsp; LOCUM TENENS</div></section><section class="login-form"><div class="login-card"><p class="eyebrow">MEDLIVO TEAM ACCESS</p><h2>Welcome back.</h2><p>Sign in with your approved Medlivo Google account to open your team workspace.</p><div id="message" class="notice '+esc(kind)+'" '+(!message?'hidden':'')+'>'+esc(message)+'</div>'+(window.TEAM_ENABLED?'<a class="button primary full" href="/api/team/auth/start"><span class="google-letter" aria-hidden="true">G</span>Continue with Google</a>':'<div class="notice">Team sign-in has not been configured for this environment. Your administrator must complete the private staging setup first.</div>')+'<div class="login-detail">Access is granted by your administrator. A company email address alone does not create an account or grant a role.<br><br>JobDiva is disconnected. No messages or submissions are sent from this workspace.</div></div></section></div>';
}
async function call(path,{method='GET',data,key}={}){
 const headers={Accept:'application/json'};
 if(method!=='GET'){headers['Content-Type']='application/json';headers['X-CSRF-Token']=session?.csrf||'';if(key)headers['Idempotency-Key']=key;}
 let response;
 try{response=await fetch('/api/team'+path,{method,headers,credentials:'same-origin',cache:'no-store',redirect:'error',body:data===undefined?undefined:JSON.stringify(data),signal:AbortSignal.timeout(20000)});}
 catch{throw new Error(method==='GET'?'Could not reach the team service. Try again.':'The save could not be confirmed. Retry without changing the fields, or reload to inspect the saved record.');}
 let value;try{value=await response.json();}catch{throw new Error('The service returned an unexpected response. Try again.');}
 if(response.status===401){login(value.detail);throw new Error(value.detail);}
 if(!response.ok){const error=new Error(value.detail||'The request could not be completed.');error.status=response.status;throw error;}
 return value;
}
async function write(slot,path,data,method='POST'){
 const body=JSON.stringify(data);let operation=pending.get(slot);
 if(operation&&operation.body!==body)throw new Error('A previous save is unconfirmed. Retry the original fields, or reload and inspect the record before making another change.');
 if(!operation){operation={key:crypto.randomUUID(),body};pending.set(slot,operation);}
 const result=await call(path,{method,data,key:operation.key});pending.delete(slot);return result;
}
async function uploadXlsx(form){
 const file=form.querySelector('input[type=file]')?.files?.[0];
 if(!file)throw new Error('Choose an Excel workbook to upload.');
 if(!file.name.toLowerCase().endsWith('.xlsx'))throw new Error('Upload an .xlsx workbook.');
 if(file.size>5*1024*1024)throw new Error('The spreadsheet must be 5 MB or smaller.');
 const data=new FormData(form),headers={'X-CSRF-Token':session?.csrf||'','Idempotency-Key':crypto.randomUUID()};
 let response;try{response=await fetch('/api/team/job-intake/upload',{method:'POST',headers,credentials:'same-origin',cache:'no-store',redirect:'error',body:data,signal:AbortSignal.timeout(30000)});}
 catch{throw new Error('The spreadsheet upload could not be confirmed. Please try again.');}
 let value;try{value=await response.json();}catch{throw new Error('The service returned an unexpected upload response.');}
 if(response.status===401){login(value.detail);throw new Error(value.detail);}
 if(!response.ok)throw new Error(value.detail||'The spreadsheet could not be processed.');
 return value;
}
function shell(){const user=session.member;
 root.innerHTML='<div class="workspace"><aside class="sidebar"><div class="brand">medlivo<small>RECRUIT AI</small></div><nav aria-label="Team navigation"><p class="nav-label">TEAM WORKSPACE</p><button class="nav-item active" data-home>My work</button><button class="nav-item" data-jobs>Jobs</button><button class="nav-item" data-candidates>Candidates</button>'+'<button class="nav-item" data-weekly>'+(managed()?'Weekly review':'Weekly goals')+'</button>'+(managed()?'<button class="nav-item" data-intake>Job intake</button><button class="nav-item" data-publications>Job approval</button><button class="nav-item" data-manager>Team overview</button>':'')+(user.role==='admin'?'<button class="nav-item" data-admin>Admin</button>':'')+'</nav><div class="sidebar-footer"><div class="status-line"><span class="status-dot"></span>Shared team workspace</div><p>JobDiva disconnected.<br>No outreach or submissions.</p></div></aside><div class="main-shell"><header class="topbar"><div><p class="eyebrow">RECRUITER COMMAND CENTER</p><h1 id="pageTitle">My work</h1></div><div class="account"><div><span class="account-name">'+esc(user.display_name||'Team member')+'</span><span class="account-role">'+esc(user.role)+'</span></div><button class="signout" id="signout">Sign out</button></div></header><main class="content" id="main" tabindex="-1"><div id="message" class="status-message" role="status" aria-live="polite" hidden></div><section class="hero"><div><p class="eyebrow">FOCUS ON THE NEXT ACTION</p><h2>Keep the work moving.</h2><p>Notes, follow-ups, and ownership are shared with your authorized team. Every change keeps its author and history.</p></div><div class="hero-number"><b id="caseCount">0</b><small>WORK ITEMS LOADED</small></div></section><div class="section-title"><h2>'+ (managed()?'Your team’s work':'Assigned to you') +'</h2><button class="button" id="refresh">Refresh workspace</button></div><div class="work-layout"><section aria-label="Assigned work items"><div id="workList" class="work-list"></div><button class="button pager" id="moreCases" hidden>Load more work</button></section><section class="panel" id="detail" aria-label="Work item details"><div class="empty">Select a work item to review its notes and follow-ups.</div></section></div><footer class="footer"><span>Medlivo Recruit AI · Private team workflow</span><span>Session ends '+esc(new Date(session.expires*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}))+'</span></footer></main></div>';
 expiryTimer=setTimeout(()=>login('Your session has ended. Please sign in again.'),Math.max(0,session.expires*1000-Date.now()));
}
function drawCases(){
 const count=$('#caseCount'),list=$('#workList'),moreButton=$('#moreCases');
 if(count)count.textContent=cases.length;
 if(list)list.innerHTML=cases.length?cases.map(c=>'<button class="case-card '+(active?.id===c.id?'active':'')+'" data-case="'+esc(c.id)+'"><strong>'+esc(c.title)+'</strong><small>'+(c.owner_user_id===session.member.id?'Assigned to you':'Team work item')+' · Version '+esc(c.version)+'</small></button>').join(''):'<div class="panel empty">No work items are assigned to this account yet. Your administrator can assign a test work item.</div>';
 if(moreButton)moreButton.hidden=!nextCase;
}
async function loadCases(append=false){const result=await call('/cases?limit=50'+(append&&nextCase?'&after='+encodeURIComponent(nextCase):''));cases=append?[...cases,...result.items]:result.items;nextCase=result.next_cursor;drawCases();}
async function loadCase(id){
 try{active=await call('/cases/'+encodeURIComponent(id));drawCases();await drawDetail();}
 catch(error){if(error.status===403||error.status===404){active=null;drawCases();$('#detail').innerHTML='<div class="empty">This work item is no longer available to your account.</div>';}throw error;}
}
async function drawDetail(){
 if(!active)return;const id=active.id;
 $('#detail').innerHTML='<div class="detail-heading"><div><p class="eyebrow">SHARED WORK ITEM</p><h2>'+esc(active.title)+'</h2><p class="muted small">'+(active.owner_user_id===session.member.id?'Assigned to you':'Assigned within your team')+' · Version '+esc(active.version)+'</p></div><span class="pill">TEAM ONLY</span></div><div class="tabs" role="tablist" aria-label="Work item sections">'+['notes','tasks','activity',...(managed()?['ownership']:[])].map(t=>'<button class="tab '+(tab===t?'active':'')+'" role="tab" aria-selected="'+(tab===t)+'" data-tab="'+t+'">'+({notes:'Notes',tasks:'Follow-ups',activity:'Activity',ownership:'Ownership'}[t])+'</button>').join('')+'</div><div id="section"><div class="loading">Loading shared '+esc(tab)+'…</div></div>';
 const prefix='/cases/'+id;
 const resource={notes:'notes',tasks:'tasks',activity:'audit',ownership:'eligible-owners'}[tab];
 const result=await call(prefix+'/'+resource+'?limit=50');
 if(!active||active.id!==id)return;
 const rows=result.items||[];
 if(tab==='notes'){
 $('#section').innerHTML='<form id="noteForm"><label for="note">Add a note</label><textarea id="note" maxlength="4000" required placeholder="What should the next person know?"></textarea><div class="form-footer"><small>Visible to your authorized team. Do not add sensitive medical reports.</small><button class="button primary" type="submit">Save note</button></div></form><hr class="section-rule"><h3>Shared notes</h3><div id="records">'+noteRows(rows)+'</div>'+more(result.next_cursor,'notes');
 }else if(tab==='tasks'){
 $('#section').innerHTML='<form id="taskForm"><div class="grid-two"><div><label for="taskTitle">Follow-up</label><input id="taskTitle" maxlength="250" required placeholder="Confirm next availability"></div><div><label for="taskDue">Due in your local time</label><input id="taskDue" type="datetime-local" required></div></div><div class="form-footer"><small>Planning only. No email, text, or reminder is sent.</small><button class="button primary" type="submit">Create follow-up</button></div></form><hr class="section-rule"><h3>Shared follow-ups</h3><div id="records">'+taskRows(rows)+'</div>'+more(result.next_cursor,'tasks');
 }else if(tab==='activity'){
 $('#section').innerHTML='<h3>Work item history</h3><p class="muted small">Changes are recorded with their author. New activity may appear on another page; use Refresh to recheck the list.</p><div id="records">'+auditRows(rows)+'</div>'+more(result.next_cursor,'audit');
 }else{
 $('#section').innerHTML='<h3>Reassign this work item</h3><p class="muted small">Follow-ups move with the work item. This does not change JobDiva or the original job’s owner.</p><form id="ownerForm"><label for="owner">Active recruiter on this team</label><select id="owner" required><option value="">Select a recruiter</option>'+rows.filter(r=>r.id!==active.owner_user_id).map(r=>'<option value="'+esc(r.id)+'">'+esc(r.display_name||'Team member')+'</option>').join('')+'</select><label for="reason">Reason for the change</label><textarea id="reason" required minlength="5" maxlength="500" placeholder="Explain the coverage or workload change."></textarea><div class="form-footer"><small>The reason is saved in the activity history.</small><button class="button primary" type="submit">Reassign work item</button></div></form>'+(result.truncated?'<p class="notice">This list is limited to 100 members. Contact your administrator for another owner.</p>':'');
 }
}
function filteredCandidates(){
 const q=candidateQuery.trim().toLowerCase();
 return q?candidates.filter(candidate=>String(candidate.canonical_name||'').toLowerCase().includes(q)):candidates;
}
function drawCandidateList(){
 const list=$('#candidateList');if(!list)return;
 const rows=filteredCandidates();
 list.innerHTML=rows.length?rows.map(candidate=>'<button class="candidate-card '+(activeCandidate?.id===candidate.id?'active':'')+'" data-candidate="'+esc(candidate.id)+'"><strong>'+esc(candidate.canonical_name||'Unnamed candidate')+'</strong><small>Canonical Medlivo candidate</small></button>').join(''):'<div class="panel empty">No candidates match this view.</div>';
 const more=$('#moreCandidates');if(more)more.hidden=!nextCandidate;
}
async function loadCandidates(append=false){
 const result=await call('/candidates?limit=50'+(append&&nextCandidate?'&after='+encodeURIComponent(nextCandidate):''));
 candidates=append?[...candidates,...result.items]:result.items;nextCandidate=result.next_cursor;drawCandidateList();
 const count=$('#candidateCount');if(count)count.textContent=candidates.length;
}
async function loadCandidate(id){
 activeCandidate=await call('/candidates/'+encodeURIComponent(id));drawCandidateList();
 const detail=$('#candidateDetail');if(detail)detail.innerHTML='<div class="detail-heading"><div><p class="eyebrow">CANONICAL CANDIDATE</p><h2>'+esc(activeCandidate.canonical_name||'Unnamed candidate')+'</h2><p class="job-detail-id">'+esc(activeCandidate.id)+'</p></div><span class="pill">READ ONLY</span></div><hr class="section-rule"><h3>Recruit AI candidate record</h3><p class="muted small">This is the trusted Medlivo candidate identity record. Resume intelligence, licenses, certifications, specialties, location, availability, compliance readiness, and contact preferences will appear here after JobDiva candidate synchronization is enabled.</p><div class="notice">No outreach, candidate update, submission, or JobDiva write-back is performed from this screen.</div>';
}
async function drawCandidates(){
 $('#pageTitle').textContent='Candidates';
 document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n.hasAttribute('data-candidates')));
 $('#main').innerHTML='<div id="message" class="status-message" role="status" aria-live="polite" hidden></div><section class="hero"><div><p class="eyebrow">CANDIDATE INTELLIGENCE</p><h2>Build from one trusted candidate identity.</h2><p>Browse canonical Medlivo candidate records now. Resume, credential, availability, and matching intelligence will layer onto these records when JobDiva synchronization is enabled.</p></div><div class="hero-number"><b id="candidateCount">0</b><small>CANDIDATES LOADED</small></div></section><div class="section-title"><h2>Candidate directory</h2><button class="button" id="refreshCandidates">Refresh candidates</button></div><div class="jobs-tools"><div><label for="candidateSearch">Search loaded candidates</label><input id="candidateSearch" value="'+esc(candidateQuery)+'" placeholder="Search by candidate name" autocomplete="off"></div></div><div class="jobs-layout" style="margin-top:16px"><section><div id="candidateList" class="job-list"></div><button class="button pager" id="moreCandidates" hidden>Load more candidates</button></section><section class="panel" id="candidateDetail"><div class="empty">Select a candidate to review the canonical record.</div></section></div><footer class="footer"><span>Medlivo Recruit AI · Candidates</span><span>Canonical identity layer · Read only</span></footer>';
 await loadCandidates();
 if(activeCandidate&&candidates.some(candidate=>candidate.id===activeCandidate.id))await loadCandidate(activeCandidate.id);
}
function filteredJobs(){
 const q=jobQuery.trim().toLowerCase();
 return q?jobs.filter(job=>String(job.title||'').toLowerCase().includes(q)):jobs;
}
function drawJobList(){
 const list=$('#jobList');if(!list)return;
 const rows=filteredJobs();
 list.innerHTML=rows.length?rows.map(job=>'<button class="job-card '+(activeJob?.id===job.id?'active':'')+'" data-job="'+esc(job.id)+'"><strong>'+esc(job.title)+'</strong><small>Canonical Medlivo job</small></button>').join(''):'<div class="panel empty">No jobs match this view.</div>';
 const more=$('#moreJobs');if(more)more.hidden=!nextJob;
}
async function loadJobs(append=false){
 const result=await call('/jobs?limit=50'+(append&&nextJob?'&after='+encodeURIComponent(nextJob):''));
 jobs=append?[...jobs,...result.items]:result.items;nextJob=result.next_cursor;drawJobList();
 const count=$('#jobCount');if(count)count.textContent=jobs.length;
}
async function loadJob(id){
 activeJob=await call('/jobs/'+encodeURIComponent(id));drawJobList();
 const detail=$('#jobDetail');if(detail)detail.innerHTML='<div class="detail-heading"><div><p class="eyebrow">CANONICAL REQUISITION</p><h2>'+esc(activeJob.title)+'</h2><p class="job-detail-id">'+esc(activeJob.id)+'</p></div><span class="pill">READ ONLY</span></div><hr class="section-rule"><h3>Recruit AI job record</h3><p class="muted small">This is the trusted Medlivo canonical job record. Source-specific fields, healthcare requirements, and matching evidence will appear here as the JobDiva connector is enabled and normalized.</p><div class="notice">No JobDiva write-back, candidate submission, outreach, or status change is performed from this screen.</div>';
}
async function drawJobs(){
 $('#pageTitle').textContent='Jobs';
 document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n.hasAttribute('data-jobs')));
 $('#main').innerHTML='<div id="message" class="status-message" role="status" aria-live="polite" hidden></div><section class="hero"><div><p class="eyebrow">REQUISITION INTELLIGENCE</p><h2>Start with a trusted job record.</h2><p>Browse canonical Medlivo requisitions now. JobDiva source fields and healthcare matching requirements will layer onto these records as the connector is activated.</p></div><div class="hero-number"><b id="jobCount">0</b><small>JOBS LOADED</small></div></section><div class="section-title"><h2>Jobs</h2><button class="button" id="refreshJobs">Refresh jobs</button></div><div class="jobs-tools"><div><label for="jobSearch">Search loaded jobs</label><input id="jobSearch" value="'+esc(jobQuery)+'" placeholder="Search by job title" autocomplete="off"></div></div><div class="jobs-layout" style="margin-top:16px"><section><div id="jobList" class="job-list"></div><button class="button pager" id="moreJobs" hidden>Load more jobs</button></section><section class="panel" id="jobDetail"><div class="empty">Select a job to review the canonical requisition.</div></section></div><footer class="footer"><span>Medlivo Recruit AI · Jobs</span><span>Canonical data layer · Read only</span></footer>';
 await loadJobs();
 if(activeJob&&jobs.some(j=>j.id===activeJob.id))await loadJob(activeJob.id);
}
async function drawManager(){
 if(!managed())throw new Error('Manager access required.');
 const [overview,caseResult]=await Promise.all([call('/manager/overview'),call('/cases?limit=50')]);
 cases=caseResult.items||[];nextCase=caseResult.next_cursor;
 const totals=overview.totals||{},teams=overview.teams||[],recruiters=overview.recruiters||[];
 $('#pageTitle').textContent='Team overview';
 document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n.hasAttribute('data-manager')));
 const teamLabel=teams.length?teams.map(t=>esc(t.name)+(t.division?' · '+esc(t.division):'')).join(' / '):'No managed team is assigned';
 $('#main').innerHTML='<div id="message" class="status-message" role="status" aria-live="polite" hidden></div>'+
 '<section class="hero"><div><p class="eyebrow">TEAM OPERATIONS</p><h2>See the workload before it becomes a bottleneck.</h2><p>Review team capacity, open follow-ups, overdue work, and recruiter ownership from one place.</p><p class="manager-team-label">'+teamLabel+'</p></div><div class="hero-number"><b>'+esc(totals.active_recruiters||0)+'</b><small>ACTIVE RECRUITERS</small></div></section>'+
 '<section class="manager-metrics" aria-label="Team workload summary">'+
 '<div class="metric-card"><b>'+esc(totals.work_items||0)+'</b><span>Work items</span></div>'+
 '<div class="metric-card"><b>'+esc(totals.active_recruiters||0)+'</b><span>Active recruiters</span></div>'+
 '<div class="metric-card"><b>'+esc(totals.open_followups||0)+'</b><span>Open follow-ups</span></div>'+
 '<div class="metric-card '+((totals.overdue_followups||0)>0?'attention':'')+'"><b>'+esc(totals.overdue_followups||0)+'</b><span>Overdue follow-ups</span></div>'+
 '</section>'+
 '<div class="section-title"><h2>Recruiter workload</h2><button class="button" id="refreshManager">Refresh overview</button></div>'+
 '<section class="panel admin-table-wrap">'+
 '<table class="manager-table"><thead><tr><th>Recruiter</th><th>Team</th><th>Work items</th><th>Open follow-ups</th><th>Overdue</th></tr></thead><tbody>'+
 (recruiters.length?recruiters.map(r=>'<tr><td><strong>'+esc(r.display_name||r.email||'Team member')+'</strong><small>'+esc(r.email||'')+'</small></td><td>'+esc((teams.find(t=>t.id===r.team_id)||{}).name||'Assigned team')+'</td><td>'+esc(r.work_items)+'</td><td>'+esc(r.open_followups)+'</td><td>'+(r.overdue_followups?'<span class="status-chip off">'+esc(r.overdue_followups)+'</span>':'0')+'</td></tr>').join(''):'<tr><td colspan="5" class="empty">No active recruiters are assigned to the managed team.</td></tr>')+
 '</tbody></table></section>'+
 '<div class="section-title"><h2>Team work queue</h2><span class="pill">MANAGER VIEW</span></div>'+
 '<div class="work-layout"><section aria-label="Team work items"><div id="workList" class="work-list"></div><button class="button pager" id="moreCases" hidden>Load more work</button></section><section class="panel" id="detail" aria-label="Work item details"><div class="empty">Select a work item to review notes, follow-ups, activity, or ownership.</div></section></div>'+
 '<footer class="footer"><span>Medlivo Recruit AI · Manager workspace</span><span>Team metrics are derived from the shared workspace</span></footer>';
 drawCases();
 if(active&&cases.some(c=>c.id===active.id))await loadCase(active.id);
}
function adminEditor(user=null){
 const teams=adminTeams;
 if(user){
   const self=user.id===session.member.id;
   return '<h3>Edit workspace user</h3><p class="admin-note">Change the user’s display name, role, team, or active access. Email remains tied to the approved identity record.</p>'+
   (self?'<div class="notice">Your own administrator access cannot be changed here. This protects the workspace from accidental lockout.</div>':
   '<form id="adminEditForm" data-user-id="'+esc(user.id)+'"><label for="editName">Display name</label><input id="editName" maxlength="200" required autocomplete="off" value="'+esc(user.display_name||'')+'"><label>Email</label><input disabled value="'+esc(user.email)+'"><div class="grid-two"><div><label for="editRole">Role</label><select id="editRole" required>'+['recruiter','manager','admin'].map(r=>'<option value="'+r+'" '+(user.role===r?'selected':'')+'>'+r[0].toUpperCase()+r.slice(1)+'</option>').join('')+'</select></div><div><label for="editTeam">Team</label><select id="editTeam"><option value="">No team</option>'+teams.map(t=>'<option value="'+esc(t.id)+'" '+(user.team_id===t.id?'selected':'')+'>'+esc(t.name)+(t.division?' · '+esc(t.division):'')+'</option>').join('')+'</select></div></div><label for="editActive">Access status</label><select id="editActive"><option value="true" '+(user.is_active?'selected':'')+'>Active</option><option value="false" '+(!user.is_active?'selected':'')+'>Inactive</option></select><div class="admin-form-actions"><button class="button" type="button" data-cancel-edit>Cancel</button><button class="button primary" type="submit">Save changes</button></div></form>')+
   '<p class="admin-note">Deactivating a user blocks workspace access on the next authenticated request. Existing work history remains preserved.</p>';
 }
 return '<h3>Provision a Medlivo user</h3><p class="admin-note">Create or update the approved account record. On first Google sign-in, the verified Medlivo email is bound to this pre-provisioned user.</p><form id="adminUserForm"><label for="adminName">Display name</label><input id="adminName" maxlength="200" required autocomplete="off"><label for="adminEmail">Medlivo email</label><input id="adminEmail" type="email" maxlength="320" required autocomplete="off" placeholder="name@medlivo.com"><div class="grid-two"><div><label for="adminRole">Role</label><select id="adminRole" required><option value="recruiter">Recruiter</option><option value="manager">Manager</option><option value="admin">Admin</option></select></div><div><label for="adminTeam">Team</label><select id="adminTeam"><option value="">No team</option>'+teams.map(t=>'<option value="'+esc(t.id)+'">'+esc(t.name)+(t.division?' · '+esc(t.division):'')+'</option>').join('')+'</select></div></div><div class="admin-form-actions"><button class="button primary" type="submit">Provision user</button></div></form><p class="admin-note">Recruiters and managers require a team. Admin may be provisioned without one.</p>';
}
function adminAuditRows(rows){
 return rows.length?rows.map(r=>{
   const before=r.before_state||{},after=r.after_state||{},changes=[];
   if(before.role!==after.role)changes.push('Role: '+(before.role||'new')+' → '+after.role);
   if(before.team_id!==after.team_id)changes.push('Team assignment changed');
   if(before.is_active!==after.is_active)changes.push('Access: '+(after.is_active?'activated':'deactivated'));
   if(before.display_name!==after.display_name)changes.push('Display name updated');
   if(!changes.length)changes.push(r.action==='user.provisioned'?'User provisioned':'User record updated');
   return '<article class="entry"><span class="audit-badge">'+esc(r.action==='user.provisioned'?'User provisioned':'User updated')+'</span><p><strong>'+esc(r.target_display_name||r.target_email||'Workspace user')+'</strong> · '+esc(changes.join(' · '))+'</p><div class="entry-meta"><span>'+esc(actor(r.actor_user_id,r.actor_display_name))+'</span><time>'+esc(fmt(r.created_at))+'</time></div></article>';
 }).join(''):'<p class="empty">No administrator access changes have been recorded yet.</p>';
}
function adminUserRows(teamNames){
 const q=adminQuery.trim().toLowerCase();
 const rows=adminUsers.filter(u=>{
   if(adminStatus==='active'&&!u.is_active)return false;
   if(adminStatus==='inactive'&&u.is_active)return false;
   if(!q)return true;
   const team=u.team_id?(teamNames.get(u.team_id)||''):'';
   return [u.display_name,u.email,u.role,team].some(v=>String(v||'').toLowerCase().includes(q));
 });
 return rows.length?rows.map(u=>'<tr><td>'+esc(u.display_name||'Team member')+'</td><td><span>'+esc(u.email)+'</span>'+(u.email.endsWith('@medlivo.com')?'':'<small>Test-only identity</small>')+'</td><td>'+esc(u.role)+'</td><td>'+esc(u.team_id?teamNames.get(u.team_id)||'Assigned team':'—')+'</td><td><span class="status-chip '+(u.is_active?'':'off')+'">'+(u.is_active?'Active':'Inactive')+'</span></td><td><span class="identity-chip '+(u.identity_bound?'':'pending')+'">'+(u.identity_bound?'Google linked':'Not linked')+'</span></td><td>'+(u.id===session.member.id?'<span class="admin-current">Current admin</span>':'<button class="button compact" data-edit-user="'+esc(u.id)+'">Edit</button>')+'</td></tr>').join(''):'<tr><td colspan="7" class="empty">No workspace users match these filters.</td></tr>';
}
async function drawAdmin(selectedUserId=null){
 if(session.member.role!=='admin')throw new Error('Administrator access required.');
 const [usersResult,teamsResult,auditResult]=await Promise.all([call('/admin/users'),call('/admin/teams'),call('/admin/audit?limit=50')]);
 adminUsers=usersResult.items||[];adminTeams=teamsResult.items||[];
 const teamNames=new Map(adminTeams.map(t=>[t.id,t.name])),selected=adminUsers.find(u=>u.id===selectedUserId)||null;
 $('#pageTitle').textContent='Admin';
 document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n.hasAttribute('data-admin')));
 $('#main').innerHTML='<div id="message" class="status-message" role="status" aria-live="polite" hidden></div><section class="hero"><div><p class="eyebrow">ACCESS &amp; TEAM MANAGEMENT</p><h2>Provision people, not passwords.</h2><p>Approve Medlivo users, assign roles and teams, control active access, and keep every administrator change auditable.</p></div><div class="hero-number"><b>'+esc(adminUsers.length)+'</b><small>USERS</small></div></section><div class="section-title"><h2>Workspace users</h2><span class="pill">ADMIN ONLY</span></div><div class="admin-grid"><section class="panel admin-table-wrap"><div class="admin-tools"><div><label for="adminSearch">Search users</label><input id="adminSearch" value="'+esc(adminQuery)+'" placeholder="Name, email, role, or team" autocomplete="off"></div><div><label for="adminStatus">Status</label><select id="adminStatus"><option value="all" '+(adminStatus==='all'?'selected':'')+'>All users</option><option value="active" '+(adminStatus==='active'?'selected':'')+'>Active</option><option value="inactive" '+(adminStatus==='inactive'?'selected':'')+'>Inactive</option></select></div></div><table class="admin-table"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Team</th><th>Status</th><th>Google identity</th><th>Action</th></tr></thead><tbody id="adminUserRows">'+adminUserRows(teamNames)+'</tbody></table>'+(usersResult.truncated?'<p class="notice">Showing the first 500 users. Use search and status filters to narrow this loaded set.</p>':'')+'</section><section class="panel" id="adminEditor">'+adminEditor(selected)+'</section></div><section class="panel admin-audit"><div class="section-title" style="margin-top:0"><h2>Recent admin activity</h2><span class="muted small">Latest 50 changes</span></div>'+adminAuditRows(auditResult.items||[])+'</section><footer class="footer"><span>Medlivo Recruit AI · Administrative access</span><span>Google identity remains the sign-in provider</span></footer>';
}
function actor(id,name){return id===session.member.id?'You':(name||('Team member '+String(id).slice(-6)));}
function publicationSection(section){
 const badge=section.provenance==='source_confirmed'?'SOURCE CONFIRMED':section.provenance==='medlivo_standard'?'MEDLIVO STANDARD':'AI SUGGESTED';
 return '<article class="entry"><span class="audit-badge">'+esc(badge)+'</span><strong>'+esc(section.heading||section.key)+'</strong><p>'+esc(section.content||'')+'</p>'+(section.requires_confirmation?'<span class="danger-text small">Manager confirmation required</span>':'')+'</article>';
}
function sourceSnapshotView(source){
 const entries=Object.entries(source||{}).filter(([,v])=>v!==null&&v!==''&&v!==undefined);
 return entries.length?entries.map(([k,v])=>'<div class="entry"><strong>'+esc(k.replaceAll('_',' '))+'</strong><p>'+esc(typeof v==='object'?JSON.stringify(v):v)+'</p></div>').join(''):'<p class="empty">No source snapshot is available.</p>';
}
async function loadPublication(id){
 const result=await call('/job-publications/'+encodeURIComponent(id));activePublication=result.publication;
 const detail=$('#publicationDetail');if(!detail)return;
 const p=result.publication,e=p.enhanced_snapshot||{},quality=p.quality_score||{},sections=e.sections||[];
 const canWebsite=p.recruiting_status==='approved'&&p.readiness==='ready_to_publish';
 detail.innerHTML='<div class="detail-heading"><div><p class="eyebrow">MANAGER APPROVAL</p><h2>'+esc(e.public_title||p.source_snapshot?.title||'Job draft')+'</h2><p class="muted small">Version '+esc(p.version)+' · '+esc(p.readiness.replaceAll('_',' '))+'</p></div><span class="pill">'+esc(quality.overall??'–')+' / 100</span></div>'+
 '<div class="manager-metrics"><article class="metric-card"><b>'+esc(quality.core_data??'–')+'</b><span>Core data</span></article><article class="metric-card"><b>'+esc(quality.matching_readiness??'–')+'</b><span>Matching</span></article><article class="metric-card"><b>'+esc(quality.publishing_readiness??'–')+'</b><span>Publishing</span></article><article class="metric-card"><b>'+esc(p.website_status)+'</b><span>Website</span></article></div>'+
 '<div class="grid-two"><section class="panel"><p class="eyebrow">ORIGINAL SOURCE</p><h3>What the customer / JobDiva supplied</h3>'+sourceSnapshotView(p.source_snapshot)+'</section>'+
 '<section class="panel"><p class="eyebrow">MEDLIVO ENHANCED</p><h3>'+esc(e.public_title||'Enhanced job')+'</h3><p>'+esc(e.summary||'')+'</p>'+(sections.length?sections.map(publicationSection).join(''):'<p class="empty">Enhanced sections have not been generated yet.</p>')+'</section></div>'+
 ((quality.missing_fields||[]).length|| (quality.warnings||[]).length?'<section class="panel" style="margin-top:16px"><h3>Needs attention</h3>'+[...(quality.missing_fields||[]).map(x=>'Missing: '+x),...(quality.warnings||[])].map(x=>'<p class="danger-text">'+esc(x)+'</p>').join('')+'</section>':'')+
 '<div class="section-title"><h2>Manager decision</h2><div class="admin-actions"><button class="button" data-pub-decision="recruiting:rejected">Reject recruiting</button><button class="button primary" data-pub-decision="recruiting:approved">Approve for recruiting</button><button class="button" data-pub-decision="website:rejected">Reject website</button><button class="button primary" data-pub-decision="website:approved" '+(canWebsite?'':'disabled title="Approve for recruiting and resolve website readiness first"')+'>Approve for website</button></div></div>'+
 '<p class="admin-note">Website approval is intentionally separate. Internal bill rates and other protected fields remain outside the public job payload.</p>';
}
async function drawPublications(){
 if(!managed())throw new Error('Manager access required.');
 $('#pageTitle').textContent='Job approval';
 document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n.hasAttribute('data-publications')));
 const result=await call('/job-publications?limit=100');publications=result.items||[];
 $('#main').innerHTML='<div id="message" class="status-message" role="status" aria-live="polite" hidden></div>'+
 '<section class="hero"><div><p class="eyebrow">JOB QUALITY & PUBLISHING</p><h2>Approve the Medlivo version before candidates see it.</h2><p>Compare the original source with the standardized Medlivo job, review anything AI suggested, then approve recruiting and website publication separately.</p></div><div class="hero-number"><b>'+esc(publications.filter(p=>p.website_status==='pending').length)+'</b><small>AWAITING WEBSITE REVIEW</small></div></section>'+
 '<div class="jobs-layout" style="margin-top:18px"><section><div class="job-list">'+
 (publications.length?publications.map(p=>{const e=p.enhanced_snapshot||{};return '<button class="job-card '+(activePublication?.id===p.id?'active':'')+'" data-publication="'+esc(p.id)+'"><strong>'+esc(e.public_title||p.source_snapshot?.title||'Job draft')+'</strong><small>'+esc(p.readiness.replaceAll('_',' '))+' · Recruiting '+esc(p.recruiting_status)+' · Website '+esc(p.website_status)+'</small></button>';}).join(''):'<div class="panel empty">No enhanced jobs are waiting for manager approval yet.</div>')+
 '</div><button class="button pager" id="refreshPublications">Refresh approvals</button></section><section class="panel" id="publicationDetail"><div class="empty">Select a job to compare the source with the Medlivo-enhanced version.</div></section></div>'+
 '<footer class="footer"><span>Medlivo Recruit AI · Job approval</span><span>Human approval required before website publishing</span></footer>';
 if(activePublication&&publications.some(p=>p.id===activePublication.id))await loadPublication(activePublication.id);
}
function targetActual(target,actual){return '<b>'+esc(actual)+'</b><span>of '+esc(target)+' goal</span>';}
function exportWeeklyCsv(){
 if(!weeklyReview?.recruiters?.length)throw new Error('There is no weekly report to export.');
 const header=['Recruiter','Email','Submissions Goal','Submissions Actual','Interviews Goal','Interviews Actual','Closures Goal','Closures Actual','Offers','Starts','Qualified','Responses'];
 const rows=weeklyReview.recruiters.map(r=>[r.display_name||'',r.email||'',r.targets.submissions,r.actuals.submissions,r.targets.interviews,r.actuals.interviews,r.targets.closures,r.actuals.closures,r.actuals.offers,r.actuals.starts,r.actuals.qualified,r.actuals.responses]);
 const csv=[header,...rows].map(row=>row.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\r\n');
 const blob=new Blob([csv],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
 a.href=url;a.download='medlivo-recruiter-review-'+weeklyReview.week_start+'.csv';document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
}
async function drawWeekly(){
 weeklyWeek=weeklyWeek||currentMonday();
 $('#pageTitle').textContent=managed()?'Weekly recruiter review':'Weekly goals';
 document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n.hasAttribute('data-weekly')));
 if(managed()){
   weeklyReview=await call('/manager/weekly-review?week_start='+encodeURIComponent(weeklyWeek));
   const rows=weeklyReview.recruiters||[];
   $('#main').innerHTML='<div id="message" class="status-message" role="status" aria-live="polite" hidden></div>'+
   '<section class="hero"><div><p class="eyebrow">WEEKLY DELIVERY REVIEW</p><h2>Walk into Friday with the report already prepared.</h2><p>Monday goals are compared with synchronized activity so the review can focus on what moved, what closed, and where the team needs support.</p></div><div class="hero-number"><b>'+esc(rows.length)+'</b><small>RECRUITERS</small></div></section>'+
   '<div class="section-title"><h2>Goal vs. actual</h2><div class="admin-actions"><input id="weeklyWeek" type="date" value="'+esc(weeklyWeek)+'" style="width:160px"><button class="button" id="refreshWeekly">Load week</button><button class="button primary" id="exportWeekly">Export CSV</button></div></div>'+
   '<div class="admin-table-wrap"><table class="manager-table"><thead><tr><th>Recruiter</th><th>Submissions</th><th>Interviews</th><th>Closures</th><th>Offers</th><th>Starts</th><th>Qualified</th><th>Responses</th></tr></thead><tbody>'+
   (rows.length?rows.map(r=>'<tr><td><strong>'+esc(r.display_name||r.email)+'</strong><small>'+esc(r.email||'')+'</small></td><td>'+targetActual(r.targets.submissions,r.actuals.submissions)+'</td><td>'+targetActual(r.targets.interviews,r.actuals.interviews)+'</td><td>'+targetActual(r.targets.closures,r.actuals.closures)+'</td><td>'+esc(r.actuals.offers)+'</td><td>'+esc(r.actuals.starts)+'</td><td>'+esc(r.actuals.qualified)+'</td><td>'+esc(r.actuals.responses)+'</td></tr>').join(''):'<tr><td colspan="8">No active recruiters are assigned to this manager for the selected week.</td></tr>')+
   '</tbody></table></div><p class="admin-note">Actual activity is populated from Medlivo platform and JobDiva synchronization as those feeds are enabled. Recruiters do not manually type the Friday actuals.</p><footer class="footer"><span>Medlivo Recruit AI · Weekly recruiter review</span><span>Week of '+esc(weeklyWeek)+'</span></footer>';
 }else{
   const progress=await call('/recruiters/'+encodeURIComponent(session.member.id)+'/weekly-goals?week_start='+encodeURIComponent(weeklyWeek));
   weeklyReview=progress;
   const t=progress.targets,a=progress.actuals;
   $('#main').innerHTML='<div id="message" class="status-message" role="status" aria-live="polite" hidden></div>'+
   '<section class="hero"><div><p class="eyebrow">YOUR WEEKLY COMMITMENT</p><h2>Set the goal Monday. See progress all week.</h2><p>Your Friday actuals come from recruiting activity already captured by Medlivo and JobDiva. You only set the goals and focus on delivery.</p></div><div class="hero-number"><b>'+esc(a.submissions)+'</b><small>SUBMISSIONS THIS WEEK</small></div></section>'+
   '<div class="grid-two" style="margin-top:18px"><section class="panel"><h3>Weekly goals</h3><form id="weeklyGoalForm"><label for="goalWeek">Week starting</label><input id="goalWeek" type="date" value="'+esc(weeklyWeek)+'" required><div class="grid-two"><div><label for="goalSubmissions">Resume submissions</label><input id="goalSubmissions" type="number" min="0" max="1000" value="'+esc(t.submissions)+'" required></div><div><label for="goalInterviews">Interviews</label><input id="goalInterviews" type="number" min="0" max="1000" value="'+esc(t.interviews)+'" required></div><div><label for="goalClosures">Positions to close</label><input id="goalClosures" type="number" min="0" max="1000" value="'+esc(t.closures)+'" required></div><div><label for="goalPriorityJobs">Priority jobs</label><input id="goalPriorityJobs" type="number" min="0" max="1000" value="'+esc(t.priority_jobs)+'" required></div></div><label for="goalNotes">Focus for the week</label><textarea id="goalNotes" maxlength="1000" placeholder="Optional">'+esc(progress.notes||'')+'</textarea><div class="admin-form-actions"><button class="button primary" type="submit">Save weekly goals</button></div></form></section>'+
   '<section class="panel"><h3>Progress so far</h3><div class="manager-metrics"><article class="metric-card">'+targetActual(t.submissions,a.submissions)+'</article><article class="metric-card">'+targetActual(t.interviews,a.interviews)+'</article><article class="metric-card">'+targetActual(t.closures,a.closures)+'</article><article class="metric-card"><b>'+esc(a.starts)+'</b><span>Starts</span></article></div><p class="admin-note">'+(progress.actuals_generated_at?'Activity refreshed '+esc(fmt(progress.actuals_generated_at))+'.':'Activity synchronization has not produced a snapshot yet.')+'</p></section></div>'+
   '<footer class="footer"><span>Medlivo Recruit AI · Weekly goals</span><span>Week of '+esc(weeklyWeek)+'</span></footer>';
 }
}
async function loadIntakeBatch(id){
 const result=await call('/job-intake/batches/'+encodeURIComponent(id)+'/items?limit=200');activeIntake=result.batch;
 const detail=$('#intakeDetail');if(!detail)return;
 const rows=result.items||[];
 detail.innerHTML='<div class="detail-heading"><div><p class="eyebrow">UPLOAD REVIEW</p><h2>'+esc(activeIntake.customer_name)+'</h2><p class="muted small">'+esc(activeIntake.source_filename)+' · '+esc(activeIntake.division)+'</p></div><span class="pill">'+esc(activeIntake.status)+'</span></div>'+
 '<div class="manager-metrics"><article class="metric-card"><b>'+esc(activeIntake.ready_count)+'</b><span>Ready</span></article><article class="metric-card attention"><b>'+esc(activeIntake.review_count)+'</b><span>Needs review</span></article><article class="metric-card"><b>'+esc(activeIntake.duplicate_count)+'</b><span>Duplicates</span></article><article class="metric-card"><b>'+esc(activeIntake.row_count)+'</b><span>Total rows</span></article></div>'+
 '<div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>Row</th><th>Status</th><th>Position</th><th>Facility / Location</th><th>Dates / Hours</th><th>Review note</th></tr></thead><tbody>'+
 (rows.length?rows.map(item=>{const j=item.normalized_job||{},errs=item.validation_errors||[];return '<tr><td>'+esc(item.row_number)+'</td><td><span class="status-chip '+(item.status==='review'||item.status==='duplicate'?'off':'')+'">'+esc(item.status)+'</span></td><td><strong>'+esc(j.title||'Needs mapping')+'</strong><small>'+esc(j.requisition_id||'')+'</small></td><td>'+esc(j.facility||'')+'<small>'+esc([j.city,j.state].filter(Boolean).join(', '))+'</small></td><td>'+esc([j.start_date,j.end_date].filter(Boolean).join(' → '))+'<small>'+(j.hours_per_week!=null?esc(j.hours_per_week)+' hrs/week':'')+'</small></td><td>'+esc(errs.map(e=>e.message).join('; ')||(item.status==='duplicate'?'Possible duplicate row':''))+'</td></tr>';}).join(''):'<tr><td colspan="6">No rows were processed.</td></tr>')+
 '</tbody></table></div>';
}
async function drawJobIntake(){
 if(!managed())throw new Error('Manager access required.');
 $('#pageTitle').textContent='Job intake';
 document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n.hasAttribute('data-intake')));
 const result=await call('/job-intake/batches?limit=50');intakeBatches=result.items||[];
 $('#main').innerHTML='<div id="message" class="status-message" role="status" aria-live="polite" hidden></div>'+
 '<section class="hero"><div><p class="eyebrow">DIRECT CUSTOMER JOB INTAKE</p><h2>Turn customer Excel sheets into review-ready jobs.</h2><p>Upload the customer workbook. Medlivo recognizes known columns, reuses saved customer mappings, flags missing information and duplicate rows, and prepares the jobs for approval before JobDiva sync.</p></div><div class="hero-number"><b>'+esc(intakeBatches.length)+'</b><small>RECENT BATCHES</small></div></section>'+
 '<div class="grid-two" style="margin-top:18px"><section class="panel"><h3>Upload Excel workbook</h3><p class="admin-note">Managers can upload .xlsx files up to 5 MB. The workbook is processed inside the authenticated workspace.</p><form id="intakeUploadForm"><label for="intakeCustomer">Customer</label><input id="intakeCustomer" name="customer_name" maxlength="200" required placeholder="Customer or health system name"><label for="intakeDivision">Division</label><select id="intakeDivision" name="division" required><option value="Rehabilitation">Rehabilitation</option><option value="Nursing & Allied">Nursing &amp; Allied</option><option value="Locum Tenens">Locum Tenens</option></select><label for="intakeFile">Excel workbook</label><input id="intakeFile" name="source_file" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" required><div class="admin-form-actions"><button class="button primary" type="submit">Upload and review</button></div></form></section>'+
 '<section class="panel" id="intakeDetail"><div class="empty">Upload a workbook or select a recent batch to review its jobs.</div></section></div>'+
 '<div class="section-title"><h2>Recent intake batches</h2><button class="button" id="refreshIntake">Refresh</button></div><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>Customer</th><th>Division</th><th>File</th><th>Ready</th><th>Review</th><th>Duplicates</th><th></th></tr></thead><tbody>'+
 (intakeBatches.length?intakeBatches.map(batch=>'<tr><td><strong>'+esc(batch.customer_name)+'</strong><small>'+esc(fmt(batch.created_at))+'</small></td><td>'+esc(batch.division)+'</td><td>'+esc(batch.source_filename)+'</td><td>'+esc(batch.ready_count)+'</td><td>'+esc(batch.review_count)+'</td><td>'+esc(batch.duplicate_count)+'</td><td><button class="button compact" data-intake-batch="'+esc(batch.id)+'">Review</button></td></tr>').join(''):'<tr><td colspan="7">No customer spreadsheets have been uploaded yet.</td></tr>')+
 '</tbody></table></div><footer class="footer"><span>Medlivo Recruit AI · Job intake</span><span>Human approval remains required before ATS write-back</span></footer>';
 if(activeIntake&&intakeBatches.some(b=>b.id===activeIntake.id))await loadIntakeBatch(activeIntake.id);
}
function noteRows(rows){return rows.length?rows.map(r=>'<article class="entry"><p>'+esc(r.body)+'</p><div class="entry-meta"><span>'+esc(actor(r.actor_user_id,r.actor_display_name))+'</span><time>'+esc(fmt(r.created_at))+'</time></div></article>').join(''):'<p class="empty">No shared notes yet.</p>';}
function taskRows(rows){return rows.length?rows.map(r=>'<article class="entry task-row '+(r.status==='done'?'done':'')+'"><div><strong>'+esc(r.title)+'</strong><p>Due '+esc(fmt(r.due_at))+' · '+esc(r.status)+' · '+esc(actor(r.actor_user_id,r.actor_display_name))+'</p></div><button class="button" data-task="'+esc(r.id)+'" data-version="'+esc(r.version)+'" data-status="'+esc(r.status==='done'?'open':'done')+'">'+(r.status==='done'?'Reopen':'Mark done')+'</button></article>').join(''):'<p class="empty">No follow-ups for this work item.</p>';}
function auditRows(rows){return rows.length?rows.map(r=>'<article class="entry"><span class="audit-badge">'+esc({'note.created':'Note saved','task.created':'Follow-up created','task.updated':'Follow-up updated','case.reassigned':'Ownership changed'}[r.action]||r.action)+'</span>'+(r.details?.reason?'<p>'+esc(r.details.reason)+'</p>':'')+'<div class="entry-meta"><span>'+esc(actor(r.actor_user_id,r.actor_display_name))+'</span><time>'+esc(fmt(r.created_at))+'</time></div></article>').join(''):'<p class="empty">No activity has been recorded yet.</p>';}
function more(cursor,kind){return cursor?'<button class="button pager" data-more="'+esc(cursor)+'" data-kind="'+kind+'">Load more history</button>':'';}
async function act(button,fn){if(button?.disabled)return;if(button)button.disabled=true;msg('');try{await fn();}catch(error){msg(error.message);}finally{if(button?.isConnected)button.disabled=false;}}
root.addEventListener('click',event=>{
 const b=event.target.closest('button');if(!b)return;
 if(b.dataset.case)return act(b,()=>loadCase(b.dataset.case));
 if(b.dataset.tab)return act(b,async()=>{tab=b.dataset.tab;await drawDetail();});
 if(b.hasAttribute('data-admin'))return act(b,()=>drawAdmin());
 if(b.hasAttribute('data-publications'))return act(b,()=>drawPublications());
 if(b.dataset.publication)return act(b,()=>loadPublication(b.dataset.publication));
 if(b.hasAttribute('data-weekly'))return act(b,()=>drawWeekly());
 if(b.hasAttribute('data-intake'))return act(b,()=>drawJobIntake());
 if(b.dataset.intakeBatch)return act(b,()=>loadIntakeBatch(b.dataset.intakeBatch));
 if(b.hasAttribute('data-jobs'))return act(b,()=>drawJobs());
 if(b.hasAttribute('data-candidates'))return act(b,()=>drawCandidates());
 if(b.dataset.job)return act(b,()=>loadJob(b.dataset.job));
 if(b.dataset.candidate)return act(b,()=>loadCandidate(b.dataset.candidate));
 if(b.id==='refreshJobs')return act(b,()=>drawJobs());
 if(b.id==='refreshCandidates')return act(b,()=>drawCandidates());
 if(b.id==='moreJobs')return act(b,()=>loadJobs(true));
 if(b.id==='moreCandidates')return act(b,()=>loadCandidates(true));
 if(b.dataset.editUser)return act(b,async()=>{const user=adminUsers.find(u=>u.id===b.dataset.editUser);if(!user)throw new Error('Reload the Admin page and try again.');$('#adminEditor').innerHTML=adminEditor(user);});
 if(b.hasAttribute('data-cancel-edit'))return act(b,async()=>{$('#adminEditor').innerHTML=adminEditor();});
 if(b.hasAttribute('data-home'))return act(b,async()=>{shell();await loadCases();if(cases.length)await loadCase(active?.id&&cases.some(c=>c.id===active.id)?active.id:cases[0].id);});
 if(b.hasAttribute('data-manager'))return act(b,()=>drawManager());
 if(b.id==='refreshManager')return act(b,()=>drawManager());
 if(b.id==='refreshIntake')return act(b,()=>drawJobIntake());
 if(b.id==='refreshPublications')return act(b,()=>drawPublications());
 if(b.dataset.pubDecision)return act(b,async()=>{if(!activePublication)throw new Error('Select a job first.');const [target,decision]=b.dataset.pubDecision.split(':');let reason=null;if(decision==='rejected'){reason=window.prompt('Reason for rejection:')?.trim();if(!reason)return;}await write('pubdecision:'+activePublication.id+':'+target,'/job-publications/'+activePublication.id+'/decision',{target,decision,reason,expected_version:activePublication.version});await drawPublications();await loadPublication(activePublication.id);msg((target==='website'?'Website':'Recruiting')+' decision saved.','success');});
 if(b.id==='refreshWeekly')return act(b,async()=>{const input=$('#weeklyWeek');if(input?.value)weeklyWeek=input.value;await drawWeekly();});
 if(b.id==='exportWeekly')return act(b,async()=>exportWeeklyCsv());
 if(b.id==='refresh')return act(b,async()=>{await loadCases();if(active)await loadCase(active.id);});
 if(b.id==='moreCases')return act(b,()=>loadCases(true));
 if(b.id==='signout')return act(b,async()=>{await call('/auth/logout',{method:'POST',data:{}});pending.clear();login('You are signed out.','success');});
 if(b.dataset.task)return act(b,async()=>{await write('task:'+b.dataset.task,'/cases/'+active.id+'/tasks/'+b.dataset.task,{status:b.dataset.status,expected_version:Number(b.dataset.version)},'PATCH');await drawDetail();msg('Follow-up updated.','success');});
 if(b.dataset.more)return act(b,async()=>{const kind=b.dataset.kind;const result=await call('/cases/'+active.id+'/'+kind+'?limit=50&after='+encodeURIComponent(b.dataset.more));$('#records').insertAdjacentHTML('beforeend',({notes:noteRows,tasks:taskRows,audit:auditRows}[kind])(result.items));b.outerHTML=more(result.next_cursor,kind);});
});
root.addEventListener('input',event=>{
 if(event.target?.id==='adminSearch'){adminQuery=event.target.value;const teamNames=new Map(adminTeams.map(t=>[t.id,t.name]));if($('#adminUserRows'))$('#adminUserRows').innerHTML=adminUserRows(teamNames);}
 if(event.target?.id==='jobSearch'){jobQuery=event.target.value;drawJobList();}
 if(event.target?.id==='candidateSearch'){candidateQuery=event.target.value;drawCandidateList();}
 if(event.target?.id==='goalWeek'){weeklyWeek=event.target.value;}
});
root.addEventListener('change',event=>{
 if(event.target?.id==='adminStatus'){adminStatus=event.target.value;const teamNames=new Map(adminTeams.map(t=>[t.id,t.name]));if($('#adminUserRows'))$('#adminUserRows').innerHTML=adminUserRows(teamNames);}
});
root.addEventListener('submit',event=>{event.preventDefault();const form=event.target,b=form.querySelector('button[type=submit]');
 if(form.id==='adminUserForm')return act(b,async()=>{const role=$('#adminRole').value,team=$('#adminTeam').value;if(['manager','recruiter'].includes(role)&&!team)throw new Error('Choose a team for a recruiter or manager.');await write('adminuser:'+$('#adminEmail').value.trim().toLowerCase(),'/admin/users',{email:$('#adminEmail').value.trim().toLowerCase(),display_name:$('#adminName').value.trim(),role,team_id:team||null,is_active:true});await drawAdmin();msg('User provisioned. They can sign in with the approved Medlivo Google account.','success');});
 if(form.id==='adminEditForm')return act(b,async()=>{const id=form.dataset.userId,role=$('#editRole').value,team=$('#editTeam').value,is_active=$('#editActive').value==='true';if(['manager','recruiter'].includes(role)&&!team)throw new Error('Choose a team for a recruiter or manager.');await write('adminedit:'+id,'/admin/users/'+id,{display_name:$('#editName').value.trim(),role,team_id:team||null,is_active},'PATCH');await drawAdmin(id);msg('User access settings updated and recorded in admin activity.','success');});
 if(form.id==='intakeUploadForm')return act(b,async()=>{const result=await uploadXlsx(form);activeIntake=result;await drawJobIntake();await loadIntakeBatch(result.id);msg('Spreadsheet processed. Review the flagged rows before approval.','success');});
 if(form.id==='weeklyGoalForm')return act(b,async()=>{weeklyWeek=$('#goalWeek').value;if(new Date(weeklyWeek+'T12:00:00').getDay()!==1)throw new Error('Choose a Monday as the week starting date.');await write('weeklygoal:'+session.member.id+':'+weeklyWeek,'/recruiters/'+session.member.id+'/weekly-goals',{week_start:weeklyWeek,submissions_target:Number($('#goalSubmissions').value),interviews_target:Number($('#goalInterviews').value),closures_target:Number($('#goalClosures').value),priority_jobs_target:Number($('#goalPriorityJobs').value),notes:$('#goalNotes').value.trim()||null},'PUT');await drawWeekly();msg('Weekly goals saved. Actual results will update from recruiting activity.','success');});
 if(!active)return;
 if(form.id==='noteForm')act(b,async()=>{await write('note:'+active.id,'/cases/'+active.id+'/notes',{body:$('#note').value});await drawDetail();msg('Note saved to the shared workspace.','success');});
 if(form.id==='taskForm')act(b,async()=>{const due=new Date($('#taskDue').value);if(Number.isNaN(due.getTime()))throw new Error('Choose a valid date and time.');await write('tasknew:'+active.id,'/cases/'+active.id+'/tasks',{title:$('#taskTitle').value,due_at:due.toISOString()});await drawDetail();msg('Follow-up saved. No notification was sent.','success');});
 if(form.id==='ownerForm')act(b,async()=>{await write('owner:'+active.id,'/cases/'+active.id+'/reassign',{owner_user_id:$('#owner').value,reason:$('#reason').value,expected_version:active.version});await loadCases();await loadCase(active.id);msg('Ownership updated and the reason recorded.','success');});
});
async function boot(){
 if(!window.TEAM_ENABLED){login();return;}
 const error=new URLSearchParams(location.search).get('error');
 if(error){history.replaceState(null,'','/team');login(error==='access'?'Your Google account is not enabled for this workspace. Please contact your administrator.':'Sign-in could not be completed. Please start again.');return;}
 try{session=await call('/session');shell();await loadCases();if(cases.length)await loadCase(cases[0].id);}
 catch(error){if(!session)login(error.message);else msg(error.message);}
}
boot();
})();`;
export function renderTeam(enabled){
 const script='window.TEAM_ENABLED='+JSON.stringify(Boolean(enabled))+';\n'+SCRIPT;
 const digest=v=>"'sha256-"+createHash('sha256').update(v).digest('base64')+"'";
 const csp="default-src 'none'; script-src "+digest(script)+"; style-src "+digest(CSS)+"; connect-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'";
 return new Response('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Medlivo Recruit AI | Team workspace</title><style>'+CSS+'</style></head><body><a class="skip" href="#main">Skip to workspace</a><div id="app"><p class="loading">Opening your team workspace…</p></div><noscript>This workspace needs JavaScript for secure team actions. Please enable JavaScript and reload.</noscript><script>'+script+'</script></body></html>',
 {status:200,headers:securityHeaders({'Content-Type':'text/html; charset=utf-8','Content-Security-Policy':csp})});
}
