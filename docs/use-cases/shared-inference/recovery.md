# Defend native priority and recover store-backed policy

Verify that an untrusted engine-native priority cannot bypass Gateway policy, then interrupt the policy database without confusing a readable applied policy with a writable healthy store.

<!-- example-status-default: illustrative-only -->

The first requests show exactly where a client can supply native priority and where the Gateway-neutralized result is observed. The later fault exercise uses explicit docker pause/unpause and process restart commands; change only the container names and DB flags of the isolated deployment you own.

## Before you start

Complete overload and retain the private policy/store inputs.

**Focus of this page:** Observe native priority at the backend, then pause only the owned policy DB and restart the Gateway.

## Topology and execution locations

--8<-- "snippets/use-cases/topology/shared.md"

One disposable Linux host contains two Gateway/DB containers and four network namespaces. Support reaches the Gateway on 192.0.2.254; research uses its 198.51.100.254 interface. The backend is a host Python process in share-backend, not an inference engine. PostgreSQL uses its inspected Docker-bridge address.

| Where | What happens here |
|---|---|
| Host root Bash | Create namespaces, save LAB inputs, start/stop exact owned processes. |
| share-a / share-b | Send inference as support/research; management curls use share-a. |
| share-gateway | Apply policy and forward requests; management is port 11111, inference port 8080. |
| share-backend | Read /receipt/ and /order directly, bypassing Gateway routing. |
| share-pg | Keep keys/objectives; pause only in the explicit recovery experiment. |

## Walkthrough

### Inspect native-priority sanitization at the backend

Complete [overload](overload.md). Native body `priority` and `X-Vllm-Priority` are independent of the authorized objective. On an AI Gateway path with class policy active (`ai_gw_mode` and `ai_gw_class_on()`), the Gateway strips the header and renames the literal top-level JSON key to `_gw_prio`. Objectives and class settings in this lab enable that policy; lowering bindings or JWT profiles can also enable it. A deployment without class policy can pass these native hints through unchanged, so do not assume sanitization from Gateway mode alone. Escaped spellings are neutralized with underscore padding to preserve the original wire length (the example below becomes `_gw_prio_____`). It does not rewrite priority to zero. An unrelated nested priority is preserved.

**Step 1 — Reapply the service rule with queue depth 30**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 200 for the saved management response before continuing. Write `native-priority.request.json` with the displayed editable JSON input.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
jq '.serviceArguments += {
  "fc_max_queue_depth": 30
}' \
  "$LAB/base-rule.json" > "$LAB/recovery-rule-1.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/recovery-rule-1.request.json" \
  -D "$LAB/recovery-rule-1.headers" -o "$LAB/recovery-rule-1.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-rule-1.response.json"
test "$status" = 200
cat > "$LAB/native-priority.request.json" <<'JSON'
{"model":"shared-model","messages":[{"role":"user","content":"batch"}],"max_tokens":4,"priority":-100,"metadata":{"priority":7}}
JSON
```

**Step 2 — Send `native-priority` and retain the response**

Send `native-priority` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `native-priority`. Read `native-priority` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `native-priority`. Write `escaped-native.request.json` with the displayed editable JSON input.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support-batch.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: native-priority' -H 'X-Request-Id: native-priority' \
  -H X-Vllm-Priority:-100 \
  --data-binary "@$LAB/native-priority.request.json" \
  -D "$LAB/native-priority.headers" -o "$LAB/native-priority.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/native-priority.http"
if test -f "$LAB/native-priority.pid"; then
  wait "$(cat "$LAB/native-priority.pid")"
fi
test "$(cat "$LAB/native-priority.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/native-priority" -o "$LAB/native-priority.receipt.json"
jq -e '.count == 1' "$LAB/native-priority.receipt.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/native-priority" -o "$LAB/native-priority.receipt.json"
jq . "$LAB/native-priority.receipt.json"
jq -e '(((.["headers"] | has("x-vllm-priority") | not)) and ((.["body"] | has("priority") | not)) and ((.["body"]["_gw_prio"] == -100)) and ((.["body"]["metadata"]["priority"] == 7)) and ((.["headers"]["x-llm-d-inference-objective"] == "sheddable")))' "$LAB/native-priority.receipt.json"
cat > "$LAB/escaped-native.request.json" <<'JSON'
{"model":"shared-model","messages":[{"role":"user","content":"batch"}],"max_tokens":4,"pri\u006frity":-100}
JSON
```

