"use client";
import {useEffect} from "react";
import {useRouter} from "next/navigation";

export default function RecruiterPreviewRedirect(){
  const router=useRouter();
  useEffect(()=>{router.replace("/recruiter-review")},[router]);
  return <main className="page"><div className="adminLoading">Opening the full recruiter UX review…</div></main>;
}
