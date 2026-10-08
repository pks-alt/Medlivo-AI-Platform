#!/usr/bin/env python3
import argparse, json, sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def base_url(value):
    parsed=urlparse(value)
    if parsed.scheme!="https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("staging URLs must be absolute HTTPS origins without credentials/query/fragment")
    return value.rstrip("/")

def fetch(url, token=None):
    headers={"Accept":"application/json","User-Agent":"medlivo-phase3-staging-acceptance/1"}
    if token:
        headers["Authorization"]="Bearer "+token
    req=Request(url,headers=headers,method="GET")
    try:
        with urlopen(req,timeout=15) as r:
            return r.status, dict(r.headers.items()), r.read(65536)
    except HTTPError as e:
        return e.code, dict(e.headers.items()), e.read(65536)
    except URLError as e:
        raise RuntimeError("staging endpoint is unreachable") from e

def parse_json(body):
    try:
        return json.loads(body.decode("utf-8"))
    except Exception as e:
        raise AssertionError("expected JSON response") from e

def run(web_url, api_url, token):
    checks=[]
    def check(name, ok, detail):
        checks.append({"name":name,"status":"pass" if ok else "fail","detail":detail})
        if not ok:
            raise AssertionError(name+": "+detail)

    status,headers,body=fetch(web_url+"/team")
    check("web_team_reachable",status==200,f"HTTP {status}")
    cc=headers.get("Cache-Control","").lower()
    check("web_no_store","no-store" in cc,f"Cache-Control={headers.get('Cache-Control','')}")
    text=body.decode("utf-8","replace")
    check("web_team_surface","medlivo" in text.lower() and "team" in text.lower(),"team surface rendered")

    status,_,body=fetch(api_url+"/health",token)
    data=parse_json(body)
    check("api_health_reachable",status==200,f"HTTP {status}")
    check("api_health_enabled",data.get("workspace_enabled") is True,"workspace_enabled must be true")

    status,_,body=fetch(api_url+"/ready",token)
    ready=parse_json(body)
    check("api_ready",status==200 and ready.get("ok") is True,f"HTTP {status}")
    check("api_database_reachable",ready.get("database_checked") is True and ready.get("database_reachable") is True,"database readiness failed")

    status,_,_=fetch(api_url+"/api/v1/team/me",None)
    check("private_api_rejects_missing_user_token",status in {401,403},f"HTTP {status}")

    return {"mode":"read_only_phase3_acceptance","mutations_performed":False,"jobdiva_write_authorized":False,"checks":checks}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--web-url",required=True)
    p.add_argument("--api-url",required=True)
    p.add_argument("--api-token",default="")
    p.add_argument("--output")
    args=p.parse_args()
    result=run(base_url(args.web_url),base_url(args.api_url),args.api_token or None)
    rendered=json.dumps(result,indent=2,sort_keys=True)
    if args.output:
        open(args.output,"w",encoding="utf-8").write(rendered+"\n")
    print(rendered)

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"mode":"read_only_phase3_acceptance","mutations_performed":False,"status":"failed","detail":str(exc)}),file=sys.stderr)
        raise
