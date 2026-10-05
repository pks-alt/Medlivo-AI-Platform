FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    "fastapi[standard]==0.141.1" \
    "pydantic-settings>=2.0,<3.0" \
    "psycopg[binary,pool]>=3.2,<4.0"
COPY app ./app
ENV PORT=8080
EXPOSE 8080
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
