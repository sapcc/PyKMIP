
# Metadata API for Barbican and KMIP Operations

This document provides details about the APIs for managing and interacting with metadata from both Barbican and KMIP operations.

---

## **API Endpoints**

| Endpoint                  | HTTP Method | Description                                              | Required Parameters                     |
|---------------------------|-------------|----------------------------------------------------------|-----------------------------------------|
| `/get_barbican_id`        | `GET`       | Fetch the Barbican ID for a given KMIP ID.               | `kmip_id` (Query Parameter)             |
| `/get_kmip_id`            | `GET`       | Fetch the KMIP ID for a given Barbican ID.               | `barbican_id` (Query Parameter)         |
| `/get_kmip_details`       | `GET`       | Fetch details for a given KMIP ID.                       | `kmip_id` (Query Parameter)             |
| `/update_policy`          | `POST`      | Update the operation policy for a KMIP object.           | `kmip_id` and `operation_policy_name` (JSON Body) |
| `/update_owner`           | `POST`      | Update the owner of a KMIP object.                       | `kmip_id` and `owner` (JSON Body)       |
| `/kmip_register`          | `POST`      | Register a new KMIP object with a URL (barbican href), owner, and policy.| `url`, `owner`, and `policy` (JSON Body)|
| `/get_barbican_metadata`  | `GET`       | Fetch metadata for a given Barbican UUID.                | `uuid` (Query Parameter)                |
| `/update_project_id`      | `POST`      | Update the project ID for a Barbican secret.             | `secret_id` and `project_id` (JSON Body)|

---

## **API Details**

### **1. `/get_barbican_id`**
**Description**: Fetch the Barbican ID for a given KMIP ID.

- **Request**:
  ```bash
  curl 'http://localhost:5005/get_barbican_id?kmip_id=12345'
  ```

- **Response (Success)**:
  ```json
  {
      "barbican_id": "b95940ee-6320-4e47-ae86-3139a7d8ec73"
  }
  ```

- **Response (Error)**:
  ```json
  {
      "error": "No data found for the given KMIP ID"
  }
  ```

---

### **2. `/get_kmip_id`**
**Description**: Fetch the KMIP ID for a given Barbican ID.

- **Request**:
  ```bash
  curl 'http://localhost:5005/get_kmip_id?barbican_id=b95940ee-6320-4e47-ae86-3139a7d8ec73'
  ```

- **Response (Success)**:
  ```json
  {
      "kmip_id": "12345"
  }
  ```

- **Response (Error)**:
  ```json
  {
      "error": "No KMIP ID found for the given Barbican ID"
  }
  ```

---

### **3. `/get_kmip_details`**
**Description**: Fetch detailed metadata for a given KMIP ID.

- **Request**:
  ```bash
  curl 'http://localhost:5005/get_kmip_details?kmip_id=12345'
  ```

- **Response (Success)**:
  ```json
  {
      "barbican_id": "b95940ee-6320-4e47-ae86-3139a7d8ec73",
      "kmip_details": {
          "uid": "12345",
          "class_type": "SymmetricKey",
          "value": "https://example.com/kmip/12345",
          "owner": "owner@example.com",
          "operation_policy_name": "default-policy"
      }
  }
  ```

- **Response (Error)**:
  ```json
  {
      "error": "No KMIP details found for the given KMIP ID"
  }
  ```

---

### **4. `/update_policy`**
**Description**: Update the operation policy for a KMIP object.

- **Request**:
  ```bash
  curl -X POST 'http://localhost:5005/update_policy' \
  -H "Content-Type: application/json" \
  -d '{
      "kmip_id": "12345",
      "operation_policy_name": "new-policy"
  }'
  ```

- **Response (Success)**:
  ```json
  {
      "message": "Operation policy updated successfully"
  }
  ```

- **Response (Error)**:
  ```json
  {
      "error": "No KMIP object found with the given ID"
  }
  ```

---

### **5. `/update_owner`**
**Description**: Update the owner of a KMIP object.

- **Request**:
  ```bash
  curl -X POST 'http://localhost:5005/update_owner' \
  -H "Content-Type: application/json" \
  -d '{
      "kmip_id": "12345",
      "owner": "new-owner@example.com"
  }'
  ```

- **Response (Success)**:
  ```json
  {
      "message": "Owner updated successfully"
  }
  ```

- **Response (Error)**:
  ```json
  {
      "error": "No KMIP object found with the given ID"
  }
  ```

---

### **6. `/kmip_register`**
**Description**: Register a new KMIP object.

- **Request**:
  ```bash
  curl -X POST 'http://localhost:5005/kmip_register' \
  -H "Content-Type: application/json" \
  -d '{
      "url": "https://example.com/kmip/12345",
      "owner": "owner@example.com",
      "policy": "default-policy"
  }'
  ```

- **Response (Success)**:
  ```json
  {
      "message": "KMIP object registered successfully",
      "uid": "12345"
  }
  ```

- **Response (Error)**:
  ```json
  {
      "error": "KMIP registration failed"
  }
  ```

---

### **7. `/get_barbican_metadata`**
**Description**: Fetch metadata for a given Barbican UUID.

- **Request**:
  ```bash
  curl 'http://localhost:5005/get_barbican_metadata?uuid=b95940ee-6320-4e47-ae86-3139a7d8ec73'
  ```

- **Response (Success)**:
  ```json
  {
      "metadata": {
          "id": "b95940ee-6320-4e47-ae86-3139a7d8ec73",
          "name": "Test Secret",
          "type": "symmetric-key",
          "metadata": "{\"purpose\": \"encryption\", \"size\": 256}"
      }
  }
  ```

- **Response (Error)**:
  ```json
  {
      "error": "No metadata found for the given UUID"
  }
  ```

---

### **8. `/update_project_id`**
**Description**: Update the project ID for a Barbican secret.

- **Request**:
  ```bash
  curl -X POST 'http://localhost:5005/update_project_id' \
  -H "Content-Type: application/json" \
  -d '{
      "secret_id": "b95940ee-6320-4e47-ae86-3139a7d8ec73",
      "project_id": "new-project-id"
  }'
  ```

- **Response (Success)**:
  ```json
  {
      "message": "Project ID updated successfully"
  }
  ```

- **Response (Error)**:
  ```json
  {
      "error": "No secret found with the given ID"
  }
  ```

Example output from a pod in monsoon3 domain :

```
curl -X POST 'http://kmip-barbican:5005/update_project_id'       -H "Content-Type: application/json"       -d '{"secret_id": "cc2ed8f9-b17b-477c-9845-fd85486a4f28", "project_id": "ccbd3829f5314b9c937a4990c952fe03"}'
{"message":"Project ID updated successfully"}
```

---
