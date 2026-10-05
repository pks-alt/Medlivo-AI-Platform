const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const source = fs.readFileSync(path.join(__dirname, "../lib/api.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  reportDiagnostics: true,
});
assert.equal((compiled.diagnostics || []).length, 0);

function loadApi(env, fetchMock) {
  const exports = {};
  // Next.js enforces server-only at build time. Stub just that marker for these
  // isolated unit tests; no real metadata or API calls are made.
  new Function("require", "exports", "process", "fetch", compiled.outputText)(
    (name) => { assert.equal(name, "server-only"); return {}; },
    exports, { env }, fetchMock
  );
  return exports;
}

const cloudEnv = {
  K_SERVICE: "medlivo-recruit-web",
  API_URL: "https://medlivo-ai-api-test.us-west1.run.app",
  API_AUTH_AUDIENCE: "https://medlivo-ai-api-test-uw.a.run.app",
  NEXT_PUBLIC_API_URL: "http://wrong-build-time-address:8080",
};
const fakeToken = "fake.header.signature";

for (const [fn, endpoint, result] of [
  ["getJobs", "/api/v1/jobs", [{ id: "mock-job" }]],
  ["getDashboard", "/api/v1/dashboard", { submission_ready: 3 }],
]) {
  test(`${fn} obtains a service identity token and authenticates only to the API`, async () => {
    const calls = [];
    const api = loadApi(cloudEnv, async (url, options) => {
      calls.push({ url: String(url), options });
      if (calls.length === 1) {
        const metadata = new URL(url);
        assert.equal(metadata.hostname, "metadata.google.internal");
        assert.equal(metadata.searchParams.get("audience"), cloudEnv.API_AUTH_AUDIENCE);
        assert.equal(options.headers["Metadata-Flavor"], "Google");
        assert.equal(options.redirect, "error");
        assert.equal(options.cache, "no-store");
        return new Response(fakeToken);
      }
      assert.equal(String(url), `${cloudEnv.API_URL}${endpoint}`);
      assert.equal(options.headers.get("X-Serverless-Authorization"), `Bearer ${fakeToken}`);
      assert.equal(options.headers.get("Authorization"), null);
      assert.equal(options.redirect, "error");
      assert.equal(options.cache, "no-store");
      return Response.json(result);
    });
    assert.deepEqual(await api[fn](), result);
    assert.equal(calls.length, 2);
  });
}

test("local development uses localhost without metadata or identity headers", async () => {
  let count = 0;
  const api = loadApi({}, async (url, options) => {
    count++;
    assert.equal(url, "http://localhost:8080/api/v1/jobs");
    assert.equal(options.headers.get("X-Serverless-Authorization"), null);
    return Response.json([]);
  });
  assert.deepEqual(await api.getJobs(), []);
  assert.equal(count, 1);
});

test("metadata denial fails closed without an unauthenticated API fallback", async () => {
  let count = 0;
  const api = loadApi(cloudEnv, async () => { count++; return new Response("private body", { status: 403 }); });
  await assert.rejects(api.getJobs(), /identity token request failed \(HTTP 403\)/);
  assert.equal(count, 1);
});

test("empty identity token fails before any API request", async () => {
  let count = 0;
  const api = loadApi(cloudEnv, async () => { count++; return new Response("  "); });
  await assert.rejects(api.getJobs(), /empty or invalid/);
  assert.equal(count, 1);
});

test("API failure reports status without exposing the token or response body", async () => {
  let count = 0;
  const api = loadApi(cloudEnv, async () => ++count === 1
    ? new Response(fakeToken)
    : new Response("private candidate details", { status: 403 }));
  await assert.rejects(api.getJobs(), (err) => {
    assert.equal(err.message, "Failed to load jobs (API HTTP 403)");
    assert.ok(!err.message.includes(fakeToken));
    assert.ok(!err.message.includes("private candidate"));
    return true;
  });
});

test("Cloud Run rejects non-Cloud-Run or non-HTTPS API destinations", async () => {
  for (const bad of ["http://localhost:8080", "https://other.example", "https://api.run.app/path"]) {
    const api = loadApi({ ...cloudEnv, API_URL: bad }, async () => assert.fail("must not fetch"));
    await assert.rejects(api.getJobs(), /HTTPS root URL/);
  }
});

test("Cloud Run metadata network errors do not cause an unauthenticated fallback", async () => {
  let count = 0;
  const api = loadApi(cloudEnv, async () => { count++; throw new Error("network unavailable"); });
  await assert.rejects(api.getJobs(), /network unavailable/);
  assert.equal(count, 1);
});
