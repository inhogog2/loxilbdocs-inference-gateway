# Give departments identity and bounded priority authority

Create support and research tenants, then issue separate interactive-capable and batch-only keys for each. Keep tenant identity stable across keys and network paths.

<!-- example-status-default: illustrative-only -->

## Before you start

Complete setup and keep one root Bash session.

**Focus of this page:** Create objectives, tenant authority and separate interactive/batch keys, then one shared listener.

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

### Onboard the departments

After [setup](setup.md), create the two named objectives below, then configure each tenant and issue its keys through the REST API. Batch keys carry a sheddable cap. The high synthetic RPS limit prevents this exercise from measuring quota exhaustion instead of scheduling.

**Step 1 — Create the `interactive` objective**

Write `identity-config-1.request.json` with the displayed editable JSON input. Send the displayed management request to `/config/ai/objective` and retain its response. Require HTTP 200 for the saved management response before continuing. Write `identity-config-2.request.json` with the displayed editable JSON input.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
cat > "$LAB/identity-config-1.request.json" <<'JSON'
{
  "name": "interactive",
  "priority": 10
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/identity-config-1.request.json" \
  -D "$LAB/identity-config-1.headers" -o "$LAB/identity-config-1.response.json" \
  -w '%{http_code}' "$API/config/ai/objective")
printf 'HTTP %s\n' "$status"
jq . "$LAB/identity-config-1.response.json"
test "$status" = 200
cat > "$LAB/identity-config-2.request.json" <<'JSON'
{
  "name": "batch",
  "priority": -5
}
JSON
```

**Step 2 — Create the `batch` objective**

Send the displayed management request to `/config/ai/objective` and retain its response. Require HTTP 200 for the saved management response before continuing.

```bash
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/identity-config-2.request.json" \
  -D "$LAB/identity-config-2.headers" -o "$LAB/identity-config-2.response.json" \
  -w '%{http_code}' "$API/config/ai/objective")
printf 'HTTP %s\n' "$status"
jq . "$LAB/identity-config-2.response.json"
test "$status" = 200
```

#### Configure support authority

Set support's maximum class and the objective names it may request. A tenant POST returns 204. Change tenant_id and allowed_objectives when adding another department.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
mkdir -p "$LAB/keys"

cat > "$LAB/identity-config-3.request.json" <<'JSON'
{
  "tenant_id": "support",
  "priority_class": "critical",
  "allowed_objectives": [
    "interactive",
    "batch"
  ]
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/identity-config-3.request.json" \
  -D "$LAB/identity-config-3.headers" -o "$LAB/identity-config-3.response.json" \
  -w '%{http_code}' "$API/config/ai/tenant/ratelimit")
printf 'HTTP %s\n' "$status"
test "$status" = 204

```

#### Issue the support interactive-capable key

This key is restricted to shared-model and may use the tenant's authorized objectives. Store the one-time raw_key privately and retain key_id for deletion.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
cat > "$LAB/support.key-request.json" <<'JSON'
{
  "tenant_id": "support",
  "name": "support",
  "allowed_models": [
    "shared-model"
  ],
  "enabled": true,
  "rate_limit_rps": 10000,
  "burst_size": 10000,
  "priority_class": "critical"
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/support.key-request.json" \
  -o "$LAB/keys/support.json" -w '%{http_code}' "$API/config/ai/apikey")
test "$status" = 201
jq -er '"header = \"X-Api-Key: " + .raw_key + "\""' \
  "$LAB/keys/support.json" > "$LAB/keys/support.curl"
chmod 600 "$LAB/keys/support.json" "$LAB/keys/support.curl"
jq '{key_id,tenant_id,allowed_models,priority_class}' "$LAB/keys/support.json"

```

#### Issue a narrower support batch key

The sheddable key cap narrows support's critical tenant cap. Change priority_class here to restrict this workload without changing every support request.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
cat > "$LAB/support-batch.key-request.json" <<'JSON'
{
  "tenant_id": "support",
  "name": "support-batch",
  "allowed_models": [
    "shared-model"
  ],
  "enabled": true,
  "rate_limit_rps": 10000,
  "burst_size": 10000,
  "priority_class": "sheddable"
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/support-batch.key-request.json" \
  -o "$LAB/keys/support-batch.json" -w '%{http_code}' "$API/config/ai/apikey")
test "$status" = 201
jq -er '"header = \"X-Api-Key: " + .raw_key + "\""' \
  "$LAB/keys/support-batch.json" > "$LAB/keys/support-batch.curl"
chmod 600 "$LAB/keys/support-batch.json" "$LAB/keys/support-batch.curl"
jq '{key_id,tenant_id,allowed_models,priority_class}' "$LAB/keys/support-batch.json"

```

#### Configure research authority

Grant the same objective names to research while keeping its tenant identity separate.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
cat > "$LAB/identity-config-4.request.json" <<'JSON'
{
  "tenant_id": "research",
  "priority_class": "critical",
  "allowed_objectives": [
    "interactive",
    "batch"
  ]
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/identity-config-4.request.json" \
  -D "$LAB/identity-config-4.headers" -o "$LAB/identity-config-4.response.json" \
  -w '%{http_code}' "$API/config/ai/tenant/ratelimit")
printf 'HTTP %s\n' "$status"
test "$status" = 204

```

#### Issue the research interactive-capable key

Research uses its own tenant for fairness and accounting even though the model and listener are shared.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
cat > "$LAB/research.key-request.json" <<'JSON'
{
  "tenant_id": "research",
  "name": "research",
  "allowed_models": [
    "shared-model"
  ],
  "enabled": true,
  "rate_limit_rps": 10000,
  "burst_size": 10000,
  "priority_class": "critical"
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/research.key-request.json" \
  -o "$LAB/keys/research.json" -w '%{http_code}' "$API/config/ai/apikey")
test "$status" = 201
jq -er '"header = \"X-Api-Key: " + .raw_key + "\""' \
  "$LAB/keys/research.json" > "$LAB/keys/research.curl"
chmod 600 "$LAB/keys/research.json" "$LAB/keys/research.curl"
jq '{key_id,tenant_id,allowed_models,priority_class}' "$LAB/keys/research.json"

```

#### Issue a narrower research batch key

This separate key remains the same research tenant. It does not create another tenant share.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
cat > "$LAB/research-batch.key-request.json" <<'JSON'
{
  "tenant_id": "research",
  "name": "research-batch",
  "allowed_models": [
    "shared-model"
  ],
  "enabled": true,
  "rate_limit_rps": 10000,
  "burst_size": 10000,
  "priority_class": "sheddable"
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/research-batch.key-request.json" \
  -o "$LAB/keys/research-batch.json" -w '%{http_code}' "$API/config/ai/apikey")
test "$status" = 201
jq -er '"header = \"X-Api-Key: " + .raw_key + "\""' \
  "$LAB/keys/research-batch.json" > "$LAB/keys/research-batch.curl"
chmod 600 "$LAB/keys/research-batch.json" "$LAB/keys/research-batch.curl"
jq '{key_id,tenant_id,allowed_models,priority_class}' "$LAB/keys/research-batch.json"

```

#### Create the shared model service

The complete configuration below is the baseline for later edits. Change externalIP/host/port and endpointIP/targetPort together with setup routes and client URLs. model_name must match the request model and each key's allowed_models. Capacity is one executing request, 32 waiting requests and a 30000 ms window to make dispatch order visible. sse_mode enables the AI Gateway request path; it does not make the fixture a real streaming engine.

**Step 1 — Load the lab values**

Keep the same private LAB and shell for this chapter. These assignments choose paths and identities; they do not establish store readiness or traffic success.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
```

**Step 2 — Prepare `base-rule.json`**

Write `base-rule.json` with the displayed editable JSON input.

```bash
cat > "$LAB/base-rule.json" <<'JSON'
{
  "serviceArguments": {
    "externalIP": "192.0.2.254",
    "port": 8080,
    "protocol": "tcp",
    "sel": 0,
    "mode": 4,
    "host": "192.0.2.254",
    "path_prefix": "/",
    "path_match_mode": "prefix",
    "model_name": "shared-model",
    "sse_mode": true,
    "api_key_auth": "required",
    "inactiveTimeOut": 60,
    "fc_mode": "enforce",
    "fc_max_outstanding": 1,
    "fc_max_queue_depth": 32,
    "fc_max_queue_wait_ms": 30000,
    "fc_expose_headers": "on",
    "fc_wake_policy": "strict",
    "fc_band_weights": "0:0:0",
    "fc_band_min_share_pct": "0:0:0",
    "fc_critical_reserve_pct": 0,
    "fc_band_wait_ms": "0:0:0",
    "fc_band_queue_pct": "0:0:0",
    "fc_shed_queue": "on",
    "fc_tenant_wake": "fifo",
    "fc_tenant_max_share_pct": 100,
    "fc_llmd_headers": "on",
    "ai_objective_strict": true
  },
  "endpoints": [
    {
      "endpointIP": "203.0.113.1",
      "targetPort": 8080,
      "weight": 1
    }
  ]
}
JSON
```

**Step 3 — Apply `base-rule.json` and list all service rules**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 200 for the saved management response before continuing. Send the displayed management request to `/config/loadbalancer/all` and retain its response.

```bash
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/base-rule.json" \
  -D "$LAB/identity-config-5.headers" -o "$LAB/identity-config-5.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/identity-config-5.response.json"
test "$status" = 200
status=$(ip netns exec share-a curl -sS --max-time 10 -X GET \
  -D "$LAB/identity-config-6.headers" -o "$LAB/identity-config-6.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer/all")
printf 'HTTP %s\n' "$status"
jq . "$LAB/identity-config-6.response.json"
test "$status" = 200
```

**Step 4 — Send `support-baseline` and retain the response**

Write `support-baseline.request.json` with the displayed editable JSON input. Send `support-baseline` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `support-baseline`.

```bash
cat > "$LAB/support-baseline.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "support-baseline"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: support-baseline' -H 'X-Request-Id: support-baseline' \
  --data-binary "@$LAB/support-baseline.request.json" \
  -D "$LAB/support-baseline.headers" -o "$LAB/support-baseline.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/support-baseline.http"
if test -f "$LAB/support-baseline.pid"; then
  wait "$(cat "$LAB/support-baseline.pid")"
fi
test "$(cat "$LAB/support-baseline.http")" = 200
```

**Step 5 — Send `research-baseline` and retain the response**

Read `support-baseline` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `support-baseline`. Write `research-baseline.request.json` with the displayed editable JSON input. Send `research-baseline` through the Gateway from the namespace shown below; retain its HTTP status and response separately.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/support-baseline" -o "$LAB/support-baseline.receipt.json"
jq -e '.count == 1' "$LAB/support-baseline.receipt.json"
jq -e '(((.["headers"]["x-llm-d-inference-fairness-id"] == "support")) and ((.["headers"]["x-llm-d-inference-objective"] == "standard")))' "$LAB/support-baseline.receipt.json"
cat > "$LAB/research-baseline.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "research-baseline"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-b curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: research-baseline' -H 'X-Request-Id: research-baseline' \
  --data-binary "@$LAB/research-baseline.request.json" \
  -D "$LAB/research-baseline.headers" -o "$LAB/research-baseline.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/research-baseline.http"
```

**Step 6 — Confirm `research-baseline` reached the backend**

Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `research-baseline`. Read `research-baseline` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `research-baseline`. Write `support-interactive.request.json` with the displayed editable JSON input.

```bash
if test -f "$LAB/research-baseline.pid"; then
  wait "$(cat "$LAB/research-baseline.pid")"
fi
test "$(cat "$LAB/research-baseline.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/research-baseline" -o "$LAB/research-baseline.receipt.json"
jq -e '.count == 1' "$LAB/research-baseline.receipt.json"
cat > "$LAB/support-interactive.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "support-interactive"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 7 — Send `support-interactive` and retain the response**

Send `support-interactive` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `support-interactive`. Read `support-interactive` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `support-interactive`.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: support-interactive' -H 'X-Request-Id: support-interactive' \
  -H x-llm-d-inference-objective:interactive \
  --data-binary "@$LAB/support-interactive.request.json" \
  -D "$LAB/support-interactive.headers" -o "$LAB/support-interactive.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/support-interactive.http"
if test -f "$LAB/support-interactive.pid"; then
  wait "$(cat "$LAB/support-interactive.pid")"
fi
test "$(cat "$LAB/support-interactive.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/support-interactive" -o "$LAB/support-interactive.receipt.json"
jq -e '.count == 1' "$LAB/support-interactive.receipt.json"
jq -e '((.["headers"]["x-llm-d-inference-objective"] == "critical"))' "$LAB/support-interactive.receipt.json"
```

**Step 8 — Send `support-batch` and retain the response**

Write `support-batch.request.json` with the displayed editable JSON input. Send `support-batch` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `support-batch`.

```bash
cat > "$LAB/support-batch.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "support-batch"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support-batch.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: support-batch' -H 'X-Request-Id: support-batch' \
  --data-binary "@$LAB/support-batch.request.json" \
  -D "$LAB/support-batch.headers" -o "$LAB/support-batch.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/support-batch.http"
if test -f "$LAB/support-batch.pid"; then
  wait "$(cat "$LAB/support-batch.pid")"
fi
test "$(cat "$LAB/support-batch.http")" = 200
```

**Step 9 — Confirm `support-batch` arrived as sheddable**

Read `support-batch` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `support-batch`.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/support-batch" -o "$LAB/support-batch.receipt.json"
jq -e '.count == 1' "$LAB/support-batch.receipt.json"
jq -e '((.["headers"]["x-llm-d-inference-objective"] == "sheddable"))' "$LAB/support-batch.receipt.json"
```

The no-hint interactive-capable key stays standard: a cap grants a ceiling, not a default urgency. A narrower key/profile/network-binding cap can lower the result. This is why tenant and band cannot be used interchangeably.

Change allowed_models on the key request to grant a different model; keep the service model_name and request model consistent. A key's priority_class narrows its tenant cap; allowed_objectives authorizes raises, while default_objective chooses no-hint behavior. The API returns the raw key only on creation, so keep the private JSON and curl header file before proceeding.

### Deny forged authority and invalid input

A missing key and a presented invalid key are both denied; the latter must never gain a network fallback. An unknown objective under strict policy is 403, with no backend delivery. Requesting another model is also forbidden.

**Step 1 — Send `missing-key` and retain the response**

Write `missing-key.request.json` with the displayed editable JSON input. Send `missing-key` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
cat > "$LAB/missing-key.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "missing-key"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: missing-key' -H 'X-Request-Id: missing-key' \
  --data-binary "@$LAB/missing-key.request.json" \
  -D "$LAB/missing-key.headers" -o "$LAB/missing-key.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/missing-key.http"
if test -f "$LAB/missing-key.pid"; then
  wait "$(cat "$LAB/missing-key.pid")"
fi
```

**Step 2 — Send `bad-key` and retain the response**

Require saved HTTP 401 for `missing-key`. Read `missing-key` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `missing-key`. Write `bad-key.request.json` with the displayed editable JSON input. Send `bad-key` through the Gateway from the namespace shown below; retain its HTTP status and response separately.

```bash
test "$(cat "$LAB/missing-key.http")" = 401
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/missing-key" -o "$LAB/missing-key.receipt.json"
jq -e '.count == 0' "$LAB/missing-key.receipt.json"
cat > "$LAB/bad-key.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "bad-key"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: bad-key' -H 'X-Request-Id: bad-key' \
  -H "@$LAB/invalid-key.headers" \
  --data-binary "@$LAB/bad-key.request.json" \
  -D "$LAB/bad-key.headers" -o "$LAB/bad-key.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/bad-key.http"
```

**Step 3 — Confirm `bad-key` got 401 with no receipt**

Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 401 for `bad-key`. Read `bad-key` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `bad-key`. Write `unknown-objective.request.json` with the displayed editable JSON input.

```bash
if test -f "$LAB/bad-key.pid"; then
  wait "$(cat "$LAB/bad-key.pid")"
fi
test "$(cat "$LAB/bad-key.http")" = 401
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/bad-key" -o "$LAB/bad-key.receipt.json"
jq -e '.count == 0' "$LAB/bad-key.receipt.json"
cat > "$LAB/unknown-objective.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "unknown-objective"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 4 — Send `unknown-objective` and retain the response**

Send `unknown-objective` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 403 for `unknown-objective`. Read `unknown-objective` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `unknown-objective`. Write `wrong-model.request.json` with the displayed editable JSON input.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: unknown-objective' -H 'X-Request-Id: unknown-objective' \
  -H x-llm-d-inference-objective:unknown \
  --data-binary "@$LAB/unknown-objective.request.json" \
  -D "$LAB/unknown-objective.headers" -o "$LAB/unknown-objective.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/unknown-objective.http"
if test -f "$LAB/unknown-objective.pid"; then
  wait "$(cat "$LAB/unknown-objective.pid")"
fi
test "$(cat "$LAB/unknown-objective.http")" = 403
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/unknown-objective" -o "$LAB/unknown-objective.receipt.json"
jq -e '.count == 0' "$LAB/unknown-objective.receipt.json"
cat > "$LAB/wrong-model.request.json" <<'JSON'
{"model":"other-model","messages":[{"role":"user","content":"hello"}],"max_tokens":4}
JSON
```

**Step 5 — Send `wrong-model` and retain the response**

Send `wrong-model` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 403 for `wrong-model`. Read `wrong-model` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `wrong-model`.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: wrong-model' -H 'X-Request-Id: wrong-model' \
  --data-binary "@$LAB/wrong-model.request.json" \
  -D "$LAB/wrong-model.headers" -o "$LAB/wrong-model.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/wrong-model.http"
if test -f "$LAB/wrong-model.pid"; then
  wait "$(cat "$LAB/wrong-model.pid")"
fi
test "$(cat "$LAB/wrong-model.http")" = 403
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/wrong-model" -o "$LAB/wrong-model.receipt.json"
jq -e '.count == 0' "$LAB/wrong-model.receipt.json"
```

**Step 6 — Send `forged-fairness` and retain the response**

Write `forged-fairness.request.json` with the displayed editable JSON input. Send `forged-fairness` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response.

```bash
cat > "$LAB/forged-fairness.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "forged-fairness"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: forged-fairness' -H 'X-Request-Id: forged-fairness' \
  -H x-llm-d-inference-fairness-id:research \
  -H X-Auth-Tenant:research \
  --data-binary "@$LAB/forged-fairness.request.json" \
  -D "$LAB/forged-fairness.headers" -o "$LAB/forged-fairness.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/forged-fairness.http"
if test -f "$LAB/forged-fairness.pid"; then
  wait "$(cat "$LAB/forged-fairness.pid")"
fi
```

**Step 7 — Confirm `forged-fairness` stayed attributed to support**

Require saved HTTP 200 for `forged-fairness`. Read `forged-fairness` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `forged-fairness`.

```bash
test "$(cat "$LAB/forged-fairness.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/forged-fairness" -o "$LAB/forged-fairness.receipt.json"
jq -e '.count == 1' "$LAB/forged-fairness.receipt.json"
jq -e '((.["headers"]["x-llm-d-inference-fairness-id"] == "support"))' "$LAB/forged-fairness.receipt.json"
```

Change only the hint-enforcement mode. In non-strict mode an unknown hint falls back to the authorized default; it does not acquire critical authority. This switch is distinct from a network binding's strict/advisory tenant-mismatch policy.

**Step 1 — Turn off strict objective-hint enforcement**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 200 for the saved management response before continuing.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
jq '.serviceArguments += {
  "ai_objective_strict": false
}' \
  "$LAB/base-rule.json" > "$LAB/identity-rule-7.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/identity-rule-7.request.json" \
  -D "$LAB/identity-rule-7.headers" -o "$LAB/identity-rule-7.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/identity-rule-7.response.json"
test "$status" = 200
```

**Step 2 — Send `fallback-hint` and retain the response**

Write `fallback-hint.request.json` with the displayed editable JSON input. Send `fallback-hint` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `fallback-hint`.

```bash
cat > "$LAB/fallback-hint.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "fallback-hint"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: fallback-hint' -H 'X-Request-Id: fallback-hint' \
  -H x-llm-d-inference-objective:unknown \
  --data-binary "@$LAB/fallback-hint.request.json" \
  -D "$LAB/fallback-hint.headers" -o "$LAB/fallback-hint.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/fallback-hint.http"
if test -f "$LAB/fallback-hint.pid"; then
  wait "$(cat "$LAB/fallback-hint.pid")"
fi
test "$(cat "$LAB/fallback-hint.http")" = 200
```

**Step 3 — Confirm `fallback-hint` arrived as standard; restore strict mode**

Read `fallback-hint` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 and the `standard` objective header. Then restore strict objective enforcement (`ai_objective_strict: true`, `fc_max_queue_depth: 31`) through `/config/loadbalancer` and require HTTP 200.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/fallback-hint" -o "$LAB/fallback-hint.receipt.json"
jq -e '.count == 1' "$LAB/fallback-hint.receipt.json"
jq -e '((.["headers"]["x-llm-d-inference-objective"] == "standard"))' "$LAB/fallback-hint.receipt.json"
jq '.serviceArguments += {
  "ai_objective_strict": true,
  "fc_max_queue_depth": 31
}' \
  "$LAB/base-rule.json" > "$LAB/identity-rule-9.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/identity-rule-9.request.json" \
  -D "$LAB/identity-rule-9.headers" -o "$LAB/identity-rule-9.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/identity-rule-9.response.json"
test "$status" = 200
```

### Lowering versus raising within one band

Lowering from standard to flex (priority -1) needs no raise grant. But from a default priority -5 to flex -1 is a raise even though both requests remain sheddable. Set a default, remove grants, observe refusal, then grant `tier:flex` explicitly and recover. When class policy is active, the Gateway consumes the top-level body `service_tier` hint and forwards it as JSON null; the backend must not reinterpret it as engine priority. The receipt checks below require the field to remain present with a null value. The objective header takes precedence over a body `service_tier` hint; test that independently of native engine `priority` in [recovery](recovery.md).

**Step 1 — Send `lower-to-flex` and retain the response**

Write `lower-to-flex.request.json` with the displayed editable JSON input. Send `lower-to-flex` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `lower-to-flex`. Read `lower-to-flex` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `lower-to-flex`.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
cat > "$LAB/lower-to-flex.request.json" <<'JSON'
{"model":"shared-model","messages":[{"role":"user","content":"low urgency"}],"max_tokens":4,"service_tier":"flex"}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: lower-to-flex' -H 'X-Request-Id: lower-to-flex' \
  --data-binary "@$LAB/lower-to-flex.request.json" \
  -D "$LAB/lower-to-flex.headers" -o "$LAB/lower-to-flex.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/lower-to-flex.http"
if test -f "$LAB/lower-to-flex.pid"; then
  wait "$(cat "$LAB/lower-to-flex.pid")"
fi
test "$(cat "$LAB/lower-to-flex.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/lower-to-flex" -o "$LAB/lower-to-flex.receipt.json"
jq -e '.count == 1' "$LAB/lower-to-flex.receipt.json"
jq -e '(.body | has("service_tier")) and .body.service_tier == null' "$LAB/lower-to-flex.receipt.json"
jq -e '((.["headers"]["x-llm-d-inference-objective"] == "sheddable"))' "$LAB/lower-to-flex.receipt.json"
```

**Step 2 — Remove research raise grants and send `same-band-raise`**

Write `identity-config-11.request.json` with the displayed editable JSON input. Send the displayed management request to `/config/ai/tenant/ratelimit` and retain its response. Require HTTP 204 for the saved management response before continuing. Write `same-band-raise.request.json` with the displayed editable JSON input. Send `same-band-raise` through the Gateway from the namespace shown below; retain its HTTP status and response separately.

```bash
cat > "$LAB/identity-config-11.request.json" <<'JSON'
{
  "tenant_id": "research",
  "priority_class": "critical",
  "default_objective": "batch",
  "allowed_objectives": []
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/identity-config-11.request.json" \
  -D "$LAB/identity-config-11.headers" -o "$LAB/identity-config-11.response.json" \
  -w '%{http_code}' "$API/config/ai/tenant/ratelimit")
printf 'HTTP %s\n' "$status"
test "$status" = 204
cat > "$LAB/same-band-raise.request.json" <<'JSON'
{"model":"shared-model","messages":[{"role":"user","content":"raise"}],"max_tokens":4,"service_tier":"flex"}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: same-band-raise' -H 'X-Request-Id: same-band-raise' \
  --data-binary "@$LAB/same-band-raise.request.json" \
  -D "$LAB/same-band-raise.headers" -o "$LAB/same-band-raise.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/same-band-raise.http"
```

**Step 3 — Confirm `same-band-raise` is denied; grant `tier:flex`**

Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 403 for `same-band-raise`. Read `same-band-raise` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `same-band-raise`. Write `identity-config-12.request.json` with the displayed editable JSON input. Send the displayed management request to `/config/ai/tenant/ratelimit` and retain its response. Require HTTP 204 for the saved management response before continuing.

```bash
if test -f "$LAB/same-band-raise.pid"; then
  wait "$(cat "$LAB/same-band-raise.pid")"
fi
test "$(cat "$LAB/same-band-raise.http")" = 403
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/same-band-raise" -o "$LAB/same-band-raise.receipt.json"
jq -e '.count == 0' "$LAB/same-band-raise.receipt.json"
cat > "$LAB/identity-config-12.request.json" <<'JSON'
{
  "tenant_id": "research",
  "priority_class": "critical",
  "default_objective": "batch",
  "allowed_objectives": [
    "tier:flex"
  ]
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/identity-config-12.request.json" \
  -D "$LAB/identity-config-12.headers" -o "$LAB/identity-config-12.response.json" \
  -w '%{http_code}' "$API/config/ai/tenant/ratelimit")
printf 'HTTP %s\n' "$status"
test "$status" = 204
```

**Step 4 — Send `granted-flex` and retain the response**

Write `granted-flex.request.json` with the displayed editable JSON input. Send `granted-flex` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `granted-flex`. Read `granted-flex` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `granted-flex`.

```bash
cat > "$LAB/granted-flex.request.json" <<'JSON'
{"model":"shared-model","messages":[{"role":"user","content":"granted"}],"max_tokens":4,"service_tier":"flex"}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: granted-flex' -H 'X-Request-Id: granted-flex' \
  --data-binary "@$LAB/granted-flex.request.json" \
  -D "$LAB/granted-flex.headers" -o "$LAB/granted-flex.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/granted-flex.http"
if test -f "$LAB/granted-flex.pid"; then
  wait "$(cat "$LAB/granted-flex.pid")"
fi
test "$(cat "$LAB/granted-flex.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/granted-flex" -o "$LAB/granted-flex.receipt.json"
jq -e '.count == 1' "$LAB/granted-flex.receipt.json"
jq -e '(.body | has("service_tier")) and .body.service_tier == null' "$LAB/granted-flex.receipt.json"
```

**Step 5 — Allow research to request `interactive` and `batch`**

Write `identity-config-13.request.json` with the displayed editable JSON input. Send the displayed management request to `/config/ai/tenant/ratelimit` and retain its response. Require HTTP 204 for the saved management response before continuing. Write `header-precedence.request.json` with the displayed editable JSON input.

```bash
cat > "$LAB/identity-config-13.request.json" <<'JSON'
{
  "tenant_id": "research",
  "priority_class": "critical",
  "default_objective": "",
  "allowed_objectives": [
    "interactive",
    "batch"
  ]
}
JSON
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/identity-config-13.request.json" \
  -D "$LAB/identity-config-13.headers" -o "$LAB/identity-config-13.response.json" \
  -w '%{http_code}' "$API/config/ai/tenant/ratelimit")
printf 'HTTP %s\n' "$status"
test "$status" = 204
cat > "$LAB/header-precedence.request.json" <<'JSON'
{"model":"shared-model","messages":[{"role":"user","content":"urgent"}],"max_tokens":4,"service_tier":"flex"}
JSON
```

**Step 6 — Send `header-precedence` and retain the response**

Send `header-precedence` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `header-precedence`. Read `header-precedence` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `header-precedence`.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: header-precedence' -H 'X-Request-Id: header-precedence' \
  -H x-llm-d-inference-objective:interactive \
  --data-binary "@$LAB/header-precedence.request.json" \
  -D "$LAB/header-precedence.headers" -o "$LAB/header-precedence.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/header-precedence.http"
if test -f "$LAB/header-precedence.pid"; then
  wait "$(cat "$LAB/header-precedence.pid")"
fi
test "$(cat "$LAB/header-precedence.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/header-precedence" -o "$LAB/header-precedence.receipt.json"
jq -e '.count == 1' "$LAB/header-precedence.receipt.json"
jq -e '(.body | has("service_tier")) and .body.service_tier == null' "$LAB/header-precedence.receipt.json"
jq -e '((.["headers"]["x-llm-d-inference-objective"] == "critical"))' "$LAB/header-precedence.receipt.json"
```

Continue with [network attribution](networks.md). For JWT profile caps and issuance, use [UC-1 identity](../admission-flow-control/identity.md); API-key authority here does not establish a complete JWT deployment.

## Check your result

Check default standard class, denied raises, narrowed key caps and tenant identity at the backend.

Keep the configured policy, HTTP status, resolved identity, and independent backend receipt together. A rejected request must have receipt 0; a successful request must have receipt 1. A missing receipt response is a failed observation, never a zero.

## Next steps and cleanup

Continue in the documented order with the same LAB. Remove an experiment's binding or temporary rule before the next experiment; stop the shared lab only at the final cleanup chapter. Read the [lab starting point](setup.md) if required values are missing. Use [cleanup and recovery](cleanup.md) when ending the run.