**Step 3 — Send `escaped-native` and retain the response**

Send `escaped-native` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `escaped-native`. Read `escaped-native` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `escaped-native`.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support-batch.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: escaped-native' -H 'X-Request-Id: escaped-native' \
  --data-binary "@$LAB/escaped-native.request.json" \
  -D "$LAB/escaped-native.headers" -o "$LAB/escaped-native.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/escaped-native.http"
if test -f "$LAB/escaped-native.pid"; then
  wait "$(cat "$LAB/escaped-native.pid")"
fi
test "$(cat "$LAB/escaped-native.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/escaped-native" -o "$LAB/escaped-native.receipt.json"
jq -e '.count == 1' "$LAB/escaped-native.receipt.json"
jq -e '(((.["body"] | has("priority") | not)) and ((.["body"]["_gw_prio_____"] == -100)))' "$LAB/escaped-native.receipt.json"
```

The synthetic backend accepts unknown JSON fields. Your real engine's schema must be compatible with renamed fields; do not claim every engine accepts `_gw_prio`. This test proves wire sanitization in H1, not GPU order or native rank mapping. Use real-engine contention and engine-side execution evidence before making engine scheduling claims.

A shared listener must keep one authentication contract across its model rules. Attempting a sibling with `disabled` must return 400 while existing keyed traffic stays healthy:

**Step 1 — Reject a keyless `other-model` sibling rule with 400**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 400 for the saved management response before continuing.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
jq '.serviceArguments += {
  "model_name": "other-model",
  "api_key_auth": "disabled"
}' \
  "$LAB/base-rule.json" > "$LAB/recovery-rule-3.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/recovery-rule-3.request.json" \
  -D "$LAB/recovery-rule-3.headers" -o "$LAB/recovery-rule-3.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-rule-3.response.json"
test "$status" = 400
```

**Step 2 — Send `after-listener-reject` and retain the response**

Write `after-listener-reject.request.json` with the displayed editable JSON input. Send `after-listener-reject` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `after-listener-reject`.

```bash
cat > "$LAB/after-listener-reject.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "after-listener-reject"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: after-listener-reject' -H 'X-Request-Id: after-listener-reject' \
  --data-binary "@$LAB/after-listener-reject.request.json" \
  -D "$LAB/after-listener-reject.headers" -o "$LAB/after-listener-reject.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/after-listener-reject.http"
if test -f "$LAB/after-listener-reject.pid"; then
  wait "$(cat "$LAB/after-listener-reject.pid")"
fi
test "$(cat "$LAB/after-listener-reject.http")" = 200
```

**Step 3 — Send `after-listener-no-key` and retain the response**

Read `after-listener-reject` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `after-listener-reject`. Write `after-listener-no-key.request.json` with the displayed editable JSON input. Send `after-listener-no-key` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/after-listener-reject" -o "$LAB/after-listener-reject.receipt.json"
jq -e '.count == 1' "$LAB/after-listener-reject.receipt.json"
cat > "$LAB/after-listener-no-key.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "after-listener-no-key"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: after-listener-no-key' -H 'X-Request-Id: after-listener-no-key' \
  --data-binary "@$LAB/after-listener-no-key.request.json" \
  -D "$LAB/after-listener-no-key.headers" -o "$LAB/after-listener-no-key.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/after-listener-no-key.http"
if test -f "$LAB/after-listener-no-key.pid"; then
  wait "$(cat "$LAB/after-listener-no-key.pid")"
