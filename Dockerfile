FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc p7zip-full \
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

# Fixed UID/GID (not just -r/auto-assigned) so an operator can chown a host
# bind mount (see docker-compose.prod.yml's ./data:/app/data) to a known owner
# ahead of time.
RUN groupadd -g 1000 mex && useradd -u 1000 -g mex -d /app -s /usr/sbin/nologin mex \
    && mkdir -p /app/data \
    && chown -R mex:mex /app

USER mex

CMD ["./scripts/startup.sh"]