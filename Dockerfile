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
COPY policies/policy.json /etc/pykmip/policies/policy.json
COPY pykmip.conf /etc/pykmip/server.conf

# Clone the PyKMIP repository
RUN git clone https://github.com/sapcc/PyKMIP /tmp/pykmip

# Install PyKMIP from the cloned repository
RUN pip install -U --upgrade-strategy eager /tmp/pykmip

# Expose the KMIP server port
EXPOSE 5696

# Redirect logs to stdout and use Logstash for log management (if applicable)
# Ensure pykmip-server logs are directed to stdout
CMD ["pykmip-server", "-l", "/dev/stdout"]
