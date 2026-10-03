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
