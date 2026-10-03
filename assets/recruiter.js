const titles={today:'Today',jobs:'Jobs',candidates:'Candidates',customers:'Customers',conversations:'Conversations',submissions:'Submissions',analytics:'Analytics'};
document.querySelectorAll('.nav-item').forEach(btn=>btn.addEventListener('click',()=>{
  document.querySelectorAll('.nav-item').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.view').forEach(x=>x.classList.remove('active'));
  btn.classList.add('active');
  const id=btn.dataset.view;
  document.getElementById(id).classList.add('active');
  document.getElementById('pageTitle').textContent=titles[id]||'Medlivo Recruit AI';
}));
const search=document.getElementById('globalSearch');
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();search.focus()}});
search.addEventListener('keydown',e=>{if(e.key==='Enter'&&search.value.trim()){alert('Prototype: Recruit AI will answer and act on: '+search.value.trim());}});

const jobData={
  uro:{division:'Locum Tenens',id:'26-37123',title:'Urologist',meta:['Kearney, NE','$360–$420/hour','Start: ASAP','Posted Sep 2, 2026'],profession:'Physician',specialty:'Urology',location:'Kearney, Nebraska',start:'ASAP',license:'NE active or ready before start',schedule:'Confirm with client'},
  rn:{division:'Nursing & Allied',id:'26-13176',title:'Registered Nurse',meta:['Live Medlivo job record','Job details pending JobDiva API connection'],profession:'Registered Nurse',specialty:'From JobDiva requisition',location:'From JobDiva requisition',start:'From JobDiva requisition',license:'Required state license or ready before start',schedule:'From JobDiva requisition'},
  ot:{division:'Rehabilitation',id:'26-31915',title:'Occupational Therapist',meta:['Live Medlivo job record','Job details pending JobDiva API connection'],profession:'Occupational Therapist',specialty:'Occupational Therapy',location:'From JobDiva requisition',start:'From JobDiva requisition',license:'Required state OT license or ready before start',schedule:'From JobDiva requisition'}
};
document.querySelectorAll('.job-pill').forEach(btn=>btn.addEventListener('click',()=>{
  document.querySelectorAll('.job-pill').forEach(x=>x.classList.remove('active'));btn.classList.add('active');
  const d=jobData[btn.dataset.job]; if(!d)return;
  document.getElementById('jobDivision').textContent=d.division;
  document.getElementById('jobId').textContent=d.id;
  document.getElementById('jobTitle').textContent=d.title;
  document.getElementById('jobMeta').innerHTML=d.meta.map(x=>'<span>'+x+'</span>').join('');
  document.getElementById('reqProfession').textContent=d.profession;
  document.getElementById('reqSpecialty').textContent=d.specialty;
  document.getElementById('reqLocation').textContent=d.location;
  document.getElementById('reqStart').textContent=d.start;
  document.getElementById('reqLicense').textContent=d.license;
  document.getElementById('reqSchedule').textContent=d.schedule;
}));
