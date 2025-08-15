# 📘 **Barbican-KMIP REST API Documentation**

This repository provides a RESTful API for interacting with the **Barbican** and **KMIP** services. Below is a detailed list of available endpoints, their descriptions, expected request parameters, and example requests.

---

## 🔐 Authentication (Read Me First)

All endpoints require a valid **OpenStack Keystone v3** token via the HTTP header:

```
Authorization: Bearer <USER_TOKEN>
```

Internally, the service validates this token against Keystone using:

- `X-Auth-Token`: the token used to **authenticate the request to Keystone** (often a service/admin token; falls back to the user token if not provided)
- `X-Subject-Token`: the **user token being validated**

### Recommended environment setup for testing
```bash
export USER_TOKEN="<paste a user token>"
export SERVICE_TOKEN="<paste a service/admin token>"   # optional
export KEYSTONE="https://<keystone-host>:5000/v3"
```

### 🔎 Keystone validation (optional but handy for troubleshooting)

**A) Self-validation (no service token):**
```bash
curl -i -s \
  -H "X-Auth-Token: $USER_TOKEN" \
  -H "X-Subject-Token: $USER_TOKEN" \
  "$KEYSTONE/auth/tokens"
```

**B) Service-to-service validation (privileged):**
```bash
curl -i -s \
  -H "X-Auth-Token: $SERVICE_TOKEN" \
  -H "X-Subject-Token: $USER_TOKEN" \
  "$KEYSTONE/auth/tokens"
```

If successful, Keystone returns `200` with JSON containing `token.roles`. Your API checks these roles against `ALLOWED_ADMIN_ROLES` (default: `keymanager_admin`).

---

## 🚀 **Available APIs**

### 🔐 **Barbican APIs**

| **HTTP Method** | **Endpoint**                          | **Description**                                               |
|-----------------|---------------------------------------|---------------------------------------------------------------|
| `GET`           | `/barbican/get_barbican_metadata`      | Retrieves metadata from the `secrets` table using a UUID.     |
| `POST`          | `/barbican/update_project_id`          | Updates the `project_id` in the `secrets` table using `secret_id` and `external_id`. |

---

### 🔑 **KMIP APIs**

| **HTTP Method** | **Endpoint**                           | **Description**                                                |
|-----------------|----------------------------------------|----------------------------------------------------------------|
| `GET`           | `/kmip/get_barbican_id`                | Retrieves Barbican metadata based on the provided KMIP ID.     |
| `POST`          | `/kmip/kmip_register`                  | Registers a new KMIP object in the `managed_objects` table.    |
| `GET`           | `/kmip/get_kmip_id_from_barbican`      | Retrieves the KMIP ID based on the provided Barbican ID.       |
| `POST`          | `/kmip/update_policy`                  | Updates the policy for a given KMIP object.                    |
| `POST`          | `/kmip/update_owner`                   | Updates the Owner for a given KMIP object.                     |

---

## 📖 **Barbican API Documentation**

### 🔎 **1. GET /barbican/get_barbican_metadata**

**Description:**
Retrieves metadata from the `secrets` table using a UUID.

**Endpoint:**
`GET /barbican/get_barbican_metadata`

**Query Parameter:**

| **Parameter** | **Type** | **Required** | **Description**            |
|---------------|----------|--------------|----------------------------|
| `uuid`        | String   | Yes          | The unique UUID of the secret. |

**Example Request:**
```bash
curl -s -X GET "http://<host>:5006/barbican/get_barbican_metadata?uuid=cc2ed8f9-b17b-477c-9845-fd85486a4f28" \
  -H "Authorization: Bearer $USER_TOKEN" | jq .
```

---

### 🔧 **2. POST /barbican/update_project_id**

**Description:**
Updates the `project_id` in the `secrets` table for a given `secret_id` and `external_id`.

**Endpoint:**
`POST /barbican/update_project_id`

**Request Body:**

