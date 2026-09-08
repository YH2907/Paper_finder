FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (libxml2/libxslt for lxml)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for persistent SQLite (Render mounts a disk here)
RUN mkdir -p /app/data

# Expose port (Render overrides this via PORT env var)
EXPOSE 8000

# Start command - uses start.sh for flexibility
RUN chmod +x start.sh
CMD ["./start.sh"]
