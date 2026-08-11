# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r /tmp/requirements.txt


FROM python:3.12-slim AS runtime

# git — for the GitHub data backup service; dejavu — fonts for PIL map rendering
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      git \
      fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/app \
    MPLCONFIGDIR=/tmp/matplotlib \
    GIT_AUTHOR_NAME="RTCA Bot" \
    GIT_AUTHOR_EMAIL="rtca-bot@localhost" \
    GIT_COMMITTER_NAME="RTCA Bot" \
    GIT_COMMITTER_EMAIL="rtca-bot@localhost"

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY . .

RUN groupadd --gid 1000 bot \
 && useradd --uid 1000 --gid 1000 --home-dir /app --shell /usr/sbin/nologin bot \
 && mkdir -p /app/data /app/logs /app/.github_backup \
 && chown -R bot:bot /app

USER bot

EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:' + os.getenv('API_PORT', '8080') + '/', timeout=4).status == 200 else 1)"

CMD ["python", "main.py"]
