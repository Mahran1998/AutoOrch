FROM python:3.11-slim

WORKDIR /app

ARG KUBECTL_VERSION=v1.29.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && chmod +x /usr/local/bin/kubectl \
    && rm -rf /var/lib/apt/lists/*

COPY webhook/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY webhook /app/webhook
COPY playbooks /app/playbooks

ENV PLAYBOOK_DIR=/app/playbooks

EXPOSE 8080
CMD ["uvicorn", "webhook.main:app", "--host", "0.0.0.0", "--port", "8080"]
