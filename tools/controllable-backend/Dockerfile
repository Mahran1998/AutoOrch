FROM python:3.11-slim

WORKDIR /app

# Copy the Flask app
COPY flask_backend.py .

# Install dependencies
RUN pip install --no-cache-dir \
    flask==2.3.3 \
    prometheus-client==0.18.0 \
    aiohttp==3.9.0

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Expose metrics port
EXPOSE 5000

# Run the app
CMD ["python", "flask_backend.py"]
