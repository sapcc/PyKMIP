#!/usr/bin/env python3
"""
KMIP REST API end-to-end smoke test.

Exercises all 7 REST endpoints (3 GET + 4 POST) against a running
kmip-restapi instance and reports pass/fail per endpoint.

Auth: every endpoint except /healthz needs a Keystone token whose scope
grants the `keymanager_admin` role. Supply it via OS_TOKEN.

Target + token (env):
  BASE_URL   REST API base URL            (default http://localhost:5005)
  OS_TOKEN   Keystone token (Bearer)      (default empty -> requests 401)

Test fixtures (env, default to known-good qa-de-1 data; override per region):
  KMIP_ID BARBICAN_ID BARBICAN_UUID BARBICAN_URL OWNER POLICY PROJECT_ID

Usage:
  # Port-forward the service, then run with a token:
  kubectl --context qa-de-1 -n monsoon3 port-forward svc/kmip-barbican 5005:5005 &
  export OS_TOKEN=$(openstack token issue -f value -c id)
  export BASE_URL=http://localhost:5005
  python3 kmip_e2e_tests.py

  # Against another region, override the fixtures:
  BASE_URL=http://localhost:5005 OS_TOKEN=$(openstack token issue -f value -c id) \
    KMIP_ID=123 BARBICAN_ID=... BARBICAN_UUID=... OWNER=... PROJECT_ID=... \
    python3 kmip_e2e_tests.py

Notes:
  * Tests 4, 5 and 7 are no-ops (they write the value the object already has).
  * Test 6 (kmip_register) is NOT idempotent: it inserts a new managed object
    on every run. Use a throwaway/known URL and clean up if needed.

Exit code: 0 if all tests pass, 1 otherwise.
"""

import json
import logging
import os
import subprocess
import sys

LOG_FILE = "kmip_api.log"
BASE_URL = os.getenv("BASE_URL", "http://localhost:5005")
OS_TOKEN = os.getenv("OS_TOKEN", "")

# Test fixtures — default to known-good qa-de-1 data, override via env per region.
KMIP_ID       = os.getenv("KMIP_ID", "402")
BARBICAN_ID   = os.getenv("BARBICAN_ID", "2c895f23-2315-4fa6-8286-d632c88491b4")
BARBICAN_UUID = os.getenv("BARBICAN_UUID", "7ce3c41c-8b9f-42fe-9381-f82002d53a02")
BARBICAN_URL  = os.getenv(
    "BARBICAN_URL",
    f"https://keymanager-3.qa-de-1.cloud.sap:443/v1/secrets/{BARBICAN_ID}",
)
OWNER         = os.getenv("OWNER", "vc-d-0.cc.qa-de-1.cloud.sap")
POLICY        = os.getenv("POLICY", "example")
PROJECT_ID    = os.getenv("PROJECT_ID", "e9141fb24eee4b3e9f25ae69cda31132")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

passed = 0
failed = 0


def run_test(name, cmd):
    global passed, failed
    separator = "-" * 49
    logger.info("Starting: %s", name)
    logger.info("Executing: %s", " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        response = result.stdout.strip()
        http_ok = True
        try:
            body = json.loads(response)
            if "error" in body:
                http_ok = False
        except json.JSONDecodeError:
            http_ok = bool(response)

        status = "PASSED" if http_ok else "FAILED (error in response)"
        logger.info("Status: %s", status)
        logger.info("Response: %s", response)
        if http_ok:
            passed += 1
        else:
            failed += 1
    except subprocess.TimeoutExpired:
        logger.info("Status: FAILED (timeout)")
        failed += 1
    except Exception as e:
        logger.info("Status: FAILED (%s)", e)
        failed += 1

    logger.info(separator)


def curl_get(url):
    cmd = ["curl", "-s", "--max-time", "8", url]
    if OS_TOKEN:
        cmd += ["-H", f"Authorization: Bearer {OS_TOKEN}"]
    return cmd


def curl_post(url, payload):
    cmd = ["curl", "-s", "--max-time", "8", "-X", "POST", url,
           "-H", "Content-Type: application/json",
           "-d", json.dumps(payload)]
    if OS_TOKEN:
        cmd += ["-H", f"Authorization: Bearer {OS_TOKEN}"]
    return cmd


def wait_for_port(host, port, retries=10, delay=0.5):
    import socket, time
    for _ in range(retries):
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(delay)
    return False


if __name__ == "__main__":
    # Mirror output to a log file alongside stdout.
    log_handler = logging.FileHandler(LOG_FILE, mode="w")
    log_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(log_handler)

    if not OS_TOKEN:
        logger.warning("OS_TOKEN is empty — every endpoint will return 401. "
                       "Set OS_TOKEN to a keymanager_admin-scoped token.")

    # Wait for port-forward / service to be reachable.
    from urllib.parse import urlparse
    parsed = urlparse(BASE_URL)
    host = parsed.hostname
    port = parsed.port or 80
    if not wait_for_port(host, port):
        logger.error("Cannot reach %s:%s — is the port-forward running?", host, port)
        sys.exit(1)

    logger.info("KMIP REST API E2E Tests — %s", BASE_URL)
    logger.info("=" * 49)

    # 1. GET: resolve KMIP ID -> Barbican ID
    run_test(
        "Get Barbican ID from KMIP ID",
        curl_get(f"{BASE_URL}/kmip/get_barbican_id?kmip_id={KMIP_ID}"),
    )

    # 2. GET: resolve Barbican ID -> KMIP ID
    run_test(
        "Get KMIP ID from Barbican ID",
        curl_get(f"{BASE_URL}/kmip/get_kmip_id_from_barbican?barbican_id={BARBICAN_ID}"),
    )

    # 3. GET: fetch Barbican secret metadata
    run_test(
        "Get Barbican metadata by UUID",
        curl_get(f"{BASE_URL}/barbican/get_barbican_metadata?uuid={BARBICAN_UUID}"),
    )

    # 4. POST: update operation policy (no-op — same value)
    run_test(
        "Update operation policy (no-op)",
        curl_post(f"{BASE_URL}/kmip/update_policy", {
            "kmip_id": KMIP_ID,
            "operation_policy_name": POLICY,
        }),
    )

    # 5. POST: update owner (no-op — same value)
    run_test(
        "Update owner (no-op)",
        curl_post(f"{BASE_URL}/kmip/update_owner", {
            "kmip_id": KMIP_ID,
            "new_owner": OWNER,
        }),
    )

    # 6. POST: register a KMIP object (maps barbican URL -> new KMIP ID).
    #    NOT idempotent: inserts a new managed object on every run.
    run_test(
        "Register KMIP object",
        curl_post(f"{BASE_URL}/kmip/kmip_register", {
            "url": BARBICAN_URL,
            "owner": OWNER,
            "policy": POLICY,
        }),
    )

    # 7. POST: update project ID on a barbican secret (no-op — same value).
    #    NOTE: secret_id must be a real Barbican secret UUID (BARBICAN_UUID),
    #    not the KMIP-side value (BARBICAN_ID). The barbican `secrets` table
    #    keys on BARBICAN_UUID; BARBICAN_ID is only the value stored in KMIP.
    run_test(
        "Update barbican secret project ID (no-op)",
        curl_post(f"{BASE_URL}/barbican/update_project_id", {
            "secret_id": BARBICAN_UUID,
            "project_id": PROJECT_ID,
        }),
    )

    logger.info("Results: %d passed, %d failed out of 7 tests.", passed, failed)
    logger.info("Log written to: %s", LOG_FILE)
    sys.exit(0 if failed == 0 else 1)
