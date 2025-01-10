# Use a slim Python base image
FROM keppel.eu-de-1.cloud.sap/ccloud-dockerhub-mirror/library/python:3.9-slim

# Metadata about the image
LABEL source_repository="https://github.com/sapcc/PyKMIP.git"

# Set environment variables
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

# Copy application files
COPY requirements.txt app.py kmip_operations.py barbican_operations.py utils.py ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn WSGI server for production
RUN pip install gunicorn

# Expose the port the application runs on
EXPOSE 5005

# Default command to run the Flask app using Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5005", "app:app"]
