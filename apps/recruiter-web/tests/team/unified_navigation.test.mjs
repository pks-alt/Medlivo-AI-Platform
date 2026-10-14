import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";

test("My Week is exposed through the finalized recruiter workspace shell", async () => {
  const shell = await readFile(new URL("../../app/components/WorkspaceShell.tsx", import.meta.url), "utf8");
  assert.match(shell, /href:"\/weekly",label:"My Week"/);
  assert.match(shell, /return base!=="\/"&&pathname\.startsWith\(base\)/);
});

test("Weekly has a first-class application route", async () => {
  const page = await readFile(new URL("../../app/weekly/page.tsx", import.meta.url), "utf8");
  assert.match(page, /Monday Goal Meeting/);
  assert.match(page, /Friday Status Meeting/);
  assert.match(page, /Commit Monday Goals/);
});

test("Legacy My Work routes Weekly into the unified section", async () => {
  const ui = await readFile(new URL("../../lib/team/ui.mjs", import.meta.url), "utf8");
  assert.match(ui, /href="\/weekly">Weekly<\/a>/);
  assert.doesNotMatch(ui, /data-weekly>/);
});


test("Friday Weekly report keeps the Excel export", async () => {
  const page = await readFile(new URL("../../app/weekly/page.tsx", import.meta.url), "utf8");
  assert.match(page, /Download Excel \(\.xlsx\)/);
  assert.match(page, /XLSX\.writeFile/);
  assert.match(page, /Medlivo_Weekly_Status_/);
});


test("Submission to Start stays a delivery pipeline, not a count-only funnel", async () => {
  const page = await readFile(new URL("../../app/funnel/page.tsx", import.meta.url), "utf8");
  assert.match(page, /Recruiting Delivery Pipeline/);
  assert.match(page, /SUBMISSION → INTERVIEW/);
  assert.match(page, /Starting Soon/);
  assert.match(page, /At Risk/);
  assert.match(page, /Candidate 360/);
  assert.match(page, /Job 360/);
  assert.match(page, /This does not automatically mean there was no recruiting activity/);
});


test("Manager and Weekly calculate Monday without UTC date rollover", async () => {
  const manager = await readFile(new URL("../../app/manager/page.tsx", import.meta.url), "utf8");
  const weekly = await readFile(new URL("../../app/weekly/page.tsx", import.meta.url), "utf8");
  for (const source of [manager, weekly]) {
    assert.match(source, /getFullYear\(\)/);
    assert.match(source, /getMonth\(\)\+1/);
  }
  assert.doesNotMatch(manager, /return d\.toISOString\(\)\.slice\(0,10\)/);
  assert.doesNotMatch(weekly, /return d\.toISOString\(\)\.slice\(0,10\)/);
});

