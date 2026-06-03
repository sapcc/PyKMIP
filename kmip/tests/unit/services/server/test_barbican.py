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
import unittest
from unittest import mock

from kmip.services.server.barbican import Barbicanstore


class TestBarbicanstore(unittest.TestCase):

    def _make_store(self):
        return Barbicanstore(
            project_name='test-project',
            project_domain_name='test-domain',
        )

    # ------------------------------------------------------------------
    # __init__ / lazy api property
    # ------------------------------------------------------------------

    def test_init_does_not_connect(self):
        """No network call should happen on construction."""
        store = self._make_store()
        self.assertIsNone(store._os_client)

    def test_api_property_creates_os_client_once(self):
        store = self._make_store()
        mock_helper = mock.MagicMock()
        mock_helper.api.key_manager = mock.sentinel.keymgr

        with mock.patch(
            'kmip.services.server.barbican.OpenstackHelper',
            return_value=mock_helper,
        ) as mock_cls:
            keymgr1 = store.api
            keymgr2 = store.api

        mock_cls.assert_called_once()
        self.assertIs(keymgr1, mock.sentinel.keymgr)
        self.assertIs(keymgr2, mock.sentinel.keymgr)  # cached, not re-created

    # ------------------------------------------------------------------
    # create_secret
    # ------------------------------------------------------------------

    def test_create_secret_returns_secret_ref(self):
        store = self._make_store()
        payload = b'\x01\x02\x03\x04'
        expected_ref = 'https://barbican/v1/secrets/abc-123'

        mock_keymgr = mock.MagicMock()
        mock_keymgr.create_secret.return_value.secret_ref = expected_ref

        with mock.patch.object(
            type(store), 'api', new_callable=mock.PropertyMock,
            return_value=mock_keymgr,
        ):
            result = store.create_secret('mykey', payload, 'AES', 256)

        self.assertEqual(expected_ref, result)
        mock_keymgr.create_secret.assert_called_once_with(
            name='mykey',
            secret_type='symmetric',
            payload_content_type='text/plain',
            payload=base64.b64encode(payload).decode('utf-8'),
            algorithm='AES',
            bit_length=256,
        )

    def test_create_secret_without_algorithm_or_length(self):
        store = self._make_store()
        mock_keymgr = mock.MagicMock()
        mock_keymgr.create_secret.return_value.secret_ref = 'ref'

        with mock.patch.object(
            type(store), 'api', new_callable=mock.PropertyMock,
            return_value=mock_keymgr,
        ):
            store.create_secret('k', b'secret')

        call_kwargs = mock_keymgr.create_secret.call_args[1]
        self.assertNotIn('algorithm', call_kwargs)
        self.assertNotIn('bit_length', call_kwargs)

    def test_create_secret_encodes_payload_as_base64(self):
        store = self._make_store()
        raw = b'\xde\xad\xbe\xef'
        mock_keymgr = mock.MagicMock()
        mock_keymgr.create_secret.return_value.secret_ref = 'ref'

        with mock.patch.object(
            type(store), 'api', new_callable=mock.PropertyMock,
            return_value=mock_keymgr,
        ):
            store.create_secret('k', raw)

        sent = mock_keymgr.create_secret.call_args[1]['payload']
        self.assertEqual(base64.b64decode(sent), raw)

    # ------------------------------------------------------------------
    # retrive_secret
    # ------------------------------------------------------------------

    def _make_url(self, secret_id='abc-123'):
        return 'https://barbican/v1/secrets/{}'.format(secret_id).encode('utf-8')

    def test_retrive_secret_decodes_base64_payload(self):
        store = self._make_store()
        raw = b'\x00\x11\x22\x33'
        encoded = base64.b64encode(raw).decode('utf-8')

        mock_secret = mock.MagicMock()
        mock_secret.payload = encoded
        mock_secret.content_types = {'default': 'text/plain'}

        mock_keymgr = mock.MagicMock()
        mock_keymgr.get_secret.return_value = mock_secret

        with mock.patch.object(
            type(store), 'api', new_callable=mock.PropertyMock,
            return_value=mock_keymgr,
        ):
            result = store.retrive_secret(self._make_url('abc-123'))

        mock_keymgr.get_secret.assert_called_once_with('abc-123')
        self.assertEqual(raw, result)

    def test_retrive_secret_returns_binary_payload_as_is(self):
        store = self._make_store()
        binary = b'\xff\xfe\xfd'

        mock_secret = mock.MagicMock()
        mock_secret.payload = binary  # bytes → returned directly

        mock_keymgr = mock.MagicMock()
        mock_keymgr.get_secret.return_value = mock_secret

        with mock.patch.object(
            type(store), 'api', new_callable=mock.PropertyMock,
            return_value=mock_keymgr,
        ):
            result = store.retrive_secret(self._make_url())

        self.assertEqual(binary, result)

    def test_retrive_secret_pads_unaligned_base64(self):
        store = self._make_store()
        raw = b'hello'  # strip padding below to exercise the padding branch
        # Manually strip padding to force the padding branch
        encoded = base64.b64encode(raw).decode('utf-8').rstrip('=')

        mock_secret = mock.MagicMock()
        mock_secret.payload = encoded
        mock_secret.content_types = {'default': 'text/plain'}

        mock_keymgr = mock.MagicMock()
        mock_keymgr.get_secret.return_value = mock_secret

        with mock.patch.object(
            type(store), 'api', new_callable=mock.PropertyMock,
            return_value=mock_keymgr,
        ):
            result = store.retrive_secret(self._make_url())

        self.assertEqual(raw, result)

    def test_retrive_secret_empty_payload_raises_value_error(self):
        store = self._make_store()

        mock_secret = mock.MagicMock()
        mock_secret.payload = None

        mock_keymgr = mock.MagicMock()
        mock_keymgr.get_secret.return_value = mock_secret

        with mock.patch.object(
            type(store), 'api', new_callable=mock.PropertyMock,
            return_value=mock_keymgr,
        ):
            with self.assertRaises(RuntimeError):
                store.retrive_secret(self._make_url())

    def test_retrive_secret_invalid_base64_raises_value_error(self):
        store = self._make_store()

        mock_secret = mock.MagicMock()
        mock_secret.payload = '!!!not-base64!!!'
        mock_secret.content_types = {'default': 'text/plain'}

        mock_keymgr = mock.MagicMock()
        mock_keymgr.get_secret.return_value = mock_secret

        with mock.patch.object(
            type(store), 'api', new_callable=mock.PropertyMock,
            return_value=mock_keymgr,
        ):
            with self.assertRaises(RuntimeError):
                store.retrive_secret(self._make_url())

    def test_retrive_secret_uses_last_path_segment_as_id(self):
        store = self._make_store()
        raw = b'\xab\xcd'
        encoded = base64.b64encode(raw).decode('utf-8')

        mock_secret = mock.MagicMock()
        mock_secret.payload = encoded
        mock_secret.content_types = {'default': 'text/plain'}

        mock_keymgr = mock.MagicMock()
        mock_keymgr.get_secret.return_value = mock_secret

        url = b'https://barbican/v1/secrets/my-secret-id'

        with mock.patch.object(
            type(store), 'api', new_callable=mock.PropertyMock,
            return_value=mock_keymgr,
        ):
            store.retrive_secret(url)

        mock_keymgr.get_secret.assert_called_once_with('my-secret-id')


if __name__ == '__main__':
    unittest.main()
