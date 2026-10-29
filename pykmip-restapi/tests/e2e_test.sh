#!/usr/bin/env bash
# End-to-end tests for pykmip-restapi.
#
# Tests all 8 API endpoints using curl. Requires no Python — runs from any
# shell with curl and jq available (e.g. a netshoot diagnostic pod).
#
# Required env vars:
#   KMIP_API_URL   Base URL of the service
#                    inside the cluster: http://kmip-barbican:5005
#                    via ingress:        https://kmip.cc.<region>.cloud.sap
#   KMIP_TOKEN     Keystone Bearer token with keymanager_admin role
#
# Optional env vars:
#   KMIP_TEST_BARBICAN_ID    Real Barbican secret UUID — when set, the
#                            barbican endpoints verify live DB data
#   KMIP_TEST_PROJECT_ID     New project external_id used in
#                            update_project_id (requires BARBICAN_ID)
#
# ── Running from inside the QA cluster (recommended) ──────────────────────
#
#   1. Get a Keystone token:
#        source ~/Downloads/openrc-monsoon3-cc-demo-qa-de-1-tm3
#        TOKEN=$(openstack token issue -f value -c id)
#
#   2. Pipe this script into a netshoot pod:
#        kubectl -n monsoon3 run e2e-$RANDOM --rm -i --restart=Never \\
#          --image=keppel.global.cloud.sap/ccloud-dockerhub-mirror/nicolaka/netshoot \\
#          --env="KMIP_API_URL=http://kmip-barbican:5005" \\
#          --env="KMIP_TOKEN=$TOKEN" \\
#          -- bash -s < pykmip-restapi/tests/e2e_test.sh
#
# ── Running locally (requires VPN / direct route to the service) ──────────
#
#        KMIP_API_URL=https://kmip.cc.qa-de-1.cloud.sap \\
#          KMIP_TOKEN=$(openstack token issue -f value -c id) \\
#          bash pykmip-restapi/tests/e2e_test.sh
#
# ── GitHub Actions ────────────────────────────────────────────────────────
#
#   The e2e.yml workflow runs this script when KMIP_E2E_TOKEN and
#   KMIP_E2E_URL secrets are configured in the repository settings.
#   Public runners cannot reach the internal endpoint; use a self-hosted
#   runner with VPN/kubeconfig access for automated runs.
#   Secrets to configure:
#     KMIP_E2E_URL    e.g. https://kmip.cc.qa-de-1.cloud.sap
#     KMIP_E2E_TOKEN  Keystone Bearer token (long-lived service token)
# ──────────────────────────────────────────────────────────────────────────

set -uo pipefail

BASE_URL="${KMIP_API_URL:-}"
TOKEN="${KMIP_TOKEN:-}"
BARBICAN_ID="${KMIP_TEST_BARBICAN_ID:-}"
PROJECT_ID="${KMIP_TEST_PROJECT_ID:-}"

if [ -z "$BASE_URL" ]; then
  echo "ERROR: KMIP_API_URL is not set" >&2; exit 2
fi
if [ -z "$TOKEN" ]; then
  echo "ERROR: KMIP_TOKEN is not set" >&2; exit 2
fi

AUTH="Authorization: Bearer $TOKEN"
PASS=0; FAIL=0
TMP=/tmp/e2e_body

chk() {
  local name="$1" expected="$2" actual="$3" body="${4:-}"
  if [ "$actual" = "$expected" ]; then
    printf "  [PASS] %s\n" "$name"; PASS=$((PASS + 1))
  else
    printf "  [FAIL] %s (expected %s, got %s)\n" "$name" "$expected" "$actual"
    [ -n "$body" ] && printf "         %s\n" "$body"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== E2E tests -> $BASE_URL ==="

# 1. Health check
echo ""
echo "1. Health check"
r=$(curl -s -o $TMP -w "%{http_code}" "$BASE_URL/healthz")
chk "GET /healthz -> 200" 200 "$r" "$(cat $TMP)"

# 2. Register a KMIP object
echo ""
echo "2. Register KMIP object"
UUID=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]')
r=$(curl -s -o $TMP -w "%{http_code}" -X POST "$BASE_URL/kmip/kmip_register" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"url\":\"https://barbican.e2e.test/v1/secrets/$UUID\",\"owner\":\"e2e-test\",\"policy\":\"default\"}")
chk "POST /kmip/kmip_register -> 200" 200 "$r" "$(cat $TMP)"
KMIP_ID=$(jq -r ".uid // empty" $TMP 2>/dev/null)
echo "   kmip_id=$KMIP_ID"