fi
```

**Step 4 — Confirm `after-listener-no-key` got 401 with no receipt**

Require saved HTTP 401 for `after-listener-no-key`. Read `after-listener-no-key` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `after-listener-no-key`.

```bash
test "$(cat "$LAB/after-listener-no-key.http")" = 401
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/after-listener-no-key" -o "$LAB/after-listener-no-key.receipt.json"
jq -e '.count == 0' "$LAB/after-listener-no-key.receipt.json"
```

### Store failure, last-known-good policy and recovery

Set a trusted support ingress binding and persist configuration before interrupting this lab's database. Pause only share-pg. Current builds bound management store operations (default 3000 ms) and readiness pings (default 1000 ms). Keep the 10-second curl timeout longer than those server budgets when adapting the exercise.

A management write can return **503 `ai_key_store_unavailable`** when it was not sent, or **504 `ai_key_store_outcome_unknown`** when it was sent but its result is unknown. A 504 may still be followed by a commit after the store recovers: preserve the response and read back before retrying. This management 504 is distinct from an inference `admission_queue_timeout`. The objective list can still return 200 for applied policy; inspect `store_reachable` and `source` separately. HTTP000 or a nonzero curl exit is a transport/client failure, not an expected policy response and not a successful exercise result.

**Step 1 — Create the `recovery-interface` network binding**

Write `recovery-config-5.request.json` with the displayed editable JSON input. Send the displayed management request to `/config/ai/netidentity` and retain its response.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
cat > "$LAB/recovery-config-5.request.json" <<'JSON'
{
  "name": "recovery-interface",
  "match": {
    "ingress_if": "ga"
  },
  "tenant": "support",
  "services": [
    "192.0.2.254:8080"
  ],
  "credential": "network",
  "enforce": "strict",
  "forward_identity": true
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/recovery-config-5.request.json" \
  -D "$LAB/recovery-config-5.headers" -o "$LAB/recovery-config-5.response.json" \
  -w '%{http_code}' "$API/config/ai/netidentity")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-5.response.json"
```

**Step 2 — Send `before-store-outage` and retain the response**

Require HTTP 200 for the saved management response before continuing. Write `before-store-outage.request.json` with the displayed editable JSON input. Send `before-store-outage` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `before-store-outage`.

```bash
test "$status" = 200
sleep 3
cat > "$LAB/before-store-outage.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "before-store-outage"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: before-store-outage' -H 'X-Request-Id: before-store-outage' \
  --data-binary "@$LAB/before-store-outage.request.json" \
  -D "$LAB/before-store-outage.headers" -o "$LAB/before-store-outage.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/before-store-outage.http"
if test -f "$LAB/before-store-outage.pid"; then
  wait "$(cat "$LAB/before-store-outage.pid")"
fi
test "$(cat "$LAB/before-store-outage.http")" = 200
```

**Step 3 — Confirm `before-store-outage` delivery and persist configuration**

Read `before-store-outage` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `before-store-outage`. Write `recovery-config-6.request.json` with the displayed editable JSON input. Send the displayed management request to `/config/persist` and retain its response. Require HTTP 200 for the saved management response before continuing.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/before-store-outage" -o "$LAB/before-store-outage.receipt.json"
jq -e '.count == 1' "$LAB/before-store-outage.receipt.json"
cat > "$LAB/recovery-config-6.request.json" <<'JSON'
{}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/recovery-config-6.request.json" \
  -D "$LAB/recovery-config-6.headers" -o "$LAB/recovery-config-6.response.json" \
  -w '%{http_code}' "$API/config/persist")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-6.response.json"
test "$status" = 200
sleep 12
# On any unexpected lab-shell failure, restore only this lab-owned DB.
```

**Step 4 — Interrupt the owned policy store and observe failure**

Pause only the owned `share-pg` database for the store-failure observation; keep the ownership-checked recovery trap active. Write `recovery-config-7.request.json` with the displayed editable JSON input.

```bash
restore_db_on_failure() {
  rc=$?
  trap - EXIT
  if test "$rc" -ne 0 &&
     test "$(docker inspect -f '{{index .Config.Labels "shared-lab"}}' share-pg)" = "$LAB" &&
     test "$(docker inspect -f '{{.State.Paused}}' share-pg)" = true; then
    docker unpause share-pg
  fi
  exit "$rc"
}
trap restore_db_on_failure EXIT
docker pause share-pg
sleep 12
cat > "$LAB/recovery-config-7.request.json" <<'JSON'
{
  "name": "outage-write-check",
  "priority": 1
}
JSON
write_curl_exit=0
```

**Step 5 — Attempt the `outage-write-check` objective write while paused**

Send the displayed management request to `/config/ai/objective` and retain its response.

```bash
if status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/recovery-config-7.request.json" \
  -D "$LAB/recovery-config-7.headers" -o "$LAB/recovery-config-7.response.json" \
  -w '%{http_code}' "$API/config/ai/objective"); then
  :
else
  write_curl_exit=$?
