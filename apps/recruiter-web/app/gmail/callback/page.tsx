"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
import {useSearchParams} from "next/navigation";

async function session(){
  const r=await fetch("/api/team/session",{cache:"no-store",credentials:"same-origin"});
  const b=await r.json().catch(()=>({}));
  if(!r.ok||!b.csrf)throw new Error("Session security context unavailable");
  return b;
}

export default function GmailCallbackPage(){
  const params=useSearchParams();
  const[status,setStatus]=useState("Completing Gmail connection…");
  const[error,setError]=useState("");

  useEffect(()=>{
    const code=params.get("code")||"";
    const state=params.get("state")||"";
    const oauthError=params.get("error")||"";
    if(oauthError){setError("Google authorization was cancelled or denied.");setStatus("");return}
    if(!code||!state){setError("Gmail authorization response is incomplete.");setStatus("");return}
    (async()=>{
      try{
        const s=await session();
        const r=await fetch("/api/team/gmail/oauth/complete",{
          method:"POST",
          credentials:"same-origin",
          headers:{
            "Content-Type":"application/json",
            "X-CSRF-Token":s.csrf,
            "Idempotency-Key":crypto.randomUUID(),
          },
          body:JSON.stringify({code,state}),
        });
        const b=await r.json().catch(()=>({}));
        if(!r.ok)throw new Error(b.detail||"Gmail connection could not be completed");
        setStatus("Gmail connected successfully. You can return to Conversations.");
      }catch(e:any){
        setError(e.message||"Gmail connection could not be completed");
        setStatus("");
      }
    })();
  },[params]);

  return <main className="page">
    <section className="panelBox" style={{maxWidth:720,margin:"40px auto"}}>
      <small>GMAIL PILOT</small>
      <h1>Connect Gmail</h1>
      {status&&<div className="goodState">{status}</div>}
      {error&&<div className="adminError"><b>Connection not completed</b><span>{error}</span></div>}
      <p>This connection is for your own Medlivo Gmail account and is used only for approved recruiting outreach and reply synchronization.</p>
      <Link className="button primary" href="/conversations">Back to Conversations</Link>
    </section>
  </main>;
}
