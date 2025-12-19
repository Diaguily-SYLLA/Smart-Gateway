FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY weather_server.py .

# Create certs directory (will be mounted)
RUN mkdir -p /certs

# Note: Running as root to access mounted certificates
# In production, use proper secret management (Vault, K8s secrets, etc.)

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV MTLS_ENABLED=false

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "weather_server.py"]
