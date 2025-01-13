# Use a slim Python base image
FROM keppel.eu-de-1.cloud.sap/ccloud-dockerhub-mirror/library/python:3.9-slim

# Metadata about the image
LABEL source_repository="https://github.com/sapcc/PyKMIP.git"

# Set environment variables for KMIP and Barbican services
ENV KMIP_MARIADB_SERVICE_HOST=kmip-mariadb.monsoon3.svc.cluster.local \
    KMIP_MARIADB_SERVICE_PORT=3306 \
    KMIP_MARIADB_SERVICE_USER=user \
    KMIP_MARIADB_SERVICE_PASSWORD=pwd \
    KMIP_MARIADB_NAME=kmip \
    BARBICAN_MARIADB_SERVICE_HOST=barbican-mariadb.monsoon3.svc.cluster.local \
    BARBICAN_MARIADB_SERVICE_PORT=3306 \
    BARBICAN_MARIADB_SERVICE_USER=user \
    BARBICAN_MARIADB_SERVICE_PASSWORD=pwd \
    BARBICAN_MARIADB_NAME=barbican

# Set the working directory inside the container
WORKDIR /app

# Install required system packages for PyKMIP and cryptography
RUN apt-get update && apt-get install -y \
    libssl-dev \
    libffi-dev \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the project files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn WSGI server for production
RUN pip install --no-cache-dir gunicorn

# Expose the port the application runs on
EXPOSE 5005

# Default command to run the Flask app using Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5005", "app:create_app()"]