fi
printf 'HTTP %s\n' "$status"
jq -n --arg http "$status" --argjson curl_exit "$write_curl_exit" \
  '{http:$http,curl_exit:$curl_exit}' > "$LAB/paused-write-observation.json"
# Require a real Gateway response; never accept HTTP000 as a denial.
test "$write_curl_exit" -eq 0
```

**Step 6 — Check the 503/504 write error and unreachable store**

Check that the paused write from Step 5 failed with either 503 `ai_key_store_unavailable` or 504 `ai_key_store_outcome_unknown`; any other status stops the lab. Then read `/config/ai/objective`, require HTTP 200, and require `store_reachable` to be `false`.

```bash
case "$status" in
  503)
    jq -e '.code == 503 and .message == "ai_key_store_unavailable"' \
      "$LAB/recovery-config-7.response.json"
    ;;
  504)
    jq -e '.code == 504 and .message == "ai_key_store_outcome_unknown"' \
      "$LAB/recovery-config-7.response.json"
    ;;
  *)
    printf 'Unexpected store-write response: HTTP %s\n' "$status" >&2
    exit 1
    ;;
esac
status=$(ip netns exec share-a curl -sS --max-time 10 -X GET \
  -D "$LAB/recovery-config-8.headers" -o "$LAB/recovery-config-8.response.json" \
  -w '%{http_code}' "$API/config/ai/objective")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-8.response.json"
test "$status" = 200
jq -e '.store_reachable == false' "$LAB/recovery-config-8.response.json"
```

**Step 7 — Send `live-network-policy` and retain the response**

Write `live-network-policy.request.json` with the displayed editable JSON input. Send `live-network-policy` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `live-network-policy`. Read `live-network-policy` directly from the backend receipt endpoint; this observation bypasses the Gateway.

```bash
cat > "$LAB/live-network-policy.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "live-network-policy"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: live-network-policy' -H 'X-Request-Id: live-network-policy' \
  --data-binary "@$LAB/live-network-policy.request.json" \
  -D "$LAB/live-network-policy.headers" -o "$LAB/live-network-policy.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/live-network-policy.http"
if test -f "$LAB/live-network-policy.pid"; then
  wait "$(cat "$LAB/live-network-policy.pid")"
fi
test "$(cat "$LAB/live-network-policy.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/live-network-policy" -o "$LAB/live-network-policy.receipt.json"
```

**Step 8 — Restart the Gateway process and expect readiness 503**

Require backend receipt count 1 for `live-network-policy`. Confirm that `share-gateway` belongs to this lab, then stop its loxilb process with `kill -9` and start it again while the policy store is still paused. Require HTTP 503 from `/status/ready`, then read `/config/ai/objective` and retain its response.

```bash
jq -e '.count == 1' "$LAB/live-network-policy.receipt.json"
test "$(docker inspect -f '{{index .Config.Labels "shared-lab"}}' share-gateway)" = "$LAB"
GATEWAY_PROCESS=$(docker exec share-gateway pidof loxilb)
docker exec share-gateway kill -9 "$GATEWAY_PROCESS"
docker exec -d share-gateway sh -c '
exec /root/loxilb-io/loxilb/loxilb -p --sockmapsupport --loglevel debug \
  --mgmt-db-host "$1" --mgmt-db-port 5432 --mgmt-db-user aigw_mgmt_user \
  --mgmt-db-name loxilb --mgmt-db-password-file /opt/loxilb/cert/mgmt-password \
  --aikey-db-host "$1" --aikey-db-port 5432 --aikey-db-user aigwuser \
  --aikey-db-name loxilb --aikey-db-password-file /opt/loxilb/cert/dp-password \
  > /tmp/gateway.out 2> /tmp/gateway.err
' sh "$PG_IP"
sleep 12
status=$(ip netns exec share-a curl -sS --max-time 10 -X GET \
  -D "$LAB/recovery-config-9.headers" -o "$LAB/recovery-config-9.response.json" \
  -w '%{http_code}' "$API/status/ready")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-9.response.json"
test "$status" = 503
status=$(ip netns exec share-a curl -sS --max-time 10 -X GET \
  -D "$LAB/recovery-config-10.headers" -o "$LAB/recovery-config-10.response.json" \
  -w '%{http_code}' "$API/config/ai/objective")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-10.response.json"
