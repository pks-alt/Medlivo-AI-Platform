"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";
import {useEffect,useMemo,useState,type ReactNode} from "react";

type Me={
  display_name?:string;
  role?:string;
  business_role?:string;
  system_admin?:boolean;
};

async function loadMe(){
  const r=await fetch("/api/team/me",{cache:"no-store",credentials:"same-origin"});
  if(!r.ok)throw new Error("Workspace identity unavailable");
  return r.json();
}

export default function WorkspaceShell({children}:{children:ReactNode}){
  const pathname=usePathname();
  const[me,setMe]=useState<Me|null>(null);
  useEffect(()=>{loadMe().then(setMe).catch(()=>setMe(null))},[pathname]);

  const items=useMemo(()=>{
    const base=[
      {href:"/",label:"Today",show:true},
      {href:"/team",label:"My Work",show:true},
      {href:"/jobs",label:"Jobs",show:true},
      {href:"/candidates",label:"Candidates",show:true},
      {href:"/weekly",label:"Weekly",show:true},
      {href:"/funnel",label:"Submission to Start",show:true},
      {href:"/manager",label:"Manager",show:me?.business_role!=="recruiter"},
      {href:"/executive",label:"Executive",show:me?.business_role==="executive"},
      {href:"/admin",label:"Admin",show:Boolean(me?.system_admin||me?.role==="admin")},
    ];
    return base.filter(x=>x.show);
  },[me]);

  const active=(href:string)=>{
    if(href==="/")return pathname==="/";
    if(href==="/admin")return pathname.startsWith("/admin");
    if(href==="/executive")return pathname.startsWith("/executive");
    if(href==="/funnel")return pathname.startsWith("/funnel");
    if(href==="/jobs")return pathname.startsWith("/jobs");
    if(href==="/candidates")return pathname.startsWith("/candidates");
    if(href==="/weekly")return pathname.startsWith("/weekly");
    if(href==="/manager")return pathname.startsWith("/manager");
    return pathname===href;
  };

  return <div className="appShell">
    <aside className="appSidebar">
      <div className="appBrand"><b>medlivo</b><span>RECRUIT AI</span></div>
      <nav aria-label="Recruit AI navigation">
        <small>WORKSPACE</small>
        {items.map(item=><Link key={item.href} href={item.href} className={active(item.href)?"active":""}>{item.label}</Link>)}
      </nav>
      <div className="appSidebarFoot">
        <span className="appStatusDot"/> <b>Private workspace</b>
        <small>{me?.display_name||"Medlivo team"}</small>
      </div>
    </aside>
    <div className="appCanvas">{children}</div>
  </div>;
}
