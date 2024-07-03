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
    
    def retrive_secret(self, url):
        keymgr = self.api
        id = str(url, 'utf-8').split('/')[-1]
        secret = keymgr.get_secret(id)
        return base64.b64decode(secret.payload)
