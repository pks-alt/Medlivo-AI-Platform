"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";
import {useEffect,useMemo,useState,type ReactNode} from "react";

type Me={
  display_name?:string;
  role?:string;
  business_role?:string;
  system_admin?:boolean;
  division?:string;
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

  const recruiter=me?.business_role==="recruiter";
  const workspaceLabel=recruiter?"Recruiter Workspace":me?.business_role==="executive"?"Executive Workspace":me?.business_role==="delivery_manager"?"Delivery Manager Workspace":"Admin Workspace";
  const divisionLabel=recruiter?(me?.division||"Rehabilitation"):"Medlivo";

  const groups=useMemo(()=>{
    if(recruiter){
      return [{label:"RECRUITER WORKSPACE",items:[
        {href:"/",label:"Today"},
        {href:"/jobs",label:"Jobs"},
        {href:"/candidates",label:"Candidates"},
        {href:"/matching",label:"Matching"},
        {href:"/conversations",label:"Conversations"},
        {href:"/interviews",label:"Interviews"},
        {href:"/pay-gm",label:"Pay & GM"},
        {href:"/funnel",label:"Submissions"},
        {href:"/weekly",label:"My Week"},
      ]}];
    }
    return [
      {label:"MANAGEMENT",items:[
        {href:"/",label:"Today"},
        {href:"/distribution",label:"Job Distribution"},
        {href:"/jobs",label:"Jobs"},
        {href:"/candidates",label:"Candidates"},
        {href:"/funnel",label:"Submission to Start"},
        {href:"/weekly",label:"Weekly Review"},
        {href:"/manager",label:"Team Overview",show:me?.business_role!=="executive"},
        {href:"/executive",label:"Executive",show:me?.business_role==="executive"},
      ]},
      {label:"CONTROL",items:[
        {href:"/team?section=intake",label:"Job Intake"},
        {href:"/team?section=standards",label:"Job Content Standards"},
        {href:"/team?section=approvals",label:"Job Approval"},
        {href:"/admin",label:"Admin & Access",show:Boolean(me?.system_admin||me?.role==="admin")},
      ]},
    ].map(group=>({...group,items:group.items.filter((x:any)=>x.show!==false)})).filter(group=>group.items.length);
  },[me,recruiter]);

  const active=(href:string)=>{
    if(href==="/")return pathname==="/";
    if(href==="/team?section=intake")return pathname==="/team"&&section==="intake";
    if(href==="/team?section=approvals")return pathname==="/team"&&section==="approvals";
    if(href==="/team?section=standards")return pathname==="/team"&&section==="standards";
    const base=href.split("?")[0];
    return base!=="/"&&pathname.startsWith(base);
  };

  return <div className="appShell">
    <aside className="appSidebar">
      <div className="appBrand">
        <div className="appBrandMark">M</div>
        <div><b>medlivo</b><span>RECRUIT AI</span><small>Healthcare Staffing Intelligence</small></div>
      </div>

      <div className="workspaceIdentity">
        <small>WORKSPACE</small>
        <b>{workspaceLabel}</b>
        <span>{divisionLabel}</span>
      </div>

      <nav aria-label={recruiter?"Recruiter workspace navigation":"Management workspace navigation"}>
        {groups.map(group=><div className="appNavGroup" key={group.label}>
          <small>{group.label}</small>
          {group.items.map((item:any)=><Link key={item.href} href={item.href} className={active(item.href)?"active":""}>{item.label}</Link>)}
        </div>)}
      </nav>

      <div className="appSidebarFoot">
        <div className="appUserCard">
          <div className="appUserAvatar">{(me?.display_name||"M").slice(0,1).toUpperCase()}</div>
          <div><b>{me?.display_name||"Medlivo team"}</b><small>{String(me?.business_role||me?.role||"user").replaceAll("_"," ")}</small></div>
        </div>
        <div className="appEnv"><span className="appStatusDot"/><b>Secure staging</b></div>
        <em>{recruiter?"Block 1 · Recruiter workflow":"Block 1 · Management workflow"}</em>
      </div>
    </aside>
    <div className="appCanvas">{children}</div>
  </div>;
}
