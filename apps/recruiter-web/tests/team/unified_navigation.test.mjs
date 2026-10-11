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
