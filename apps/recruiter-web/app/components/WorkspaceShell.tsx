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
  const[section,setSection]=useState("");
  const[me,setMe]=useState<Me|null>(null);
  useEffect(()=>{loadMe().then(setMe).catch(()=>setMe(null));setSection(new URLSearchParams(window.location.search).get("section")||"")},[pathname]);

  const groups=useMemo(()=>{
    const recruiter=me?.business_role==="recruiter";
    return [
      {label:"DAILY WORK",items:[
        {href:"/",label:"Today",show:true},
        {href:"/distribution",label:"Job Distribution",show:!recruiter},
        {href:"/jobs",label:"Jobs",show:true},
        {href:"/candidates",label:"Candidates",show:true},
        {href:"/funnel",label:"Submission to Start",show:true},
      ]},
      {label:"OPERATING RHYTHM",items:[
        {href:"/weekly",label:"Weekly",show:true},
        {href:"/manager",label:"Team Overview",show:!recruiter},
        {href:"/executive",label:"Executive",show:me?.business_role==="executive"},
      ]},
      {label:"CONTROL",items:[
        {href:"/team?section=intake",label:"Job Intake",show:!recruiter},
        {href:"/team?section=standards",label:"Job Content Standards",show:!recruiter},
        {href:"/team?section=approvals",label:"Job Approval",show:!recruiter},
        {href:"/admin",label:"Admin & Access",show:Boolean(me?.system_admin||me?.role==="admin")},
      ]},
    ].map(group=>({...group,items:group.items.filter(x=>x.show)})).filter(group=>group.items.length);
  },[me]);

  const active=(href:string)=>{
    if(href==="/")return pathname==="/";
    if(href==="/team?section=intake")return pathname==="/team"&&section==="intake";
    if(href==="/team?section=approvals")return pathname==="/team"&&section==="approvals";
    if(href==="/team?section=standards")return pathname==="/team"&&section==="standards";
    if(href==="/admin")return pathname.startsWith("/admin");
    if(href==="/executive")return pathname.startsWith("/executive");
    if(href==="/funnel")return pathname.startsWith("/funnel");
    if(href==="/jobs")return pathname.startsWith("/jobs");
    if(href==="/candidates")return pathname.startsWith("/candidates");
    if(href==="/weekly")return pathname.startsWith("/weekly");
    if(href==="/manager")return pathname.startsWith("/manager");
    if(href==="/distribution")return pathname.startsWith("/distribution");
    return pathname===href;
  };

  return <div className="appShell">
    <aside className="appSidebar">
      <div className="appBrand">
        <div className="appBrandMark">M</div>
        <div><b>medlivo</b><span>RECRUIT AI</span><small>Healthcare Staffing Intelligence</small></div>
      </div>
      <nav aria-label="Recruit AI navigation">
        {groups.map(group=><div className="appNavGroup" key={group.label}>
          <small>{group.label}</small>
          {group.items.map(item=><Link key={item.href} href={item.href} className={active(item.href)?"active":""}>{item.label}</Link>)}
        </div>)}
      </nav>
      <div className="appSidebarFoot">
        <div className="appUserCard">
          <div className="appUserAvatar">{(me?.display_name||"M").slice(0,1).toUpperCase()}</div>
          <div><b>{me?.display_name||"Medlivo team"}</b><small>{String(me?.business_role||me?.role||"user").replaceAll("_"," ")}</small></div>
        </div>
        <div className="appEnv"><span className="appStatusDot"/><b>Secure staging</b></div>
        <em>Block 1 · Intake → Distribution → Recruiter Work</em>
      </div>
    </aside>
    <div className="appCanvas">{children}</div>
  </div>;
}