```

**Step 9 — Confirm objectives load from LKG with the store unreachable**

Require HTTP 200 for the saved management response before continuing. Send the displayed management request to `/config/ai/objective` and retain its response. Write `cold-key-store.request.json` with the displayed editable JSON input.

```bash
test "$status" = 200
status=$(ip netns exec share-a curl -sS --max-time 10 -X GET \
  -D "$LAB/recovery-config-11.headers" -o "$LAB/recovery-config-11.response.json" \
  -w '%{http_code}' "$API/config/ai/objective")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-11.response.json"
test "$status" = 200
jq -e '.source == "lkg" and .store_reachable == false' "$LAB/recovery-config-11.response.json"
cat > "$LAB/cold-key-store.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "cold-key-store"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 10 — Send `cold-key-store` and retain the response**

Send `cold-key-store` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 503 for `cold-key-store`. Read `cold-key-store` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `cold-key-store`.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: cold-key-store' -H 'X-Request-Id: cold-key-store' \
  --data-binary "@$LAB/cold-key-store.request.json" \
  -D "$LAB/cold-key-store.headers" -o "$LAB/cold-key-store.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/cold-key-store.http"
if test -f "$LAB/cold-key-store.pid"; then
  wait "$(cat "$LAB/cold-key-store.pid")"
fi
test "$(cat "$LAB/cold-key-store.http")" = 503
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/cold-key-store" -o "$LAB/cold-key-store.receipt.json"
jq -e '.count == 0' "$LAB/cold-key-store.receipt.json"
```

**Step 11 — Send `recovered-network-lkg` and retain the response**

Write `recovered-network-lkg.request.json` with the displayed editable JSON input. Send `recovered-network-lkg` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `recovered-network-lkg`. Read `recovered-network-lkg` directly from the backend receipt endpoint; this observation bypasses the Gateway.

```bash
cat > "$LAB/recovered-network-lkg.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "recovered-network-lkg"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: recovered-network-lkg' -H 'X-Request-Id: recovered-network-lkg' \
  --data-binary "@$LAB/recovered-network-lkg.request.json" \
  -D "$LAB/recovered-network-lkg.headers" -o "$LAB/recovered-network-lkg.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/recovered-network-lkg.http"
if test -f "$LAB/recovered-network-lkg.pid"; then
  wait "$(cat "$LAB/recovered-network-lkg.pid")"
fi
test "$(cat "$LAB/recovered-network-lkg.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/recovered-network-lkg" -o "$LAB/recovered-network-lkg.receipt.json"
```

**Step 12 — Confirm `recovered-network-lkg` reached the backend**

Require backend receipt count 1 for `recovered-network-lkg`.

```bash
jq -e '.count == 1' "$LAB/recovered-network-lkg.receipt.json"
```

Expected after process restart with the DB still paused: store-aware readiness 503, key lookup 503 with receipt 0, network-backed LKG traffic 200 with receipt 1, objective readback source `lkg` and store_reachable false. This is a policy-specific degraded-mode contract, not a statement that all requests fail closed. Cached key decisions before restart can differ from cold unknown evaluation; do not classify cached success as an unauthenticated bypass.

Unpause the store even if a preceding check fails. Wait for readiness **and** store APIs before new writes, verify a new objective, then remove only the recovery binding/objective. The product startup readiness limitation remains open; this workaround does not fix the chart or product.

**Step 1 — Restore the policy store and inspect recovery**

Unpause `share-pg`, then poll `/status/ready`, `/config/ai/apikey` and `/config/ai/objective` once per second for up to 90 seconds. Continue only when all three return HTTP 200; each attempt is logged to `readiness-recovery.jsonl`.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
docker unpause share-pg
probe_log="$LAB/readiness-recovery.jsonl"
ready=false
for attempt in $(seq 1 90); do
  ready=true
  for path in /status/ready /config/ai/apikey /config/ai/objective; do
    if status=$(ip netns exec share-a curl -sS --max-time 5 \
      -o "$LAB/readiness-body.json" -w '%{http_code}' "$API$path"); then
      :
    else
      status=000
    fi
    jq -nc --arg path "$path" --arg status "$status" \
      '{time:now,path:$path,http:$status}' >> "$probe_log"
    test "$status" = 200 || ready=false
  done
  test "$ready" = true && break
  sleep 1
done
test "$ready" = true
tail -n 3 "$probe_log"
```

