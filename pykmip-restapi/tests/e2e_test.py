#!/usr/bin/env python3
"""
End-to-end tests for the pykmip-restapi service.

Required env vars:
  KMIP_API_URL              Base URL, e.g. https://kmip.cc.qa-de-1.cloud.sap
  KMIP_TOKEN                Keystone Bearer token with keymanager_admin role

Optional env vars:
  KMIP_TEST_BARBICAN_ID     Real Barbican secret UUID; when set the barbican
                            endpoints are verified against live DB data
  KMIP_TEST_PROJECT_ID      External project ID for update_project_id
                            (only used together with KMIP_TEST_BARBICAN_ID)

Usage:
  export KMIP_API_URL=https://kmip.cc.qa-de-1.cloud.sap
  export KMIP_TOKEN=$(openstack token issue -f value -c id)
  python pykmip-restapi/tests/e2e_test.py
"""
import os
import sys
import uuid
import requests

BASE_URL = os.environ.get("KMIP_API_URL", "").rstrip("/")
TOKEN = os.environ.get("KMIP_TOKEN", "")
BARBICAN_ID = os.environ.get("KMIP_TEST_BARBICAN_ID", "")
PROJECT_ID = os.environ.get("KMIP_TEST_PROJECT_ID", "")

AUTH_HDRS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
NO_AUTH_HDRS = {"Content-Type": "application/json"}

results: list = []  # list of (name, ok)


def _check(name: str, ok: bool, detail: str = "") -> None:
    label = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    print(f"  [{label}] {name}")
    if not ok and detail:
        print(f"         {detail}")
    results.append((name, ok))


def _get(path, params=None, headers=None):
    return requests.get(
        f"{BASE_URL}{path}",
        headers=headers if headers is not None else AUTH_HDRS,
        params=params,
        timeout=15,
    )


def _post(path, body, headers=None):
    return requests.post(
        f"{BASE_URL}{path}",
        headers=headers if headers is not None else AUTH_HDRS,
        json=body,
        timeout=15,
    )


