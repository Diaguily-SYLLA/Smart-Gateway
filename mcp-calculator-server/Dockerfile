FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY calculator_server.py .

# Create certs directory (will be mounted)
RUN mkdir -p /certs

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8001
ENV MTLS_ENABLED=false

# Expose port
EXPOSE 8001

# Run the server
CMD ["python", "calculator_server.py"]
