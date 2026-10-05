const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export default async function CandidatePage({ params }: { params: Promise<{ candidateId: string }> }) {
  const { candidateId } = await params;
  const response = await fetch(`${API_URL}/api/v1/candidates/${candidateId}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load candidate");
  const candidate = await response.json();

  return (
    <main className="page">
      <div className="pageHead">
        <div><small>Candidate intelligence</small><h1>{candidate.name}</h1><p>{candidate.specialty} · {candidate.location}</p></div>
        <a href="/jobs/job-1">Back to Job</a>
      </div>

      <div className="profileStrip">
        <span><b>{candidate.overall_match}</b>Overall match</span>
        <span><b>{candidate.clinical_fit}</b>Clinical fit</span>
        <span><b>{candidate.availability}</b>Availability</span>
        <span><b>{candidate.license_readiness}</b>License</span>
        <span><b>{candidate.engagement}</b>Engagement</span>
      </div>

      <section className="panelBox">
        <small>Evidence</small>
        <div className="evidenceList">
          {candidate.evidence.map((item: any) => (
            <article key={item.type}>
              <b>{item.type}</b>
              <p>{item.value}</p>
              <span>{item.source}</span>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