# 3. Get Barbican ID from KMIP ID
echo ""
echo "3. Get Barbican ID from KMIP ID"
r=$(curl -s -o $TMP -w "%{http_code}" "$BASE_URL/kmip/get_barbican_id?kmip_id=$KMIP_ID" -H "$AUTH")
chk "GET /kmip/get_barbican_id -> 200" 200 "$r" "$(cat $TMP)"
echo "   body: $(cat $TMP)"

# 4. Get KMIP ID from Barbican ID (reverse lookup)
echo ""
echo "4. Reverse lookup: KMIP ID from Barbican ID"
r=$(curl -s -o $TMP -w "%{http_code}" "$BASE_URL/kmip/get_kmip_id_from_barbican?barbican_id=$UUID" -H "$AUTH")
chk "GET /kmip/get_kmip_id_from_barbican -> 200" 200 "$r" "$(cat $TMP)"
echo "   body: $(cat $TMP)"

# 5. Update operation policy
echo ""
echo "5. Update operation policy"
r=$(curl -s -o $TMP -w "%{http_code}" -X POST "$BASE_URL/kmip/update_policy" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"kmip_id\":\"$KMIP_ID\",\"operation_policy_name\":\"e2e-test-policy\"}")
chk "POST /kmip/update_policy -> 200" 200 "$r" "$(cat $TMP)"

# 6. Update owner
echo ""
echo "6. Update owner"
r=$(curl -s -o $TMP -w "%{http_code}" -X POST "$BASE_URL/kmip/update_owner" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"kmip_id\":\"$KMIP_ID\",\"new_owner\":\"e2e-updated\"}")
chk "POST /kmip/update_owner -> 200" 200 "$r" "$(cat $TMP)"

# 7. Barbican metadata
# With a real KMIP_TEST_BARBICAN_ID the response has "data"; with a synthetic
# UUID the service returns 200 with {"error": "not found"} — both are 200.
echo ""
echo "7. Barbican metadata"
LOOKUP_ID="${BARBICAN_ID:-$UUID}"
r=$(curl -s -o $TMP -w "%{http_code}" "$BASE_URL/barbican/get_barbican_metadata?uuid=$LOOKUP_ID" -H "$AUTH")
chk "GET /barbican/get_barbican_metadata -> 200" 200 "$r" "$(cat $TMP)"
echo "   body: $(cat $TMP)"

# 8. Update Barbican project ID
# Same: with real IDs this mutates the DB; with synthetic UUID service
# returns 200 + error body.
echo ""
echo "8. Update Barbican project ID"
if [ -n "$BARBICAN_ID" ] && [ -n "$PROJECT_ID" ]; then
  r=$(curl -s -o $TMP -w "%{http_code}" -X POST "$BASE_URL/barbican/update_project_id" \
    -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"secret_id\":\"$BARBICAN_ID\",\"project_id\":\"$PROJECT_ID\"}")
else
  r=$(curl -s -o $TMP -w "%{http_code}" -X POST "$BASE_URL/barbican/update_project_id" \
    -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"secret_id\":\"$UUID\",\"project_id\":\"e2e-project\"}")
fi
chk "POST /barbican/update_project_id -> 200" 200 "$r" "$(cat $TMP)"
echo "   body: $(cat $TMP)"

# 9. Auth validation — all protected endpoints must reject requests without a token
echo ""
echo "9. Auth validation (no token)"
r=$(curl -s -o $TMP -w "%{http_code}" "$BASE_URL/kmip/get_barbican_id?kmip_id=1")
chk "GET /kmip/get_barbican_id no-auth -> 401" 401 "$r" "$(cat $TMP)"
r=$(curl -s -o $TMP -w "%{http_code}" -X POST "$BASE_URL/kmip/kmip_register" \
  -H "Content-Type: application/json" -d "{\"url\":\"x\",\"owner\":\"y\",\"policy\":\"z\"}")
chk "POST /kmip/kmip_register no-auth -> 401" 401 "$r" "$(cat $TMP)"
r=$(curl -s -o $TMP -w "%{http_code}" "$BASE_URL/barbican/get_barbican_metadata?uuid=x")
chk "GET /barbican/get_barbican_metadata no-auth -> 401" 401 "$r" "$(cat $TMP)"

# Summary
echo ""
echo "=============================="
printf "  %d passed, %d failed\n" "$PASS" "$FAIL"
echo "=============================="
[ "$FAIL" -eq 0 ]
