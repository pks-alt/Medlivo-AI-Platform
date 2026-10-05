const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export default async function JobDetailPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load job");
  const job = await response.json();

  return (
    <main className="page">
      <div className="pageHead">
        <div><small>{job.division} · Job {job.source_job_id}</small><h1>{job.title}</h1><p>{job.customer} · {job.location}</p></div>
        <a href="/jobs">Back to Jobs</a>
      </div>

      <section className="detailGrid">
        <div className="panelBox">
          <small>Requirements that drive matching</small>
          <div className="requirements">
            {Object.entries(job.requirements).map(([key, value]) => (
              <div key={key}><span>{key}</span><b>{String(value)}</b></div>
            ))}
          </div>
          <h3>Hard gates</h3>
          <div className="chips">{job.hard_gates.map((gate: string) => <span key={gate}>{gate}</span>)}</div>
        </div>

        <div className="panelBox">
          <small>Best candidates to work now</small>
          {job.candidate_matches.map((candidate: any) => (
            <article className="matchCard" key={candidate.id}>
              <div><b>{candidate.name}</b><span>{candidate.specialty} · {candidate.location}</span></div>
              <strong>{candidate.overall_score}</strong>
              <p>{candidate.why_matched}</p>
              <a href={`/candidates/${candidate.id}`}>Open candidate</a>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
