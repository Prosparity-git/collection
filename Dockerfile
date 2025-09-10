# Use a slim Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system deps
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend app into container
COPY . .

# Expose port (dev = 8001, prod later will use 8000)
EXPOSE 8000

# Run FastAPI app with Gunicorn + Uvicorn worker
#CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8001", "app.main:app"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
