# Event Model

The platform is event-driven and should recalculate only affected records.

Examples:
- job.created
- job.updated
- job.closed
- candidate.created
- candidate.updated
- candidate.resume_updated
- candidate.availability_changed
- candidate.license_changed
- match.qualified
- outreach.approved
- outreach.sent
- outreach.reply_received
- qualification.completed
- candidate.near_ready
- candidate.submission_ready
- submission.approved
- submission.created
- assignment.started
- assignment.ending

Each event should include:
- event_id
- tenant_id
- entity type/id
- source
- occurred_at
- correlation_id
- idempotency key
- actor/agent
- schema version
