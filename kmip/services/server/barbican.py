# Copyright (c) 2024 SAP SE
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import urllib3
import sys
import base64
import logging
from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneclient import client
from openstack import connection

class OpenstackHelper:
    def __init__(self, region, user_domain_name, project_domain_name, project_name, autoconnect=True):
        self.region = region
        self.user_domain_name = user_domain_name
        self.project_domain_name = project_domain_name
        self.project_name = project_name
        self.api = None
        self._project_path_cache = {}

        self.monkeypatch_openstack()
        self.monkeypatch_keystoneauth1()

        if autoconnect:
            self.connect()

    @staticmethod
    def monkeypatch_openstack():
        """Apply some fixes and backports to the openstacksdk
        Can be called multiple times
        """
        from openstack.compute.v2.server import Server as OpenStackServer
        from openstack import resource

        # add the compute_host attribute to find out in which building block a server runs
        # at the time of this commit this is already in place in the openstacksdk master, but
        # not in any release
        if not hasattr(OpenStackServer, 'compute_host'):
            OpenStackServer.compute_host = resource.Body('OS-EXT-SRV-ATTR:host')

    @staticmethod
    def monkeypatch_keystoneauth1():
        """Apply fixes to keystoneauth1
        Can be called multiple times
        """
        import keystoneauth1.discover
        # patch get_version_data to include the expected values if the endpoint
        # returns only one version like nova's placement-api in queens
        if not getattr(keystoneauth1.discover.get_version_data, 'is_patched', False):
            old_get_version_data = keystoneauth1.discover.get_version_data

            def _get_version_data(session, url, **kwargs):
                data = old_get_version_data(session, url, **kwargs)
                for v in data:
                    if 'status' not in v and len(data) == 1:
                        v['status'] = 'current'
                    if 'links' not in v and len(data) == 1:
                        v['links'] = [{'href': url, 'rel': 'self'}]
                return data
            _get_version_data.is_patched = True
            keystoneauth1.discover.get_version_data = _get_version_data

    def connect(self, test=True):
        auth = dict(
            auth_url='https://identity-3.{}.cloud.sap/v3'.format(self.region),
            username=os.environ.get("OS_USERNAME"),
            user_domain_name=self.user_domain_name,
            application_credential_name=os.environ.get('OS_APPLICATION_CREDENTIAL_NAME'),
            application_credential_secret=os.environ.get('OS_APPLICATION_CREDENTIAL_SECRET'),
        )
        kwargs = {}
        if os.environ.get('OS_CERT'):
            kwargs['cert'] = os.environ['OS_CERT']
        if os.environ.get('OS_KEY'):
            kwargs['key'] = os.environ['OS_KEY']
        if os.environ.get('OS_AUTH_TYPE'):
            kwargs['auth_type'] = os.environ['OS_AUTH_TYPE']
        self.api = connection.Connection(region_name=self.region, auth=auth, debug=True, **kwargs)


        if test:
            self.api.identity.region_name

    def get_project_path(self, project_id, use_cache=True):
        if not project_id:
            return ""
        if not use_cache or project_id not in self._project_path_cache:
            project = self.api.identity.get_project(project_id)
            if project.is_domain:
                path = project.name
            else:
                path = "{}/{}".format(self.get_project_path(project.domain_id, use_cache=use_cache), project.name)
            self._project_path_cache[project_id] = path
        return self._project_path_cache[project_id]


class Barbicanstore:
    def __init__(self, project_name, project_domain_name):
        self.region = os.environ.get("OS_REGION_NAME")
        self.user_domain_name = os.environ.get("OS_USER_DOMAIN_NAME")
        self.project_domain_name = project_domain_name
        self.project_name = project_name
        self.os_client = OpenstackHelper(self.region, self.user_domain_name, self.project_domain_name, self.project_name)
        self.api = self.os_client.api.key_manager

        self.logger = logging.getLogger('kmip.server.engine')
    
    def create_secret(self, name, payload, algorithm=None, length=None):
        keymgr = self.api
        attrs = dict()
        attrs["name"] = name
        attrs["secret_type"] = "symmetric"
        attrs["payload_content_type"] = "text/plain"
        attrs["payload"] = base64.b64encode(payload).decode('utf-8')
        if algorithm:
            attrs['algorithm'] = algorithm
        if length:
            attrs['bit_length'] = length
        secret_ref = keymgr.create_secret(**attrs)   
            
        return secret_ref.secret_ref
    
    #SECTION - Store metadata in barbican
    def create_secret_metadata(self, secret_ref, metadata):
        secret_id = secret_ref.rstrip('/').split('/')[-1]
        barbican_endpoint = self.os_client.api.endpoint_for(service_type='key-manager')
        url = f"{barbican_endpoint}/v1/secrets/{secret_id}/metadata"

        metadata_payload = {"metadata": metadata}
        _ = self.os_client.api.session.put(url, json=metadata_payload)

        self.logger.debug(f'SAPCC: Metadata Created')

        return

    def retrive_secret(self, url):
        try:
            keymgr = self.api
            id = str(url, 'utf-8').split('/')[-1]
            secret = keymgr.get_secret(id)

            # Check if payload exists and is not empty
            payload = secret.payload
            if not payload:
                logging.error("Payload is empty or missing.")
                raise ValueError("Retrieved secret has an empty payload.")

            # Check for payload content type
            if type(secret.payload) == bytes:
                logging.info("Payload is binary data.")
                return payload  # Return binary data as is

            content_type = list(secret.content_types.values())[0]
            if not content_type:
                logging.warning("payload_content_type is missing. Defaulting to base64.")
                content_type = "application/base64"

            logging.debug(f"Retrieved payload: {payload}, Content-Type: {content_type}")

            # Handle different content types
            logging.info("Payload is base64 encoded. Decoding...")
            try:
                # Ensure the payload is base64 encoded
                if len(payload) % 4 != 0:
                    logging.warning("Payload length is not a multiple of 4. Padding will be added.")
                    payload += '=' * (4 - len(payload) % 4)

                decoded_payload = base64.b64decode(payload)
                logging.info("Payload successfully decoded.")
                return decoded_payload

            except base64.binascii.Error as e:
                logging.error(f"Base64 decoding failed: {e}")
                raise ValueError("Invalid base64-encoded string.") from e

        except AttributeError as e:
            logging.error(f"Attribute error: {e}")
            raise AttributeError("The secret object is missing required attributes.") from e

        except Exception as e:
            logging.error(f"Unexpected error occurred: {e}")
            raise RuntimeError("An unexpected error occurred while retrieving the secret.") from e
