# Use a lightweight official Python runtime
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app.py .
COPY templates/ ./templates/

# Create a non-root user for security best practices
RUN useradd -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

# Expose application port
EXPOSE 8080

# Run using production WSGI server or standard execution
CMD ["python", "app.py"]