**Step 2 — Reconcile the paused `outage-write-check` write**

Send the displayed management request to `/config/ai/objective` and retain its response. Require HTTP 200 for the saved management response before continuing.

```bash
status=$(ip netns exec share-a curl -sS --max-time 10 -X GET \
  -D "$LAB/recovery-config-12.headers" -o "$LAB/recovery-config-12.response.json" \
  -w '%{http_code}' "$API/config/ai/objective")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-12.response.json"
test "$status" = 200
# Check the result of the earlier write before any retry or new mutation.
jq -e '(.objectiveAttr | type) == "array" and .store_reachable == true' \
  "$LAB/recovery-config-12.response.json"
write_http=$(jq -er .http "$LAB/paused-write-observation.json")
write_present=$(jq -r 'any(.objectiveAttr[]; .name == "outage-write-check")' \
  "$LAB/recovery-config-12.response.json")
jq -n --arg http "$write_http" --argjson present "$write_present" \
  '{write_http:$http,row_present_after_recovery:$present}' > "$LAB/recovered-write-outcome.json"
cat "$LAB/recovered-write-outcome.json"
if test "$write_http" = 503; then
  # A not-sent answer must not leave a late row.
  test "$write_present" = false
fi
```

**Step 3 — Delete any late write and create `recovered-objective`**

If the paused `outage-write-check` write was committed late, delete only that row and require HTTP 200. Then write `recovery-config-13.request.json` with the displayed editable JSON input and create `recovered-objective` through `/config/ai/objective`.

```bash
if test "$write_present" = true; then
  # A 504 outcome may have committed; delete only this lab's diagnostic row.
  status=$(ip netns exec share-a curl -sS --max-time 10 -X DELETE \
    -o "$LAB/late-write-delete.response.json" -w '%{http_code}' "$API/config/ai/objective/outage-write-check")
  test "$status" = 200
fi
cat > "$LAB/recovery-config-13.request.json" <<'JSON'
{
  "name": "recovered-objective",
  "priority": 1
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/recovery-config-13.request.json" \
  -D "$LAB/recovery-config-13.headers" -o "$LAB/recovery-config-13.response.json" \
  -w '%{http_code}' "$API/config/ai/objective")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-13.response.json"
test "$status" = 200
```

**Step 4 — Send `store-key-recovered` and retain the response**

Write `store-key-recovered.request.json` with the displayed editable JSON input. Send `store-key-recovered` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `store-key-recovered`.

```bash
cat > "$LAB/store-key-recovered.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "store-key-recovered"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: store-key-recovered' -H 'X-Request-Id: store-key-recovered' \
  --data-binary "@$LAB/store-key-recovered.request.json" \
  -D "$LAB/store-key-recovered.headers" -o "$LAB/store-key-recovered.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/store-key-recovered.http"
if test -f "$LAB/store-key-recovered.pid"; then
  wait "$(cat "$LAB/store-key-recovered.pid")"
fi
test "$(cat "$LAB/store-key-recovered.http")" = 200
```

**Step 5 — Confirm `store-key-recovered`; delete recovery binding and objective**

Read `store-key-recovered` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `store-key-recovered`. Send the displayed management request to `/config/ai/netidentity/recovery-interface` and retain its response. Require HTTP 200 for the saved management response before continuing. Send the displayed management request to `/config/ai/objective/recovered-objective` and retain its response.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/store-key-recovered" -o "$LAB/store-key-recovered.receipt.json"
jq -e '.count == 1' "$LAB/store-key-recovered.receipt.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X DELETE \
  -D "$LAB/recovery-config-14.headers" -o "$LAB/recovery-config-14.response.json" \
  -w '%{http_code}' "$API/config/ai/netidentity/recovery-interface")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-14.response.json"
test "$status" = 200
status=$(ip netns exec share-a curl -sS --max-time 10 -X DELETE \
  -D "$LAB/recovery-config-15.headers" -o "$LAB/recovery-config-15.response.json" \
  -w '%{http_code}' "$API/config/ai/objective/recovered-objective")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-15.response.json"