test("Manager and Admin preserve the page when secondary data fails", async () => {
  const manager = await readFile(new URL("../../app/manager/page.tsx", import.meta.url), "utf8");
  const admin = await readFile(new URL("../../app/admin/page.tsx", import.meta.url), "utf8");
  assert.match(manager, /optional\("manager\/weekly-review/);
  assert.match(manager, /Some manager data is temporarily unavailable/);
  assert.match(admin, /Promise\.all\(specs\.map/);
  assert.match(admin, /Some administration data is temporarily unavailable/);
  assert.match(admin, /if\(!me\.system_admin\)/);
});


test("Admin operations read path is guarded by System Admin, not legacy admin role", async () => {
  const store = await readFile(new URL("../../../../services/team-workspace/workspace_api/store.py", import.meta.url), "utf8");
  const start = store.indexOf("def admin_operations_summary");
  const end = store.indexOf("\n    def ", start + 10);
  const block = store.slice(start, end > start ? end : undefined);
  assert.match(block, /if not principal\["system_admin"\]/);
  assert.doesNotMatch(block, /if principal\["role"\] != "admin"/);
});


test("Executive is a first-class command center, not margin-only", async () => {
  const shell = await readFile(new URL("../../app/components/WorkspaceShell.tsx", import.meta.url), "utf8");
  const page = await readFile(new URL("../../app/executive/page.tsx", import.meta.url), "utf8");
  assert.match(shell, /href:"\/executive",label:"Executive"/);
  assert.match(page, /Executive command center/);
  assert.match(page, /Are we producing, converting, and protecting margin\?/);
  assert.match(page, /DELIVERY RISK/);
  assert.match(page, /WEEKLY EXECUTION/);
  assert.match(page, /DIVISION PERFORMANCE/);
  assert.match(page, /COMMERCIAL CONTROL/);
  assert.match(page, /href="\/executive\/margin"/);
});


test("Job Intake exposes governed AI JD review instead of dead-end review rows", async () => {
  const ui = await readFile(new URL("../../lib/team/ui.mjs", import.meta.url), "utf8");
  assert.match(ui, /AI Draft Needed/);
  assert.match(ui, /Generate AI Draft/);
  assert.match(ui, /Review and edit JD/);
  assert.match(ui, /Accept Reviewed JD/);
  assert.match(ui, /Human Approved AI Draft provenance/);
  assert.match(ui, /data-intake-item-review/);
  assert.match(ui, /\/ai-draft/);
});


test("Job Intake is visible from the global application navigation", async () => {
  const shell = await readFile(new URL("../../app/components/WorkspaceShell.tsx", import.meta.url), "utf8");
  const ui = await readFile(new URL("../../lib/team/ui.mjs", import.meta.url), "utf8");
  assert.match(shell, /href:"\/team\?section=intake",label:"Job Intake"/);
  assert.match(shell, /section==="intake"/);
  assert.match(shell, /new URLSearchParams\(window\.location\.search\)/);
  assert.match(ui, /section==='intake'&&managed\(\)/);
  assert.match(ui, /await drawJobIntake\(\);return;/);
});


test("Job Intake approval hands off visibly to Job Approval", async () => {
  const shell = await readFile(new URL("../../app/components/WorkspaceShell.tsx", import.meta.url), "utf8");
  const ui = await readFile(new URL("../../lib/team/ui.mjs", import.meta.url), "utf8");
  assert.match(shell, /href:"\/team\?section=approvals",label:"Job Approval"/);
  assert.match(ui, /Open Job Approval/);
  assert.match(ui, /data-open-intake-publication/);
  assert.match(ui, /HUMAN APPROVED AI DRAFT/);
  assert.match(ui, /section==='approvals'&&managed\(\)/);
  assert.match(ui, /Reviewed JD accepted and sent to Job Approval/);
});


test("Job Content Standards has a dedicated management route", async () => {
  const shell = await readFile(new URL("../../app/components/WorkspaceShell.tsx", import.meta.url), "utf8");
  const ui = await readFile(new URL("../../lib/team/ui.mjs", import.meta.url), "utf8");
  assert.match(shell, /section=standards/);
  assert.match(shell, /Job Content Standards/);
  assert.match(ui, /One Medlivo standard for every job source/);
  assert.match(ui, /Create a standard version/);
  assert.match(ui, /Website-style preview/);
  assert.match(ui, /section==='standards'&&managed\(\)/);
});


test("Job Intake prepares all JDs from approved Medlivo standards", async () => {
  const ui = await readFile(new URL("../../lib/team/ui.mjs", import.meta.url), "utf8");
  assert.match(ui, /Prepare All JDs/);
  assert.match(ui, /prepare-standards/);
  assert.match(ui, /Medlivo Standard Ready/);
  assert.match(ui, /need a Job Content Standard/);
});


test("Recruiter workspace uses the finalized nine-destination navigation", async () => {
  const shell = await readFile(new URL("../../app/components/WorkspaceShell.tsx", import.meta.url), "utf8");
  assert.match(shell, /href:"\/",label:"Today"/);
  assert.match(shell, /href:"\/jobs",label:"Jobs"/);
  assert.match(shell, /href:"\/candidates",label:"Candidates"/);
  assert.match(shell, /href:"\/matching",label:"Matching"/);
  assert.match(shell, /href:"\/conversations",label:"Conversations"/);
  assert.match(shell, /href:"\/interviews",label:"Interviews"/);
  assert.match(shell, /href:"\/pay-gm",label:"Pay & GM"/);
  assert.match(shell, /href:"\/funnel",label:"Submissions"/);
  assert.match(shell, /href:"\/weekly",label:"My Week"/);
});

test("Recruiter and management navigation are separate workspace models", async () => {
  const shell = await readFile(new URL("../../app/components/WorkspaceShell.tsx", import.meta.url), "utf8");
  assert.match(shell, /if\(recruiter\)/);
  assert.match(shell, /RECRUITER WORKSPACE/);
  assert.match(shell, /MANAGEMENT/);
  assert.match(shell, /Recruiter Workspace/);
  assert.match(shell, /Delivery Manager Workspace/);
  assert.match(shell, /Executive Workspace/);
});

test("New recruiter destinations are first-class routes", async () => {
  for (const file of ["matching/page.tsx","conversations/page.tsx","interviews/page.tsx","pay-gm/page.tsx"]) {
    const source = await readFile(new URL("../../app/"+file, import.meta.url), "utf8");
    assert.ok(source.length > 100);
  }
});

test("Conversations uses persisted outreach APIs with guarded Gmail pilot delivery", async () => {
  const page = await readFile(new URL("../../app/conversations/page.tsx", import.meta.url), "utf8");
  assert.match(page, /AI-assisted Email and Text\/SMS drafting/);
  assert.match(page, /Text \/ SMS/);
  assert.match(page, /api\("outreach-drafts"/);
  assert.match(page, /Generate AI Draft/);
  assert.match(page, /Connect Gmail/i);
  assert.match(page, /deliver-gmail/);
  assert.match(page, /Send Approved Email/i);
  assert.match(page, /gmail\/messages/);
  assert.match(page, /RECENT GMAIL REPLIES/);
  assert.match(page, /FOLLOW-UP PLANS/);
  assert.match(page, /Start 3 \/ 7 \/ 14 Day Follow-up Plan/);
  assert.match(page, /Stop Email \/ Opt Out/);
  assert.match(page, /Prepare Due Follow-ups/);
  assert.match(page, /Nothing sends automatically/);
  assert.match(page, /X-CSRF-Token/);
  assert.match(page, /policy_version/);
  assert.doesNotMatch(page, /send-email|send-sms|\/send"/);
});

test("Today consumes protected action windows and preserves assignment", async () => {
  const page = await readFile(new URL("../../app/page.tsx", import.meta.url), "utf8");
  const today = await readFile(new URL("../../app/components/RecruiterToday.tsx", import.meta.url), "utf8");
  assert.match(page, /recruiter\/protected-actions/);
  assert.match(today, /protected-action/);
  assert.match(today, /AVAILABLE FOR SUPPORT/);
  assert.match(today, /assignment stays unchanged/);
  assert.match(today, /8 AM–5 PM Pacific/);
  assert.match(today, /remaining_business_minutes/);
});

test("Candidate 360 surfaces active relationship continuity", async () => {
  const page = await readFile(new URL("../../app/candidates/[candidateId]/page.tsx", import.meta.url), "utf8");
  assert.match(page, /\/relationship/);
  assert.match(page, /Active with you/);
  assert.match(page, /Active with /);
  assert.match(page, /No active relationship/);
  assert.match(page, /Unanswered outreach, profile views and internal notes do not establish a relationship/);
});


test("Final Today uses real protected-action and funnel APIs", async () => {
  const page = await readFile(new URL("../../app/components/RecruiterToday.tsx", import.meta.url), "utf8");
  assert.match(page, /recruiter\/protected-actions\?limit=50/);
  assert.match(page, /funnel\?limit=200/);
  assert.match(page, /protected-action/);
  assert.match(page, /action_type:"working"/);
  assert.match(page, /TIME-SENSITIVE ASSIGNED WORK/);
  assert.match(page, /REHABILITATION OPPORTUNITIES YOU CAN HELP WITH/);
});

test("Conversations uses persisted AI outreach draft workflow", async () => {
  const page = await readFile(new URL("../../app/conversations/page.tsx", import.meta.url), "utf8");
  assert.match(page, /outreach-drafts/);
  assert.match(page, /Generate AI Draft/);
  assert.match(page, /model_provider/);
  assert.match(page, /policy_version/);
  assert.match(page, /Approve Draft/);
  assert.match(page, /Gmail pilot/i);
  assert.match(page, /Connect Gmail before sending/i);
  assert.match(page, /candidates\/.*\/relationship/);
});

test("Candidate 360 exposes operational relationship state and meaningful activity", async () => {
  const page = await readFile(new URL("../../app/candidates/\[candidateId\]/page.tsx", import.meta.url), "utf8");
  assert.match(page, /candidates\/.*\/relationship/);
  assert.match(page, /Active with you/);
  assert.match(page, /Coordinate before outreach/);
  assert.match(page, /RELATIONSHIP ACTIVITY/);
  assert.match(page, /Meaningful/);
});


test("Recruiter Jobs separates Priority 1 accountability from Priority 2 opportunity", async () => {
  const page = await readFile(new URL("../../app/jobs/page.tsx", import.meta.url), "utf8");
  assert.match(page, /My Jobs · Priority 1/);
  assert.match(page, /Division Opportunities · Priority 2/);
  assert.match(page, /priority_1/);
  assert.match(page, /priority_2/);
  assert.match(page, /Primary assignment remains with/);
  assert.match(page, /No Priority 2 opportunities currently meet the evidence-backed visibility rule/);
});


test("System Admin recruiter review replaces the retired one-page preview", async () => {
  const admin = await readFile(new URL("../../app/admin/page.tsx", import.meta.url), "utf8");
  const preview = await readFile(new URL("../../app/recruiter-preview/page.tsx", import.meta.url), "utf8");
  assert.match(admin, /href="\/recruiter-review">Recruiter UX Review/);
  assert.match(preview, /router\.replace\("\/recruiter-review"\)/);
  assert.doesNotMatch(preview, /RecruiterToday|previewData/);
});


test("System Admin recruiter review covers the full finalized recruiter workspace", async () => {
  const review = await readFile(new URL("../../app/recruiter-review/page.tsx", import.meta.url), "utf8");
  const oldPreview = await readFile(new URL("../../app/recruiter-preview/page.tsx", import.meta.url), "utf8");
  const admin = await readFile(new URL("../../app/admin/page.tsx", import.meta.url), "utf8");
  for (const label of ["Today","Jobs","Candidates","Matching","Conversations","Interviews","Pay & GM","Submissions","My Week"]) {
    assert.match(review, new RegExp(label.replace("&","\\&")));
  }
  assert.match(review, /PHASE 2 · PR 116–120/);
  assert.match(review, /Gmail pilot/);
  assert.match(review, /3 \/ 7 \/ 14 follow-up/);
  assert.match(review, /Due preparation worker/);
  assert.match(review, /Protected first-action window/);
  assert.match(review, /Priority 2/);
  assert.match(review, /System Administrator access required/);
  assert.match(oldPreview, /router\.replace\("\/recruiter-review"\)/);
  assert.match(admin, /href="\/recruiter-review">Recruiter UX Review/);
});


test("System Admin shell exposes recruiter test mode without replacing native role", async () => {
  const shell = await readFile(new URL("../../app/components/WorkspaceShell.tsx", import.meta.url), "utf8");
  assert.match(shell, /Enter Recruiter Test Mode/);
  assert.match(shell, /Exit Recruiter Test Mode/);
  assert.match(shell, /\/api\/team\/workspace-mode/);
  assert.match(shell, /workspace_mode==="recruiter"/);
});
