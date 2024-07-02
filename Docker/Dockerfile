# Use a base image with Python 3.9 and Alpine Linux for smaller size
FROM python:3.9-alpine

# Set environment variables for OpenStack application credentials
ENV OS_USERNAME=your_openstack_username
ENV OS_PASSWORD=your_openstack_password
ENV OS_PROJECT_ID=your_openstack_project_id
ENV OS_APPLICATION_CREDENTIAL_NAME=kmip
ENV OS_APPLICATION_CREDENTIAL_SECRET=kmip
ENV OS_AUTH_TYPE=v3applicationcredential
ENV OS_AUTH_URL=your_os_auth_url
LABEL source_repository=https://github.com/sapcc/PyKMIP
# Install necessary packages (including build dependencies)
RUN apk update && \
    apk add --no-cache gcc musl-dev libffi-dev openssl-dev openssh-client git mariadb-dev python3-dev

# Set up directories for certificates and configuration
RUN mkdir -p /etc/pykmip/certs
RUN mkdir -p /etc/pykmip/policies
# Copy your certificates and configuration files into the container
# Use /bin/create_certificates.py to generate certificas for the build
COPY certs/server.crt /etc/pykmip/certs/server.crt
COPY certs/server.key /etc/pykmip/certs/server.key
COPY certs/ca.crt /etc/pykmip/certs/ca.crt
COPY policies/policy.json /etc/pykmip/policies/policy.json
COPY pykmip.conf /etc/pykmip/server.conf

# Install PyKMIP and its dependencies
#  pip install pykmip
RUN pip install -U --upgrade-strategy eager https://github.com/sapcc/PyKMIP
# Expose the KMIP server port
EXPOSE 5696

# Redirect logs to stdout and use Logstash for log management (if applicable)
# Ensure pykmip-server logs are directed to stdout
CMD ["pykmip-server", "-l", "/dev/stdout"]

