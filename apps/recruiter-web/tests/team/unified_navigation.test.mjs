import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";

test("Weekly is exposed through the unified app shell", async () => {
  const shell = await readFile(new URL("../../app/components/WorkspaceShell.tsx", import.meta.url), "utf8");
  assert.match(shell, /href:"\/weekly",label:"Weekly",show:true/);
  assert.match(shell, /pathname\.startsWith\("\/weekly"\)/);
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
