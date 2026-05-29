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

import base64
import logging
import os
import urllib3  # noqa: F401

from openstack import connection

logger = logging.getLogger(__name__)


class OpenstackHelper:
    def __init__(
            self, region, user_domain_name, project_domain_name,
            project_name, autoconnect=True):
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

        # add the compute_host attribute to find out which building block
        # hosts a server — already in openstacksdk master, not yet released
        if not hasattr(OpenStackServer, 'compute_host'):
            OpenStackServer.compute_host = resource.Body(
                'OS-EXT-SRV-ATTR:host')

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

            def _get_version_data(sess, url, **kwargs):
                data = old_get_version_data(sess, url, **kwargs)
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
            password=os.environ.get("OS_PASSWORD"),
            user_domain_name=self.user_domain_name,
            project_name=self.project_name,
            project_domain_name=self.project_domain_name,
        )
        kwargs = {}
        if os.environ.get('OS_CERT'):
            kwargs['cert'] = os.environ['OS_CERT']
        if os.environ.get('OS_KEY'):
            kwargs['key'] = os.environ['OS_KEY']
        if os.environ.get('OS_AUTH_TYPE'):
            kwargs['auth_type'] = os.environ['OS_AUTH_TYPE']
        self.api = connection.Connection(
            region_name=self.region, auth=auth, debug=True, **kwargs)

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
                path = "{}/{}".format(
                    self.get_project_path(
                        project.domain_id, use_cache=use_cache),
                    project.name)
            self._project_path_cache[project_id] = path
        return self._project_path_cache[project_id]


class Barbicanstore:
    def __init__(self, project_name, project_domain_name):
        self.region = os.environ.get("OS_REGION_NAME")
        self.user_domain_name = os.environ.get("OS_USER_DOMAIN_NAME")
        self.project_domain_name = project_domain_name
        self.project_name = project_name
        self._os_client = None

    @property
    def api(self):
        if self._os_client is None:
            self._os_client = OpenstackHelper(
                self.region, self.user_domain_name,
                self.project_domain_name, self.project_name)
        return self._os_client.api.key_manager

    def create_secret(self, name, payload, algorithm=None, length=None):
        keymgr = self.api
        attrs = dict()
        attrs["name"] = name
        attrs["secret_type"] = "symmetric"  # nosec B105
        attrs["payload_content_type"] = "text/plain"
        attrs["payload"] = base64.b64encode(payload).decode('utf-8')
        if algorithm:
            attrs['algorithm'] = algorithm
        if length:
            attrs['bit_length'] = length
        logger.debug(
            "Creating Barbican secret: name=%s algorithm=%s bit_length=%s",
            name, algorithm, length,
        )
        secret_ref = keymgr.create_secret(**attrs)
        logger.debug("Barbican secret created successfully")
        return secret_ref.secret_ref

    def retrive_secret(self, url):
        try:
            keymgr = self.api
            id = str(url, 'utf-8').split('/')[-1]
            logger.debug("Fetching Barbican secret")
            secret = keymgr.get_secret(id)

            payload = secret.payload
            if not payload:
                logger.error("Barbican secret has empty payload")
                raise ValueError("Retrieved secret has an empty payload.")

            if isinstance(secret.payload, bytes):
                logger.debug("Barbican secret returned binary payload")
                return payload

            content_type = list(secret.content_types.values())[0]
            if not content_type:
                logger.warning(
                    "Barbican secret missing content_type, assuming base64"
                )
                content_type = "application/base64"

            logger.debug(
                "Barbican secret payload: content_type=%s", content_type
            )

            if len(payload) % 4 != 0:
                padding = 4 - len(payload) % 4
                logger.debug(
                    "Base64 padding added: %d chars", padding
                )
                payload += '=' * padding

            try:
                decoded = base64.b64decode(payload)
                logger.debug("Barbican secret decoded successfully")
                return decoded
            except base64.binascii.Error as e:
                logger.error("Base64 decode failed for Barbican secret: %s", e)
                raise ValueError("Invalid base64-encoded string.") from e

        except AttributeError as e:
            logger.error(
                "Barbican secret object missing required attribute: %s", e
            )
            raise AttributeError(
                "The secret object is missing required attributes.") from e

        except Exception as e:
            logger.error(
                "Unexpected error retrieving Barbican secret: %s", e
            )
            raise RuntimeError(
                "An unexpected error occurred while retrieving the secret."
            ) from e
