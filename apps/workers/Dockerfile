FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY services/jobdiva-connector /workspace/services/jobdiva-connector
COPY services/candidate-intelligence /workspace/services/candidate-intelligence
COPY services/job-intelligence /workspace/services/job-intelligence
COPY services/matching-engine /workspace/services/matching-engine
COPY apps/workers /workspace/apps/workers

RUN pip install --no-cache-dir \
    /workspace/services/jobdiva-connector \
    /workspace/services/candidate-intelligence \
    /workspace/services/job-intelligence \
    /workspace/services/matching-engine \
    /workspace/apps/workers

WORKDIR /workspace/apps/workers

USER 65532:65532

CMD ["python", "pilot.py"]
