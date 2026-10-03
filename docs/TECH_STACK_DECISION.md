# Technology Stack Decision

## Recruiter web
Next.js 16 Active LTS with React 19.

Reasons:
- mature React application model
- strong routing and server-rendering options
- production Docker support
- good fit for an operational web application
- portable deployment even though Google Cloud is the first target

## API and workers
Python + FastAPI.

Reasons:
- strong fit for AI/data/integration services
- clean typed HTTP contracts
- useful ecosystem for parsing, ML, vector search, and orchestration

## Data
- PostgreSQL: operational canonical data
- BigQuery: analytics and event history
- Cloud Storage: source resumes/documents
- dedicated vector/hybrid search: benchmark before selection
- Neo4j: designed for, deferred until relationship intelligence justifies it

## Events
Google Pub/Sub initially, behind explicit event contracts.

## Deployment
Google Cloud first:
- Cloud Run
- Cloud SQL
- Pub/Sub
- Secret Manager
- Cloud Storage
- BigQuery

Services remain containerized to preserve portability.

## Product strategy
The root GitHub Pages files remain the UX prototype.
Production code lives under `apps/` and `services/`.
