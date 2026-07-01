FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mailextractor/ ./mailextractor/
COPY scripts/ ./scripts/
COPY example-data/ ./example-data/
COPY migrations/ ./migrations/
COPY alembic.ini ./alembic.ini

RUN chmod +x ./scripts/startup.sh

ENV PYTHONPATH=/app

RUN groupadd -r mex && useradd -r -g mex -d /app -s /usr/sbin/nologin mex \
    && chown -R mex:mex /app

USER mex

CMD ["./scripts/startup.sh"]