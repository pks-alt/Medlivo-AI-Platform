const work = [
  { label: "Submission ready", value: "7", detail: "Candidates awaiting recruiter review" },
  { label: "Interested replies", value: "12", detail: "AI qualified 8 automatically" },
  { label: "Jobs at risk", value: "3", detail: "Manager intervention recommended" },
];

export default function Home() {
  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><b>M</b><span>Medlivo<br/><small>Recruit AI</small></span></div>
        <nav>
          <a className="active" href="#">Today</a>
          <a href="#">Jobs</a>
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

        <div className="notice">
          <b>Production foundation started</b>
          <span>The GitHub Pages prototype remains the UX reference while this Next.js application becomes the production recruiter portal.</span>
        </div>
      </section>
    </main>
  );
}