| **Field**      | **Type** | **Required** | **Description**                 |
|----------------|----------|--------------|---------------------------------|
| `secret_id`    | String   | Yes          | The unique ID of the secret.    |
| `external_id`  | String   | Yes          | The external ID of the project. |

**Example Request:**
```bash
curl -s -X POST "http://<host>:5006/barbican/update_project_id" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"secret_id":"cc2ed8f9-b17b-477c-9845-fd85486a4f28","external_id":"e9141fb24eee4b3e9f25ae69cda31132"}' | jq .
```

---

## 📖 **KMIP API Documentation**

### 🔎 **3. GET /kmip/get_barbican_id**

**Description:**
Retrieves Barbican metadata based on the provided KMIP ID.

**Endpoint:**
`GET /kmip/get_barbican_id`

**Query Parameter:**

| **Parameter** | **Type** | **Required** | **Description**         |
|---------------|----------|--------------|-------------------------|
| `kmip_id`     | String   | Yes          | The unique KMIP ID.     |

**Example Request:**
```bash
curl -s -X GET "http://<host>:5006/kmip/get_barbican_id?kmip_id=1234" \
  -H "Authorization: Bearer $USER_TOKEN" | jq .
```

---

### 🔧 **4. POST /kmip/kmip_register**

**Description:**
Registers a new KMIP object in the `managed_objects` table.

**Endpoint:**
`POST /kmip/kmip_register`

**Request Body:**

| **Field**   | **Type** | **Required** | **Description**          |
|-------------|----------|--------------|--------------------------|
| `url`       | String   | Yes          | The object's URL.        |
| `owner`     | String   | Yes          | The owner of the object. |
| `policy`    | String   | Yes          | The policy to apply.     |

**Example Request:**
```bash
curl -s -X POST "http://<host>:5006/kmip/kmip_register" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/v1/secrets/e71ad2be-8708-4dcb-893d-7cb1cf22d49e","owner":"user1","policy":"default_policy"}' | jq .
```

---

### 🔎 **5. GET /kmip/get_kmip_id_from_barbican**

**Description:**
Retrieves the KMIP ID based on the provided Barbican ID.

**Endpoint:**
`GET /kmip/get_kmip_id_from_barbican`

**Query Parameter:**

| **Parameter**    | **Type** | **Required** | **Description**            |
|------------------|----------|--------------|----------------------------|
| `barbican_id`    | String   | Yes          | The unique Barbican ID.    |

**Example Request:**
```bash
curl -s -X GET "http://<host>:5006/kmip/get_kmip_id_from_barbican?barbican_id=e71ad2be-8708-4dcb-893d-7cb1cf22d49e" \
  -H "Authorization: Bearer $USER_TOKEN" | jq .
```

---

### 🔧 **6. POST /kmip/update_policy**

**Description:**
Updates the policy for a given KMIP object.

**Endpoint:**
`POST /kmip/update_policy`

**Request Body:**

| **Field**                | **Type** | **Required** | **Description**            |
|--------------------------|----------|--------------|----------------------------|
| `kmip_id`                | String   | Yes          | The unique KMIP ID.        |
| `operation_policy_name`  | String   | Yes          | The policy to be updated.  |

**Example Request:**
```bash
curl -s -X POST "http://<host>:5006/kmip/update_policy" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kmip_id":"298","operation_policy_name":"default"}' | jq .
```

---

### 🔧 **7. POST /kmip/update_owner**

**Description:**
Updates the owner for a given KMIP object.

**Endpoint:**
`POST /kmip/update_owner`

**Request Body:**

| **Field**     | **Type** | **Required** | **Description**      |
|---------------|----------|--------------|----------------------|
| `kmip_id`     | String   | Yes          | The unique KMIP ID.  |
| `new_owner`   | String   | Yes          | The new owner.       |

**Example Request:**
```bash
curl -s -X POST "http://<host>:5006/kmip/update_owner" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kmip_id":"298","new_owner":"user2"}' | jq .
```

---
