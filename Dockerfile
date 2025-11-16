FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    adb \
    bpftrace \
    linux-headers-generic \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY bpftrace_scripts/ ./bpftrace_scripts/
COPY start.sh .

# Create output directory
RUN mkdir -p output && chmod +x start.sh

# Expose ports
EXPOSE 5000 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run the application
CMD ["./start.sh"]
