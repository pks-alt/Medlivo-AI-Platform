FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY pyproject.toml ./
COPY workspace_api ./workspace_api
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8080
CMD ["sh", "-c", "uvicorn workspace_api.app:create_app --factory --host 0.0.0.0 --port ${PORT} --no-access-log"]
