import { getDashboard, getJobs } from "@/lib/api";

export default async function Home() {
  const [summary, jobs] = await Promise.all([getDashboard(), getJobs()]);

  const work = [
    { label: "Submission ready", value: summary.submission_ready, detail: "Candidates awaiting recruiter review" },
    { label: "Interested replies", value: summary.interested_replies, detail: "AI can continue approved qualification" },
    { label: "Jobs at risk", value: summary.jobs_at_risk, detail: "Manager intervention recommended" },
  ];

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><b>M</b><span>Medlivo<br/><small>Recruit AI</small></span></div>
        <nav>
          <a className="active" href="/">Today</a>
          <a href="/jobs">Jobs</a>
          <a href="#">Candidates</a>
          <a href="#">Customers</a>
          <a href="#">Conversations</a>
          <a href="#">Submissions</a>
          <a href="#">Manager</a>
        </nav>
      </aside>

      <section className="content">
        <header>
          <div><small>Recruiter command center</small><h1>Today</h1></div>
          <input aria-label="Ask Recruit AI" placeholder="Ask Recruit AI or search jobs and candidates" />
        </header>

        <section className="hero">
          <small>GOOD AFTERNOON</small>
          <h2>What should you work on next?</h2>
          <p>AI prioritizes assigned customers, jobs, candidate responses, and submission-ready work.</p>
          <button>Review submission-ready candidates</button>
        </section>

        <h3>Needs your attention</h3>
        <div className="cards">
          {work.map((item) => (
            <article key={item.label}>
              <strong>{item.value}</strong>
              <div><b>{item.label}</b><span>{item.detail}</span></div>
              <button>Review</button>
            </article>
          ))}
        </div>

        <h3>Priority jobs</h3>
        <div className="cards">
          {jobs.map((job) => (
            <article key={job.id}>
              <strong>{job.strong_matches}</strong>
              <div>
                <b>{job.title}</b>
                <span>{job.customer} · {job.location} · {job.submission_ready} submission ready</span>
              </div>
              <a className="linkButton" href={`/jobs/${job.id}`}>Open</a>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
