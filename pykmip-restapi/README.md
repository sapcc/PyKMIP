# Barbican-KMIP REST API

REST API for managing KMIP objects and Barbican secrets. All endpoints except `/healthz` require a Keystone token with the `keymanager_admin` role.

## Authentication

```bash
export TOKEN=$(openstack token issue -f value -c id)
```

Pass the token as a Bearer header on every request:
```
Authorization: Bearer <token>
```

## Base URL

```
https://kmip.cc.<region>.cloud.sap
```

---

## Endpoints

### Health check

```
GET /healthz
```

No auth required. Returns `{"status": "ok"}` when the service is up.

```bash
curl -sk https://kmip.cc.<region>.cloud.sap/healthz | jq .
```

---

### KMIP

#### GET /kmip/get_kmip_id_from_barbican

Returns the KMIP ID for a given Barbican secret ID.

| Parameter | Type | Required |
|-----------|------|----------|
| `barbican_id` | string | yes |

```bash
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://kmip.cc.<region>.cloud.sap/kmip/get_kmip_id_from_barbican?barbican_id=2c895f23-2315-4fa6-8286-d632c88491b4" | jq .
```

```json
{"kmip_id": 334}
```

---

#### GET /kmip/get_barbican_id

Returns Barbican metadata for a given KMIP ID.

| Parameter | Type | Required |
|-----------|------|----------|
| `kmip_id` | string | yes |

```bash
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://kmip.cc.<region>.cloud.sap/kmip/get_barbican_id?kmip_id=334" | jq .
```

---

#### POST /kmip/kmip_register

Registers a new KMIP object in the `managed_objects` table.

| Field | Type | Required |
|-------|------|----------|
| `url` | string | yes |
| `owner` | string | yes |
| `policy` | string | yes |

```bash
curl -sk -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/key/1234", "owner": "<project-id>", "policy": "default"}' \
  https://kmip.cc.<region>.cloud.sap/kmip/kmip_register | jq .
```

---

#### POST /kmip/update_policy

Updates the operation policy for a KMIP object.

| Field | Type | Required |
|-------|------|----------|
| `kmip_id` | string | yes |
| `operation_policy_name` | string | yes |

```bash
curl -sk -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kmip_id": "334", "operation_policy_name": "default"}' \
  https://kmip.cc.<region>.cloud.sap/kmip/update_policy | jq .
```

---

#### POST /kmip/update_owner

Updates the owner of a KMIP object.

| Field | Type | Required |
|-------|------|----------|
| `kmip_id` | string | yes |
| `new_owner` | string | yes |

```bash
curl -sk -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kmip_id": "334", "new_owner": "<new-project-id>"}' \
  https://kmip.cc.<region>.cloud.sap/kmip/update_owner | jq .
```

---

### Barbican

#### GET /barbican/get_barbican_metadata

Returns metadata from the Barbican `secrets` table for a given UUID.

| Parameter | Type | Required |
|-----------|------|----------|
| `uuid` | string | yes |

```bash
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://kmip.cc.<region>.cloud.sap/barbican/get_barbican_metadata?uuid=2c895f23-2315-4fa6-8286-d632c88491b4" | jq .
```

---

#### POST /barbican/update_project_id

Updates the `project_id` for a given Barbican secret.

| Field | Type | Required |
|-------|------|----------|
| `secret_id` | string | yes |
| `project_id` | string | yes |

```bash
curl -sk -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"secret_id": "2c895f23-2315-4fa6-8286-d632c88491b4", "project_id": "<new-project-id>"}' \
  https://kmip.cc.<region>.cloud.sap/barbican/update_project_id | jq .
```

---

## Error responses

| Code | Meaning |
|------|---------|
| `401` | Missing/invalid token or lacks `keymanager_admin` role |
| `400` | Missing required parameter |
| `500` | Internal error — check `kmip-restapi` pod logs |
