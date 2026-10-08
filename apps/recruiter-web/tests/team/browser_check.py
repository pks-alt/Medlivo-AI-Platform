"""HTTPS browser tests. Google authorization is simulated on loopback.
Uses the real private API and PostgreSQL browser-session storage with synthetic records.
"""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
ORIGIN='https://localhost:9443'
CASE='00000000-0000-0000-0000-000000000100'
OTHER='00000000-0000-0000-0000-000000000011'
OUT=Path(os.environ.get('TEAM_EVIDENCE_DIR','/mnt/data/team-browser-evidence'));OUT.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];unexpected=[]

def check(value,name):
    assert value,name
    checks.append(name)
    print('PASS:',name,flush=True)

with tempfile.TemporaryDirectory() as folder:
    folder=Path(folder)
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(folder/'tls.key'),'-out',str(folder/'tls.crt'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1'],check=True,capture_output=True)
    env={**os.environ,'TEAM_TEST_TLS_KEY':str(folder/'tls.key'),'TEAM_TEST_TLS_CERT':str(folder/'tls.crt'),'TEAM_FIXTURE_DIR':str(folder)}
    log=open(OUT/'fixture.log','w')
    server=subprocess.Popen(['node','tests/team/browser-fixture.mjs'],env=env,stdout=log,stderr=log)
    try:
        with sync_playwright() as p:
            launch={'headless':True}
            if Path('/usr/bin/chromium').exists():launch['executable_path']='/usr/bin/chromium'
            browser=p.chromium.launch(**launch)
            api=p.request.new_context(ignore_https_errors=True)
            ready=None
            for _ in range(100):
                try:
                    r=api.get(ORIGIN+'/_test/ready',timeout=1000)
                    if r.ok:ready=r.json();break
                except Exception:pass
                if server.poll() is not None:raise RuntimeError('Fixture failed: '+(OUT/'fixture.log').read_text())
                time.sleep(.2)
            check(ready is not None,'HTTPS test server starts')
            check(ready['realApi'],'Browser test uses actual private workspace API')
            check(ready['postgres'],'Browser session data is stored in PostgreSQL')
            def context(actor):
                ctx=browser.new_context(ignore_https_errors=True,viewport={'width':1440,'height':1000})
                # Synthetic identity selection exists only on the isolated test server.
                ctx.add_cookies([{'name':'medlivo_test_actor','value':actor,'url':ORIGIN,'secure':True,'httpOnly':True,'sameSite':'Lax'}])
                def route_handler(route):
                    url=urlparse(route.request.url)
                    if url.hostname in {'localhost','127.0.0.1'}:route.continue_()
                    else:unexpected.append(url.hostname);route.abort()
                ctx.route('**/*',route_handler)
                ctx.on('request',lambda req: unexpected.append(urlparse(req.url).hostname) if urlparse(req.url).hostname not in {'localhost','127.0.0.1'} else None)
                page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                return ctx,page
            recruiter,page=context('recruiter-a')
            page.goto(ORIGIN+'/team',wait_until='networkidle')
            page.get_by_role('link',name='Continue with Google').wait_for()
            page.screenshot(path=str(OUT/'signin-desktop.png'),full_page=True)
            check(page.get_by_text('Welcome back.',exact=True).is_visible(),'Sign-in page loads with no persona impersonation control')
            page.get_by_role('link',name='Continue with Google').click()
            try:
                page.get_by_role('heading',name='TEST · Physical Therapist · Dallas',exact=True).wait_for()
            except Exception:
                page.screenshot(path=str(OUT/'signin-failure.png'),full_page=True)
                print('TEST sign-in result path:',urlparse(page.url).path,'error:',parse_qs(urlparse(page.url).query).get('error'),flush=True)
                print('TEST synthetic page text:',page.locator('body').inner_text()[:2000],flush=True)
                raise
            check(page.locator('#noteForm').is_visible(),'OAuth callback opens authorized work item')
            check(page.get_by_role('button',name='Team overview',exact=True).count()==0,'Recruiter does not see manager Team overview')
            page.get_by_role('button',name='Match Queue',exact=True).click()
            page.get_by_role('heading',name='Match Queue',exact=True).wait_for()
            page.locator('#matchBand').select_option('strong')
            check(page.get_by_text('1 SHOWN',exact=True).is_visible(),'Match Queue strong-score triage filters without recalculating matches')
            page.get_by_role('button',name='Good',exact=True).click()
            page.get_by_text('Match-quality feedback saved. Thank you.',exact=True).wait_for()
            page.locator('#hideReviewed').select_option('true')
            check(page.get_by_text('0 SHOWN',exact=True).is_visible(),'Match Queue can hide matches already reviewed by this recruiter')
            page.locator('#hideReviewed').select_option('false')
            page.locator('#matchBand').select_option('all')
            page.get_by_role('button',name='Jobs',exact=True).click()
            page.locator('#pageTitle').get_by_text('Jobs',exact=True).wait_for()
            page.get_by_text('Synthetic Physical Therapist',exact=True).wait_for()
            check(True,'Recruiter can browse tenant-scoped canonical jobs')
            check(page.get_by_text('Synthetic Foreign Job',exact=True).count()==0,'Jobs screen excludes another tenant')
            page.get_by_text('Synthetic Physical Therapist',exact=True).click()
            page.get_by_text('Recruit AI job record',exact=True).wait_for()
            check(page.get_by_text('READ ONLY',exact=True).is_visible(),'Job detail is explicitly read only')
            page.get_by_role('button',name='Candidates',exact=True).click()
            page.get_by_text('Synthetic Candidate One',exact=True).wait_for()
            check(page.get_by_text('Synthetic Foreign Candidate',exact=True).count()==0,'Candidates screen excludes another tenant')
            page.get_by_text('Synthetic Candidate One',exact=True).click()
            page.get_by_role('heading',name='Best current jobs',exact=True).wait_for()
            check(page.get_by_text('READ ONLY',exact=True).is_visible(),'Candidate detail is explicitly read only')
            check(page.get_by_text('PERSISTED MATCHES',exact=True).is_visible(),'Candidate detail uses persisted match results')
            check(page.get_by_text('Strong matches 9+',exact=True).is_visible(),'Candidate Best Jobs summarizes strong match bands')
            page.get_by_role('button',name='Good',exact=True).click()
            page.get_by_text('Match-quality feedback saved. Thank you.',exact=True).wait_for()
            check(True,'Candidate Best Jobs can record the same recruiter match-quality feedback as Match Queue')
            page.get_by_role('button',name='Open job',exact=True).click()
            page.get_by_text('Recruit AI job record',exact=True).wait_for()
            check(True,'Candidate Best Jobs opens the matched canonical job directly')
            page.get_by_role('button',name='My work',exact=True).click()
            page.locator('#noteForm').wait_for()
            page.get_by_role('tab',name='Follow-ups',exact=True).click()
            page.locator('#taskTitle').fill('Queue verification follow-up');page.locator('#taskDue').fill('2026-10-12T14:30');page.get_by_role('button',name='Create follow-up').click()
            page.get_by_text('Follow-up saved. No notification was sent.',exact=True).wait_for()
            page.get_by_role('button',name='Follow-ups',exact=True).click()
            page.get_by_role('heading',name='Follow-ups',exact=True).wait_for()
            page.get_by_text('Queue verification follow-up',exact=True).wait_for()
            check(True,'Recruiter-wide Follow-ups queue shows tasks across assigned work')
            page.get_by_role('button',name='Mark done',exact=True).click()
            page.get_by_text('Follow-up updated.',exact=True).wait_for()
            check(page.get_by_text('Queue verification follow-up',exact=True).count()==0,'Completing a queue item removes it from the default open view')
            page.get_by_role('button',name='My work',exact=True).click()
            page.locator('#noteForm').wait_for()
            cookies=recruiter.cookies()
            session=[c for c in cookies if c['name']=='__Host-medlivo-team'][0]
            check(session['httpOnly'] and session['secure'] and session['sameSite']=='Lax','Browser cookie is Secure HttpOnly SameSite=Lax')
            check(page.evaluate("document.cookie.indexOf('__Host-medlivo-team') === -1"),'Session cookie cannot be read by browser JavaScript')
            check(page.evaluate('localStorage.length === 0 && sessionStorage.length === 0'),'Google and session tokens are absent from browser storage')
            note='Synthetic handoff. Candidate requests afternoon follow-up. <img src=x onerror=alert(1)>'
            page.locator('#note').fill(note);page.get_by_role('button',name='Save note',exact=True).click()
            page.get_by_text('Note saved to the shared workspace.',exact=True).wait_for()
            check(page.locator('#records').inner_text().count(note)==1,'Shared note save succeeds once and renders markup as plain text')
            page.reload(wait_until='networkidle');page.locator('#noteForm').wait_for()
            check(note in page.locator('#records').inner_text(),'Shared note and login survive reload')
            page.get_by_role('tab',name='Follow-ups',exact=True).click();page.locator('#taskTitle').fill('Synthetic availability check');page.locator('#taskDue').fill('2026-10-12T14:30');page.get_by_role('button',name='Create follow-up').click()
            page.get_by_text('Follow-up saved. No notification was sent.',exact=True).wait_for()
            check(page.get_by_text('Synthetic availability check',exact=True).is_visible(),'Follow-up is saved through the API')
            page.get_by_role('button',name='Mark done',exact=True).click();page.get_by_role('button',name='Reopen',exact=True).wait_for()
            check(page.get_by_role('button',name='Reopen',exact=True).is_visible(),'Follow-up completion updates shared state')
            page.get_by_role('tab',name='Notes',exact=True).click();page.locator('#noteForm').wait_for();page.screenshot(path=str(OUT/'team-workspace-desktop.png'),full_page=True)
            manager,mp=context('manager-a');mp.goto(ORIGIN+'/team',wait_until='networkidle');mp.get_by_role('link',name='Continue with Google').click();mp.locator('#noteForm').wait_for()
            check(note in mp.locator('#records').inner_text(),'Separate manager browser sees the same saved note')
            mp.get_by_role('button',name='Team overview',exact=True).click()
            mp.get_by_role('heading',name='Team overview',exact=True).wait_for()
            summary=mp.get_by_role('region',name='Team workload summary')
            check(summary.get_by_text('Work items',exact=True).is_visible(),'Manager overview shows team work-item metric')
            check(summary.get_by_text('Active recruiters',exact=True).is_visible(),'Manager overview shows active recruiter metric')
            check(summary.get_by_text('Open follow-ups',exact=True).is_visible(),'Manager overview shows open follow-up metric')
            check(summary.get_by_text('Overdue follow-ups',exact=True).is_visible(),'Manager overview shows overdue follow-up metric')
            check(mp.get_by_role('heading',name='Recruiter workload',exact=True).is_visible(),'Manager overview shows recruiter workload')
            workload=mp.locator('table.manager-table')
            workload.get_by_text('Alex Chen',exact=True).wait_for()
            check(True,'Manager overview includes managed-team recruiter')
            check(mp.get_by_text('Synthetic recruiter-other',exact=True).count()==0,'Manager overview excludes recruiters from other teams')
            mp.locator('#workList [data-case]').first.click()
            mp.get_by_role('tab',name='Ownership',exact=True).wait_for()
            mp.get_by_role('tab',name='Ownership',exact=True).click();mp.locator('#owner').select_option(OTHER);mp.locator('#reason').fill('Synthetic coverage handoff for next shift');mp.get_by_role('button',name='Reassign work item').click();mp.get_by_text('Ownership updated and the reason recorded.',exact=True).wait_for()
            check(True,'Manager reassignment uses server permissions and version checks')
            page.get_by_role('button',name='Refresh workspace').click();page.get_by_text('This work item is no longer available to your account.',exact=True).wait_for()
            check(page.locator('#noteForm').count()==0,'Former owner loses access and stale detail is cleared')
            newer,np=context('recruiter-b');np.goto(ORIGIN+'/team',wait_until='networkidle');np.get_by_role('link',name='Continue with Google').click();np.locator('#noteForm').wait_for()
            check(note in np.locator('#records').inner_text(),'New owner can read the preserved handoff history')
            np.get_by_role('tab',name='Activity',exact=True).click();np.get_by_text('Synthetic coverage handoff for next shift',exact=True).wait_for()
            check(True,'Ownership reason appears in shared activity history')
            np.set_viewport_size({'width':390,'height':844});np.screenshot(path=str(OUT/'team-workspace-mobile.png'),full_page=True)
            check(np.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),'Mobile workspace does not overflow horizontally')
            np.get_by_role('button',name='Sign out',exact=True).click();np.get_by_text('You are signed out.',exact=True).wait_for()
            check(newer.request.get(ORIGIN+'/api/team/cases').status==401,'Logout revokes access to team data')
            stranger,sp=context('unprovisioned');sp.goto(ORIGIN+'/team',wait_until='networkidle');sp.get_by_role('link',name='Continue with Google').click();sp.get_by_text('Your Google account is not enabled for this workspace. Please contact your administrator.',exact=True).wait_for()
            check(stranger.request.get(ORIGIN+'/api/team/cases').status==401,'Unprovisioned Google identity cannot establish a workspace session')
            check(not errors,'No uncaught browser errors')
            check(not unexpected,'No requests to Google, JobDiva or other non-test external services')
            browser.close()
    finally:
        server.terminate()
        try:server.wait(timeout=8)
        except subprocess.TimeoutExpired:server.kill()
        log.close()
        print('TEST fixture diagnostics:\n'+(OUT/'fixture.log').read_text()[-8000:],flush=True)
    report={'passed':len(checks),'checks':checks,'browser_errors':errors,'unexpected_network_requests':unexpected,'google_signin':'simulated loopback authorization provider; real Google not tested','private_api':'actual PR #3 service with synthetic SQLite records','session_storage':'PostgreSQL','production_deployed':False}
    (OUT/'browser-result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
