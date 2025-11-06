FROM python:3.12-slim

LABEL maintainer="you@example.com"
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

# upgrade pip to avoid wheel/install issues, then install requirements
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r /app/requirements.txt

COPY loadgen.py /app/loadgen.py
RUN chmod +x /app/loadgen.py

ARG METRICS_PORT=8080
EXPOSE ${METRICS_PORT}

ENV TARGET="http://frontend:80/"
ENV RPS="50"
ENV CONCURRENCY="25"
ENV METRICS_PORT="${METRICS_PORT}"
ENV DURATION_SECONDS="0"

CMD ["python", "/app/loadgen.py"]
