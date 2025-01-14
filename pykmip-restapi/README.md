Here’s a **comprehensive `README.md` file** with detailed documentation of all available APIs from your **KMIP** and **Barbican** services.

---

# 📘 **Barbican-KMIP REST API Documentation**

This repository provides a RESTful API for interacting with the **Barbican** and **KMIP** services. Below is a detailed list of available endpoints, their descriptions, expected request parameters, and example requests.

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
| `GET`           | `/kmip/get_kmip_id_from_barbican`       | Retrieves the KMIP ID based on the provided Barbican ID.       |
| `POST`          | `/kmip/update_policy`                  | Updates the policy for a given KMIP object.                    |

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
curl -X GET 'http://<host>:5006/barbican/get_barbican_metadata?uuid=cc2ed8f9-b17b-477c-9845-fd85486a4f28'
```

**Example Response:**

```json
{
    "data": [
        {
            "id": "cc2ed8f9-b17b-477c-9845-fd85486a4f28",
            "name": "Test Secret",
            "project_id": "e9141fb24eee4b3e9f25ae69cda31132"
        }
    ]
}
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
curl -X POST 'http://<host>:5006/barbican/update_project_id' \
     -H "Content-Type: application/json" \
     -d '{"secret_id": "cc2ed8f9-b17b-477c-9845-fd85486a4f28", "external_id": "e9141fb24eee4b3e9f25ae69cda31132"}'
```

**Example Response:**

```json
{
    "message": "Project ID updated successfully"
}
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
curl -X GET 'http://<host>:5006/kmip/get_barbican_id?kmip_id=1234'
```

**Example Response:**

```json
{
    "data": [
        {
            "uid": "1234",
            "url": "https://example.com/object/1234",
            "owner": "user1",
            "policy": "default"
        }
    ]
}
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
curl -X POST 'http://<host>:5006/kmip/kmip_register' \
     -H "Content-Type: application/json" \
     -d '{
           "url": "https://example.com/object/1234",
           "owner": "user1",
           "policy": "default_policy"
         }'
```

**Example Response:**

```json
{
    "message": "KMIP object registered successfully",
    "uid": 1235
}
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
curl -X GET 'http://<host>:5006/kmip/get_kmip_id_from_barbican?barbican_id=299'
```

**Example Response:**

```json
{
    "kmip_id": "1234"
}
```

---

### 🔧 **6. POST /kmip/update_policy**

**Description:**
Updates the policy for a given KMIP object.

**Endpoint:**
`POST /kmip/update_policy`

**Request Body:**

| **Field**              | **Type** | **Required** | **Description**            |
|------------------------|----------|--------------|----------------------------|
| `kmip_id`              | String   | Yes          | The unique KMIP ID.        |
| `operation_policy_name` | String   | Yes          | The policy to be updated.  |

**Example Request:**

```bash
curl -X POST 'http://<host>:5006/kmip/update_policy' \
     -H "Content-Type: application/json" \
     -d '{"kmip_id": "298", "operation_policy_name": "default"}'
```

**Example Response:**

```json
{
    "message": "Operation policy updated successfully"
}
```

---

## 🧪 **Testing the APIs**

You can use tools like **Postman** or **cURL** to test the APIs. Ensure your database is correctly configured and the server is running.

---