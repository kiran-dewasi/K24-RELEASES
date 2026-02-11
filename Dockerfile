FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/
COPY .env .

# Create database directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8001

# Run application
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8001"]
