# REST API end-to-end smoke test

`kmip_e2e_tests.py` exercises all 7 `kmip-restapi` endpoints (3 GET + 4 POST)
against a running instance and reports pass/fail per endpoint. It's an
operational smoke test (hits a live service + databases), distinct from the
unit tests under `pykmip-restapi/tests/`.

## Prerequisites

- `python3` and `curl` on PATH (the script shells out to `curl`).
- Network access to a `kmip-restapi` instance (usually via `kubectl port-forward`).
- A Keystone token whose scope grants the **`keymanager_admin`** role — every
  endpoint except `/healthz` requires it. A valid token scoped to a project
  that lacks the role still returns `401`.

## Run

```bash
# 1. Port-forward the service (adjust context/region)
kubectl --context qa-de-1 -n monsoon3 port-forward svc/kmip-barbican 5005:5005 &

# 2. Issue a keymanager_admin-scoped token
export OS_TOKEN=$(openstack token issue -f value -c id)
export BASE_URL=http://localhost:5005

# 3. Run
python3 kmip_e2e_tests.py
```

A full transcript is written to `kmip_api.log` in the working directory.
Exit code is `0` when all 7 pass, `1` otherwise.

## Configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `BASE_URL` | `http://localhost:5005` | REST API base URL |
| `OS_TOKEN` | *(empty)* | Keystone Bearer token; empty => every call returns `401` |
| `KMIP_ID` | `402` | KMIP managed-object id (tests 1, 4, 5) |
| `BARBICAN_ID` | `2c895f23-…-d632c88491b4` | KMIP-side barbican value (test 2) |
| `BARBICAN_UUID` | `7ce3c41c-…-f82002d53a02` | real Barbican secret UUID (tests 3, 7) |
| `BARBICAN_URL` | `https://keymanager-3.qa-de-1…/{BARBICAN_ID}` | secret URL to register (test 6) |
| `OWNER` | `vc-d-0.cc.qa-de-1.cloud.sap` | KMIP owner (tests 5, 6) |
| `POLICY` | `example` | operation policy name (tests 4, 6) |
| `PROJECT_ID` | `e9141fb24…31132` | Keystone project `external_id` (test 7) |

The defaults are known-good fixtures for **qa-de-1**. For another region,
override the fixtures with ids that exist there.

## Caveats

- **Not fully read-only.** Tests 4, 5 and 7 are no-ops (they write the value
  the object already has), but **test 6 (`kmip_register`) is not idempotent** —
  it inserts a **new** managed object on every run. Point it at a throwaway
  secret URL and clean up afterward if you run it repeatedly.
- `BARBICAN_ID` vs `BARBICAN_UUID` are different things: `BARBICAN_ID` is the
  value stored on the KMIP side, while `BARBICAN_UUID` is the primary key in
  the Barbican `secrets` table. Test 7 needs the latter.