test "$status" = 200
```

**Step 6 — Send `removed-recovery-binding` and retain the response**

Write `removed-recovery-binding.request.json` with the displayed editable JSON input. Send `removed-recovery-binding` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 401 for `removed-recovery-binding`. Read `removed-recovery-binding` directly from the backend receipt endpoint; this observation bypasses the Gateway.

```bash
cat > "$LAB/removed-recovery-binding.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "removed-recovery-binding"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: removed-recovery-binding' -H 'X-Request-Id: removed-recovery-binding' \
  --data-binary "@$LAB/removed-recovery-binding.request.json" \
  -D "$LAB/removed-recovery-binding.headers" -o "$LAB/removed-recovery-binding.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/removed-recovery-binding.http"
if test -f "$LAB/removed-recovery-binding.pid"; then
  wait "$(cat "$LAB/removed-recovery-binding.pid")"
fi
test "$(cat "$LAB/removed-recovery-binding.http")" = 401
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/removed-recovery-binding" -o "$LAB/removed-recovery-binding.receipt.json"
```

**Step 7 — Send `surviving-research` and retain the response**

Require backend receipt count 0 for `removed-recovery-binding`. Write `surviving-research.request.json` with the displayed editable JSON input. Send `surviving-research` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `surviving-research`.

```bash
jq -e '.count == 0' "$LAB/removed-recovery-binding.receipt.json"
cat > "$LAB/surviving-research.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "surviving-research"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-b curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: surviving-research' -H 'X-Request-Id: surviving-research' \
  --data-binary "@$LAB/surviving-research.request.json" \
  -D "$LAB/surviving-research.headers" -o "$LAB/surviving-research.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/surviving-research.http"
if test -f "$LAB/surviving-research.pid"; then
  wait "$(cat "$LAB/surviving-research.pid")"
fi
test "$(cat "$LAB/surviving-research.http")" = 200
```

**Step 8 — Confirm `surviving-research` and wait for an idle queue**

Read `surviving-research` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `surviving-research`. Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/surviving-research" -o "$LAB/surviving-research.receipt.json"
jq -e '.count == 1' "$LAB/surviving-research.receipt.json"
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/recovery-state-16.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 0 and .queued == 0' "$LAB/recovery-state-16.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/recovery-state-16.json"
```

### Observe and diagnose

Save `/config/loadbalancer/all`, `/config/ai/netidentity`, applied objective source/health and isolated metric deltas. The lab keeps request names in X-Request-Id and X-Test-Nonce for backend correlation. Read actual audit files under `/var/log/loxilb/audit/audit.jsonl` and rotated `.gz` files inside the Gateway; an empty legacy path is not evidence of missing events. Audit shipping and SIEM collectors belong in [audit operations](../../operations/audit-log.md), not in this lab. Never copy raw keys, prompts or audit dumps into a public issue.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
status=$(ip netns exec share-a curl -sS --max-time 10 -X GET \
  -D "$LAB/recovery-config-17.headers" -o "$LAB/recovery-config-17.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer/all")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-17.response.json"
test "$status" = 200
status=$(ip netns exec share-a curl -sS --max-time 10 -X GET \
  -D "$LAB/recovery-config-18.headers" -o "$LAB/recovery-config-18.response.json" \
  -w '%{http_code}' "$API/config/ai/netidentity")
printf 'HTTP %s\n' "$status"
jq . "$LAB/recovery-config-18.response.json"
test "$status" = 200
ip netns exec share-a curl -fsS http://192.0.2.254:11111/netlox/v1/metrics > "$LAB/metrics-final.txt"
docker exec share-gateway sh -c 'ls -l /var/log/loxilb/audit/'
```

For a denied request inspect its typed error, actual source, resolved key tenant, cap and grants. For an unexpected dispatch order inspect backlog and returned permits, not eventual completion order. Preserve failures before retrying. Product defects require a reproducible report and owner action, not a lab-side change to the product. Finish with [cleanup](cleanup.md).

## Check your result

Keep live/LKG policy separate from store reachability; read back an uncertain write before retrying.

Keep the configured policy, HTTP status, resolved identity, and independent backend receipt together. A rejected request must have receipt 0; a successful request must have receipt 1. A missing receipt response is a failed observation, never a zero.

## Next steps and cleanup

Continue in the documented order with the same LAB. Remove an experiment's binding or temporary rule before the next experiment; stop the shared lab only at the final cleanup chapter. Read the [lab starting point](setup.md) if required values are missing. Use [cleanup and recovery](cleanup.md) when ending the run.
