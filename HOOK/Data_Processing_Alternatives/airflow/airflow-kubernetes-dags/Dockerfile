# Use the official Python image as the base
FROM python:3.12

# Set environment variables to prevent Python from writing .pyc files
# and to ensure stdout/stderr are unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Create necessary directories with proper permissions
RUN mkdir -p /airflow/xcom /mymodules

# Copy supporting code (setup.py)
COPY dags/dedl /mymodules/dedl
COPY resources/docker/setup.py /mymodules/setup.py

# Install modules
RUN pip install --no-cache-dir /mymodules

# Prepare XCom output file
RUN touch /airflow/xcom/return.json && chmod 666 /airflow/xcom/return.json

# Set working directory
WORKDIR /app