def run():
    if not BASE_URL:
        print("ERROR: KMIP_API_URL is not set", file=sys.stderr)
        sys.exit(2)
    if not TOKEN:
        print("ERROR: KMIP_TOKEN is not set", file=sys.stderr)
        sys.exit(2)

    print(f"\nE2E tests → {BASE_URL}\n")

    test_url = f"https://barbican.e2e.test/v1/secrets/{uuid.uuid4()}"
    test_uuid = test_url.rsplit("/", 1)[-1]
    registered_kmip_id = None

    # ------------------------------------------------------------------ #
    # 1. Health check
    # ------------------------------------------------------------------ #
    print("1. Health check")
    r = requests.get(f"{BASE_URL}/healthz", timeout=10)
    _check("GET /healthz → 200", r.status_code == 200, r.text)
    _check('GET /healthz → {"status": "ok"}', r.json().get("status") == "ok", r.text)

    # ------------------------------------------------------------------ #
    # 2. Register KMIP object
    # ------------------------------------------------------------------ #
    print("\n2. Register KMIP object")
    r = _post("/kmip/kmip_register", {
        "url": test_url,
        "owner": "e2e-test-project",
        "policy": "default",
    })
    ok = r.status_code == 200 and "uid" in r.json()
    _check("POST /kmip/kmip_register → 200 with uid", ok, r.text)
    if ok:
        registered_kmip_id = str(r.json()["uid"])
        print(f"         kmip_id = {registered_kmip_id}")

    # ------------------------------------------------------------------ #
    # 3. Get Barbican ID from KMIP ID
    # ------------------------------------------------------------------ #
    print("\n3. Get Barbican ID from KMIP ID")
    if registered_kmip_id:
        r = _get("/kmip/get_barbican_id", params={"kmip_id": registered_kmip_id})
        _check("GET /kmip/get_barbican_id → 200", r.status_code == 200, r.text)
        _check("GET /kmip/get_barbican_id → has barbican_id field", "barbican_id" in r.json(), r.text)
        _check(
            "GET /kmip/get_barbican_id → barbican_id matches registered UUID",
            r.json().get("barbican_id") == test_uuid,
            r.text,
        )
    else:
        _check("GET /kmip/get_barbican_id (skipped — register step failed)", True)

    # ------------------------------------------------------------------ #
    # 4. Get KMIP ID from Barbican ID (reverse lookup)
    # ------------------------------------------------------------------ #
    print("\n4. Reverse lookup: KMIP ID from Barbican ID")
    r = _get("/kmip/get_kmip_id_from_barbican", params={"barbican_id": test_uuid})
    _check("GET /kmip/get_kmip_id_from_barbican → 200", r.status_code == 200, r.text)
    if registered_kmip_id:
        _check(
            "GET /kmip/get_kmip_id_from_barbican → matches registered kmip_id",
            str(r.json().get("kmip_id")) == registered_kmip_id,
            r.text,
        )

    # ------------------------------------------------------------------ #
    # 5. Update operation policy
    # ------------------------------------------------------------------ #
    print("\n5. Update operation policy")
    if registered_kmip_id:
        r = _post("/kmip/update_policy", {
            "kmip_id": registered_kmip_id,
            "operation_policy_name": "e2e-test-policy",
        })
        _check("POST /kmip/update_policy → 200", r.status_code == 200, r.text)
        _check("POST /kmip/update_policy → has message", "message" in r.json(), r.text)
    else:
        _check("POST /kmip/update_policy (skipped — register step failed)", True)

    # ------------------------------------------------------------------ #
    # 6. Update owner
    # ------------------------------------------------------------------ #
    print("\n6. Update owner")
    if registered_kmip_id:
        r = _post("/kmip/update_owner", {
            "kmip_id": registered_kmip_id,
            "new_owner": "e2e-test-project-updated",
        })
        _check("POST /kmip/update_owner → 200", r.status_code == 200, r.text)
        _check("POST /kmip/update_owner → has message", "message" in r.json(), r.text)
    else:
        _check("POST /kmip/update_owner (skipped — register step failed)", True)

    # ------------------------------------------------------------------ #
    # 7. Barbican metadata
    # ------------------------------------------------------------------ #
    print("\n7. Barbican metadata")
    lookup_id = BARBICAN_ID if BARBICAN_ID else test_uuid
    r = _get("/barbican/get_barbican_metadata", params={"uuid": lookup_id})
    _check("GET /barbican/get_barbican_metadata → 200", r.status_code == 200, r.text)
    if BARBICAN_ID:
        _check("GET /barbican/get_barbican_metadata → has data", "data" in r.json(), r.text)
    else:
        _check(
            "GET /barbican/get_barbican_metadata → responds with data or error",
            "data" in r.json() or "error" in r.json(),
            r.text,
        )

    # ------------------------------------------------------------------ #
    # 8. Update Barbican project ID
    # ------------------------------------------------------------------ #
    print("\n8. Update Barbican project ID")
    if BARBICAN_ID and PROJECT_ID:
        r = _post("/barbican/update_project_id", {
            "secret_id": BARBICAN_ID,
            "project_id": PROJECT_ID,
        })
        _check("POST /barbican/update_project_id → 200", r.status_code == 200, r.text)
        _check("POST /barbican/update_project_id → has message", "message" in r.json(), r.text)
    else:
        # Probe reachability with a synthetic UUID — service returns 200 + error body
        r = _post("/barbican/update_project_id", {
            "secret_id": test_uuid,
            "project_id": "e2e-test-project",
        })
        _check(
            "POST /barbican/update_project_id → reachable (200)",
            r.status_code == 200,
            r.text,
        )

    # ------------------------------------------------------------------ #
    # 9. Auth validation
    # ------------------------------------------------------------------ #
    print("\n9. Auth validation (unauthenticated requests)")
    r = _get("/kmip/get_barbican_id", params={"kmip_id": "1"}, headers=NO_AUTH_HDRS)
    _check("GET /kmip/get_barbican_id without token → 401", r.status_code == 401, r.text)
    r = _post("/kmip/kmip_register", {"url": "x", "owner": "y", "policy": "z"}, headers=NO_AUTH_HDRS)
    _check("POST /kmip/kmip_register without token → 401", r.status_code == 401, r.text)
    r = _get("/barbican/get_barbican_metadata", params={"uuid": "x"}, headers=NO_AUTH_HDRS)
    _check("GET /barbican/get_barbican_metadata without token → 401", r.status_code == 401, r.text)

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    verdict = "\033[32m✓ all good\033[0m" if not failed else f"\033[31m✗ {failed} failed\033[0m"
    print(f"\n{'=' * 55}")
    print(f"  {passed}/{total} passed  {verdict}")
    print(f"{'=' * 55}\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run()
