import { getJobs } from "@/lib/api";

export default async function JobsPage() {
  const jobs = await getJobs();

  return (
    <main className="page">
      <div className="pageHead">
        <div><small>Job intelligence</small><h1>Jobs</h1></div>
        <a href="/">Back to Today</a>
      </div>

      <div className="jobList">
        {jobs.map((job) => (
          <article key={job.id} className="jobCard">
            <div>
              <small>{job.division} · Job {job.source_job_id}</small>
              <h2>{job.title}</h2>
              <p>{job.customer} · {job.location}</p>
            </div>
            <div className="jobStats">
              <span><b>{job.strong_matches}</b>Strong matches</span>
              <span><b>{job.submission_ready}</b>Submission ready</span>
            </div>
            <a href={`/jobs/${job.id}`}>Open job</a>
          </article>
        ))}
      </div>
    </main>
  );
}
