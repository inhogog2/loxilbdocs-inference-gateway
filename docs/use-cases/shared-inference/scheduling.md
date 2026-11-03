# Schedule urgent and batch requests on one service

Observe actual backend admission order while one existing request occupies capacity. This isolates the Gateway queue from engine scheduling and client completion timing.

<!-- example-status-default: illustrative-only -->

Each rule update below merges the displayed values into the full baseline JSON from onboarding, then POSTs the complete service. Change fc_wake_policy to choose band dispatch, fc_tenant_wake for tenant turns inside a band, and fc_tenant_max_share_pct for the per-tenant inflight ceiling. The following requests show the actual key, objective header, JSON body and background PID.

## Before you start

Finish the network exercises and remove their temporary bindings. Read each contention experiment before starting its held requests.

**Focus of this page:** Change the Gateway queue selection and tenant share, leaving the synthetic backend unchanged.

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

### Strict bands: urgency before waiting batch

Complete [network exercises](networks.md) and confirm no bindings remain. This experiment leaves one running request untouched, queues batch first, then critical. Strict chooses the critical waiter when a permit returns. It can starve batch under sustained critical demand.

**Step 1 — Raise the queue depth to 32**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 200 for the saved management response before continuing.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
jq '.serviceArguments += {
  "fc_max_queue_depth": 32
}' \
  "$LAB/base-rule.json" > "$LAB/scheduling-rule-1.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/scheduling-rule-1.request.json" \
  -D "$LAB/scheduling-rule-1.headers" -o "$LAB/scheduling-rule-1.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/scheduling-rule-1.response.json"
test "$status" = 200
```

**Step 2 — Start the held `strict-holder` request**

Write `strict-holder.request.json` with the displayed editable JSON input. Send `strict-holder` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/strict-holder.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "strict-holder"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: strict-holder' -H 'X-Request-Id: strict-holder' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/strict-holder.request.json" \
  -D "$LAB/strict-holder.headers" -o "$LAB/strict-holder.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/strict-holder.http" &
printf '%s\n' "$!" > "$LAB/strict-holder.pid"
arrived=false
```

**Step 3 — Confirm the backend received `strict-holder`**

Read `strict-holder` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `strict-holder`. Write `strict-batch.request.json` with the displayed editable JSON input.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/strict-holder" -o "$LAB/strict-holder.receipt.json"
  if jq -e '.count == 1' "$LAB/strict-holder.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
cat > "$LAB/strict-batch.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "strict-batch"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 4 — Queue `strict-batch` behind the holder**

Send `strict-batch` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps. Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research-batch.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: strict-batch' -H 'X-Request-Id: strict-batch' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/strict-batch.request.json" \
  -D "$LAB/strict-batch.headers" -o "$LAB/strict-batch.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/strict-batch.http" &
printf '%s\n' "$!" > "$LAB/strict-batch.pid"
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/scheduling-state-3.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 1 and .queued == 1' "$LAB/scheduling-state-3.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
```

**Step 5 — Queue `strict-urgent` as an interactive request**

Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Write `strict-urgent.request.json` with the displayed editable JSON input. Send `strict-urgent` through the Gateway from the namespace shown below; retain its HTTP status and response separately.

```bash
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/scheduling-state-3.json"
cat > "$LAB/strict-urgent.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "strict-urgent"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: strict-urgent' -H 'X-Request-Id: strict-urgent' \
  -H 'X-Test-Hold: 1' \
  -H x-llm-d-inference-objective:interactive \
  --data-binary "@$LAB/strict-urgent.request.json" \
  -D "$LAB/strict-urgent.headers" -o "$LAB/strict-urgent.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/strict-urgent.http" &
```

**Step 6 — Wait for two waiters, then release `strict-holder`**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Read `strict-batch` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `strict-batch`. Release the held backend request `strict-holder` so its capacity can return to the Gateway.

```bash
printf '%s\n' "$!" > "$LAB/strict-urgent.pid"
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/scheduling-state-4.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 1 and .queued == 2' "$LAB/scheduling-state-4.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/scheduling-state-4.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/strict-batch" -o "$LAB/strict-batch.receipt.json"
jq -e '.count == 0' "$LAB/strict-batch.receipt.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/strict-holder" | jq .
arrived=false
```

**Step 7 — Confirm `strict-urgent` dispatches before `strict-batch`**

Read `strict-urgent` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `strict-urgent`. Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/strict-urgent" -o "$LAB/strict-urgent.receipt.json"
  if jq -e '.count == 1' "$LAB/strict-urgent.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/scheduling-state-5.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 1 and .queued == 1' "$LAB/scheduling-state-5.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
```

**Step 8 — Release `strict-urgent` and confirm `strict-batch` dispatch**

Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Read `strict-batch` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `strict-batch`. Release the held backend request `strict-urgent` so its capacity can return to the Gateway. Require backend receipt count 1 for `strict-batch`. Release the held backend request `strict-batch` so its capacity can return to the Gateway. Wait for the saved client PID in this same parent Bash before checking its final response.

```bash
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/scheduling-state-5.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/strict-batch" -o "$LAB/strict-batch.receipt.json"
jq -e '.count == 0' "$LAB/strict-batch.receipt.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/strict-urgent" | jq .
arrived=false
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/strict-batch" -o "$LAB/strict-batch.receipt.json"
  if jq -e '.count == 1' "$LAB/strict-batch.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/strict-batch" | jq .
if test -f "$LAB/strict-holder.pid"; then
  wait "$(cat "$LAB/strict-holder.pid")"
fi
```

**Step 9 — Verify HTTP 200 and one receipt for each strict request**

Require saved HTTP 200 for `strict-holder`. Read `strict-holder` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `strict-holder`. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `strict-urgent`. Read `strict-urgent` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `strict-urgent`. Require saved HTTP 200 for `strict-batch`. Read `strict-batch` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `strict-batch`.

```bash
test "$(cat "$LAB/strict-holder.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/strict-holder" -o "$LAB/strict-holder.receipt.json"
jq -e '.count == 1' "$LAB/strict-holder.receipt.json"
if test -f "$LAB/strict-urgent.pid"; then
  wait "$(cat "$LAB/strict-urgent.pid")"
fi
test "$(cat "$LAB/strict-urgent.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/strict-urgent" -o "$LAB/strict-urgent.receipt.json"
jq -e '.count == 1' "$LAB/strict-urgent.receipt.json"
if test -f "$LAB/strict-batch.pid"; then
  wait "$(cat "$LAB/strict-batch.pid")"
fi
test "$(cat "$LAB/strict-batch.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/strict-batch" -o "$LAB/strict-batch.receipt.json"
jq -e '.count == 1' "$LAB/strict-batch.receipt.json"
jq -e '((.["arrival"] > 0))' "$LAB/strict-batch.receipt.json"
reached=false
```

**Step 10 — Wait for the queue to drain to zero**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/scheduling-state-6.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 0 and .queued == 0' "$LAB/scheduling-state-6.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/scheduling-state-6.json"
```

Both reads of strict-batch before urgent release must show count 0. `fc_effective` must reach inflight 1/queued 2 before release; otherwise you have not tested contention. Running work is never preempted.

### Tenant RR within the standard band

FIFO preserves global arrival order. Change to RR to give research a turn despite support's earlier burst; support's own pending work retains FIFO order. RR counts resolved tenant identities, not keys, connections, prompt tokens or GPU milliseconds. It rotates tenant slots from the current cursor. The first turn below relies on this fresh lab's slot-allocation history (support in slot 0) and cursor reset; an existing pool can start with another tenant. Preserve per-tenant FIFO and rotation when adapting the check, rather than assuming support always starts.

**Step 1 — Switch tenant wake to round robin**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 200 for the saved management response before continuing.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
jq '.serviceArguments += {
  "fc_tenant_wake": "rr"
}' \
  "$LAB/base-rule.json" > "$LAB/scheduling-rule-7.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/scheduling-rule-7.request.json" \
  -D "$LAB/scheduling-rule-7.headers" -o "$LAB/scheduling-rule-7.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/scheduling-rule-7.response.json"
test "$status" = 200
```

**Step 2 — Start the held `rr-holder` request**

Write `rr-holder.request.json` with the displayed editable JSON input. Send `rr-holder` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/rr-holder.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "rr-holder"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: rr-holder' -H 'X-Request-Id: rr-holder' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/rr-holder.request.json" \
  -D "$LAB/rr-holder.headers" -o "$LAB/rr-holder.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/rr-holder.http" &
printf '%s\n' "$!" > "$LAB/rr-holder.pid"
arrived=false
```

**Step 3 — Confirm the backend received `rr-holder`**

Read `rr-holder` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `rr-holder`. Write `rr-support-1.request.json` with the displayed editable JSON input.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/rr-holder" -o "$LAB/rr-holder.receipt.json"
  if jq -e '.count == 1' "$LAB/rr-holder.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
cat > "$LAB/rr-support-1.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "rr-support-1"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 4 — Queue `rr-support-1` behind the holder**

Send `rr-support-1` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps. Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: rr-support-1' -H 'X-Request-Id: rr-support-1' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/rr-support-1.request.json" \
  -D "$LAB/rr-support-1.headers" -o "$LAB/rr-support-1.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/rr-support-1.http" &
printf '%s\n' "$!" > "$LAB/rr-support-1.pid"
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/scheduling-state-9.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 1 and .queued == 1' "$LAB/scheduling-state-9.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
```

**Step 5 — Queue `rr-support-2` from the same tenant**

Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Write `rr-support-2.request.json` with the displayed editable JSON input. Send `rr-support-2` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/scheduling-state-9.json"
cat > "$LAB/rr-support-2.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "rr-support-2"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: rr-support-2' -H 'X-Request-Id: rr-support-2' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/rr-support-2.request.json" \
  -D "$LAB/rr-support-2.headers" -o "$LAB/rr-support-2.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/rr-support-2.http" &
printf '%s\n' "$!" > "$LAB/rr-support-2.pid"
```

**Step 6 — Wait for two queued support requests**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/scheduling-state-10.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 1 and .queued == 2' "$LAB/scheduling-state-10.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/scheduling-state-10.json"
```

**Step 7 — Queue `rr-research` from the research tenant**

Write `rr-research.request.json` with the displayed editable JSON input. Send `rr-research` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/rr-research.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "rr-research"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: rr-research' -H 'X-Request-Id: rr-research' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/rr-research.request.json" \
  -D "$LAB/rr-research.headers" -o "$LAB/rr-research.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/rr-research.http" &
printf '%s\n' "$!" > "$LAB/rr-research.pid"
reached=false
```

**Step 8 — Wait for three waiters, then release `rr-holder`**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Release the held backend request `rr-holder` so its capacity can return to the Gateway.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/scheduling-state-11.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 1 and .queued == 3' "$LAB/scheduling-state-11.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/scheduling-state-11.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/rr-holder" | jq .
arrived=false
```

**Step 9 — Release `rr-support-1` and confirm `rr-research` dispatches next**

Read `rr-support-1` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `rr-support-1`. Release the held backend request `rr-support-1` so its capacity can return to the Gateway. Read `rr-research` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `rr-research`.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/rr-support-1" -o "$LAB/rr-support-1.receipt.json"
  if jq -e '.count == 1' "$LAB/rr-support-1.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/rr-support-1" | jq .
arrived=false
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/rr-research" -o "$LAB/rr-research.receipt.json"
  if jq -e '.count == 1' "$LAB/rr-research.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
```

**Step 10 — Release `rr-research` and confirm `rr-support-2` dispatches last**

Read `rr-support-2` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `rr-support-2`. Release the held backend request `rr-research` so its capacity can return to the Gateway. Require backend receipt count 1 for `rr-support-2`. Release the held backend request `rr-support-2` so its capacity can return to the Gateway. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `rr-holder`. Read `rr-holder` directly from the backend receipt endpoint; this observation bypasses the Gateway.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/rr-support-2" -o "$LAB/rr-support-2.receipt.json"
jq -e '.count == 0' "$LAB/rr-support-2.receipt.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/rr-research" | jq .
arrived=false
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/rr-support-2" -o "$LAB/rr-support-2.receipt.json"
  if jq -e '.count == 1' "$LAB/rr-support-2.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/rr-support-2" | jq .
if test -f "$LAB/rr-holder.pid"; then
  wait "$(cat "$LAB/rr-holder.pid")"
fi
test "$(cat "$LAB/rr-holder.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/rr-holder" -o "$LAB/rr-holder.receipt.json"
```

**Step 11 — Verify HTTP 200 and one receipt for each RR request**

Require backend receipt count 1 for `rr-holder`. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `rr-support-1`. Read `rr-support-1` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `rr-support-1`. Require saved HTTP 200 for `rr-research`. Read `rr-research` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `rr-research`. Require saved HTTP 200 for `rr-support-2`. Read `rr-support-2` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `rr-support-2`.

```bash
jq -e '.count == 1' "$LAB/rr-holder.receipt.json"
if test -f "$LAB/rr-support-1.pid"; then
  wait "$(cat "$LAB/rr-support-1.pid")"
fi
test "$(cat "$LAB/rr-support-1.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/rr-support-1" -o "$LAB/rr-support-1.receipt.json"
jq -e '.count == 1' "$LAB/rr-support-1.receipt.json"
if test -f "$LAB/rr-research.pid"; then
  wait "$(cat "$LAB/rr-research.pid")"
fi
test "$(cat "$LAB/rr-research.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/rr-research" -o "$LAB/rr-research.receipt.json"
jq -e '.count == 1' "$LAB/rr-research.receipt.json"
if test -f "$LAB/rr-support-2.pid"; then
  wait "$(cat "$LAB/rr-support-2.pid")"
fi
test "$(cat "$LAB/rr-support-2.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/rr-support-2" -o "$LAB/rr-support-2.receipt.json"
jq -e '.count == 1' "$LAB/rr-support-2.receipt.json"
reached=false
```

**Step 12 — Wait for the RR queue to drain to zero**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/scheduling-state-12.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 0 and .queued == 0' "$LAB/scheduling-state-12.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/scheduling-state-12.json"
```

Expected dispatch: support-1, research, support-2. If it differs, save the receipt arrival times and effective policy; do not infer RR from three eventual HTTP 200s.

### Weighted bands: bounded progress under mixed backlog

Use weights 8:3:1 with no floors or reserve, so the wake algorithm alone determines turns. The shell commands below hold one permit, queue 10 critical, 5 standard and 3 sheddable requests, and release one dispatched request at a time. Change the three case rows to alter the backlog or credentials; change fc_band_weights in the rule to choose the allocation. Keep each band runnable for at least one complete weighted cycle. Every request, response, receipt and dispatch turn is visible below.

**Step 1 — Apply 8:3:1 band weights and read back the config**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 200 for the saved management response before continuing. Send the displayed management request to `/config/loadbalancer/all` and retain its response.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
jq '.serviceArguments += {
  "fc_wake_policy": "weighted",
  "fc_band_weights": "8:3:1",
  "fc_max_queue_depth": 64,
  "fc_max_queue_wait_ms": 60000
}' \
  "$LAB/base-rule.json" > "$LAB/scheduling-rule-13.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/scheduling-rule-13.request.json" \
  -D "$LAB/scheduling-rule-13.headers" -o "$LAB/scheduling-rule-13.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/scheduling-rule-13.response.json"
test "$status" = 200
status=$(ip netns exec share-a curl -sS --max-time 10 -X GET \
  -D "$LAB/scheduling-config-15.headers" -o "$LAB/scheduling-config-15.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer/all")
printf 'HTTP %s\n' "$status"
jq . "$LAB/scheduling-config-15.response.json"
test "$status" = 200
```

**Step 2 — Start the held `weighted-holder` request**

Write `weighted-holder.request.json` with the displayed editable JSON input. Send `weighted-holder` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/weighted-holder.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "weighted-holder"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: weighted-holder' -H 'X-Request-Id: weighted-holder' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/weighted-holder.request.json" \
  -D "$LAB/weighted-holder.headers" -o "$LAB/weighted-holder.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/weighted-holder.http" &
printf '%s\n' "$!" > "$LAB/weighted-holder.pid"
arrived=false
```

**Step 3 — Confirm the backend received `weighted-holder`**

Read `weighted-holder` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `weighted-holder`.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/weighted-holder" -o "$LAB/weighted-holder.receipt.json"
  if jq -e '.count == 1' "$LAB/weighted-holder.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
# Every row describes a band, its backlog size and the credential to use.
: > "$LAB/weighted-pending.txt"
```

**Step 4 — Queue 10 critical, 5 standard and 3 sheddable requests**

This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
for band in critical standard sheddable; do
  case "$band" in
    critical) count=10; identity=support; objective=interactive ;;
    standard) count=5; identity=research; objective= ;;
    sheddable) count=3; identity=support-batch; objective= ;;
  esac
  for number in $(seq 1 "$count"); do
    name="weighted-$band-$number"
    jq -n --arg model "$MODEL" --arg text "$name" \
      '{model:$model,messages:[{role:"user",content:$text}],max_tokens:4}' \
      > "$LAB/$name.request.json"
    # An empty optional header is omitted; it does not choose another class.
    extra_headers=()
    if test -n "$objective"; then
      extra_headers=(-H "x-llm-d-inference-objective: $objective")
    fi
    ip netns exec share-a curl --http1.1 -sS --max-time 55 \
      --config "$LAB/keys/$identity.curl" -H 'Content-Type: application/json' \
      -H "X-Test-Nonce: $name" -H "X-Request-Id: $name" -H 'X-Test-Hold: 1' \
      "${extra_headers[@]}" --data-binary "@$LAB/$name.request.json" \
      -D "$LAB/$name.headers" -o "$LAB/$name.response.json" \
      -w '%{http_code}\n' "$INFER" > "$LAB/$name.http" &
    printf '%s\n' "$!" > "$LAB/$name.pid"
    printf '%s\n' "$name" >> "$LAB/weighted-pending.txt"
  done
done
```

**Step 5 — Wait for 18 waiters, then release `weighted-holder`**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Release the held backend request `weighted-holder` so its capacity can return to the Gateway.

```bash
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/weighted-state-101.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 1 and .queued == 18' "$LAB/weighted-state-101.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/weighted-state-101.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/weighted-holder" | jq .
: > "$LAB/weighted-order.tsv"
```

**Step 6 — Release each dispatched request and record its band**

Read `$name` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `$name`. Release the held backend request `$arrived` so its capacity can return to the Gateway.

```bash
for turn in $(seq 1 18); do
  arrived=''
  for attempt in $(seq 1 100); do
    while read -r name; do
      ip netns exec share-backend curl -fsS --max-time 3 \
        "http://127.0.0.1:8080/receipt/$name" -o "$LAB/$name.receipt.json"
      if jq -e '.count == 1' "$LAB/$name.receipt.json" >/dev/null; then
        arrived="$name"
        break
      fi
    done < "$LAB/weighted-pending.txt"
    test -n "$arrived" && break
    sleep 0.05
  done
  test -n "$arrived"
  band=${arrived#weighted-}
  band=${band%-*}
  printf '%s\t%s\n' "$arrived" "$band" >> "$LAB/weighted-order.tsv"
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/release/$arrived" > "$LAB/$arrived.release.json"
  # grep returns 1 when the last pending row has been removed.
  grep -Fxv "$arrived" "$LAB/weighted-pending.txt" > "$LAB/weighted-pending.tmp" || test "$turn" = 18
  mv "$LAB/weighted-pending.tmp" "$LAB/weighted-pending.txt"
done
```

**Step 7 — Check every response and the first-12 band split**

Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `$name`. Read `$name` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `$name`.

```bash
for file in "$LAB"/weighted-*.pid; do
  name=$(basename "$file" .pid)
  wait "$(cat "$file")"
  test "$(cat "$LAB/$name.http")" = 200
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/$name" -o "$LAB/$name.receipt.json"
  jq -e '.count == 1' "$LAB/$name.receipt.json" >/dev/null
done
cat "$LAB/weighted-order.tsv"
head -n 12 "$LAB/weighted-order.tsv" | cut -f2 | sort | uniq -c
test "$(head -n 12 "$LAB/weighted-order.tsv" | cut -f2 | grep -c '^critical$')" = 8
test "$(head -n 12 "$LAB/weighted-order.tsv" | cut -f2 | grep -c '^standard$')" = 3
test "$(head -n 12 "$LAB/weighted-order.tsv" | cut -f2 | grep -c '^sheddable$')" = 1
reached=false
```

**Step 8 — Wait for the weighted queue to drain to zero**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/scheduling-state-16.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 0 and .queued == 0' "$LAB/scheduling-state-16.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/scheduling-state-16.json"
```

Expected first 12 dispatches, while all bands have runnable backlog: critical 8, standard 3, sheddable 1. Remaining work drains as bands empty; do not require the same ratio after a band runs out. This is a bounded dispatch experiment, not a long-term latency or compute-share guarantee. An invalid weight configuration must leave the accepted policy usable:

**Step 1 — Reject the invalid 8:0:1 weights with HTTP 400**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 400 for the saved management response before continuing.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
jq '.serviceArguments += {
  "fc_wake_policy": "weighted",
  "fc_band_weights": "8:0:1"
}' \
  "$LAB/base-rule.json" > "$LAB/scheduling-rule-17.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/scheduling-rule-17.request.json" \
  -D "$LAB/scheduling-rule-17.headers" -o "$LAB/scheduling-rule-17.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/scheduling-rule-17.response.json"
test "$status" = 400
```

**Step 2 — Send `after-invalid-weight` and expect HTTP 200**

Write `after-invalid-weight.request.json` with the displayed editable JSON input. Send `after-invalid-weight` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `after-invalid-weight`.

```bash
cat > "$LAB/after-invalid-weight.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "after-invalid-weight"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: after-invalid-weight' -H 'X-Request-Id: after-invalid-weight' \
  --data-binary "@$LAB/after-invalid-weight.request.json" \
  -D "$LAB/after-invalid-weight.headers" -o "$LAB/after-invalid-weight.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/after-invalid-weight.http"
if test -f "$LAB/after-invalid-weight.pid"; then
  wait "$(cat "$LAB/after-invalid-weight.pid")"
fi
test "$(cat "$LAB/after-invalid-weight.http")" = 200
```

**Step 3 — Confirm the backend received `after-invalid-weight`**

Read `after-invalid-weight` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `after-invalid-weight`.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/after-invalid-weight" -o "$LAB/after-invalid-weight.receipt.json"
jq -e '.count == 1' "$LAB/after-invalid-weight.receipt.json"
```

### One tenant cannot multiply its inflight share with keys

At ceiling 4 and tenant share 50%, support can hold 2 permits. A second interactive-capable key for the same department cannot obtain a third. Research still proceeds. For this experiment `fc_max_queue_depth: 0` resets to the process default. Setup explicitly sets `LLB_FC_MAX_QUEUE_DEPTH=0`, so the effective depth is zero and the third support request receives an immediate 429. If your process default is nonzero, a rule value of zero inherits that queue; check the effective configuration before expecting immediate refusal.

**Step 1 — Create the `support-secondary` API key**

Write `support-secondary.key-request.json` with the displayed editable JSON input. Send the displayed management request to `/config/ai/apikey` and retain its response. Require HTTP 201 for the saved management response before continuing.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
cat > "$LAB/support-secondary.key-request.json" <<'JSON'
{
  "tenant_id": "support",
  "name": "support-secondary",
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
  -H 'Content-Type: application/json' --data-binary "@$LAB/support-secondary.key-request.json" \
  -o "$LAB/keys/support-secondary.json" -w '%{http_code}' "$API/config/ai/apikey")
test "$status" = 201
jq -er '"header = \"X-Api-Key: " + .raw_key + "\""' \
  "$LAB/keys/support-secondary.json" > "$LAB/keys/support-secondary.curl"
chmod 600 "$LAB/keys/support-secondary.json" "$LAB/keys/support-secondary.curl"
jq '{key_id,tenant_id,allowed_models,priority_class}' "$LAB/keys/support-secondary.json"
```

**Step 2 — Set ceiling 4 with a 50% tenant share**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 200 for the saved management response before continuing.

```bash
jq '.serviceArguments += {
  "fc_max_outstanding": 4,
  "fc_max_queue_depth": 0,
  "fc_tenant_max_share_pct": 50,
  "fc_shed_queue": "off"
}' \
  "$LAB/base-rule.json" > "$LAB/scheduling-rule-19.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/scheduling-rule-19.request.json" \
  -D "$LAB/scheduling-rule-19.headers" -o "$LAB/scheduling-rule-19.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/scheduling-rule-19.response.json"
test "$status" = 200
```

**Step 3 — Start the held `share-support-1` request**

Write `share-support-1.request.json` with the displayed editable JSON input. Send `share-support-1` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/share-support-1.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "share-support-1"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: share-support-1' -H 'X-Request-Id: share-support-1' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/share-support-1.request.json" \
  -D "$LAB/share-support-1.headers" -o "$LAB/share-support-1.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/share-support-1.http" &
printf '%s\n' "$!" > "$LAB/share-support-1.pid"
arrived=false
```

**Step 4 — Confirm the backend received `share-support-1`**

Read `share-support-1` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `share-support-1`. Write `share-support-2.request.json` with the displayed editable JSON input.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/share-support-1" -o "$LAB/share-support-1.receipt.json"
  if jq -e '.count == 1' "$LAB/share-support-1.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
cat > "$LAB/share-support-2.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "share-support-2"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 5 — Start `share-support-2` and confirm its receipt**

Send `share-support-2` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps. Read `share-support-2` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `share-support-2`.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: share-support-2' -H 'X-Request-Id: share-support-2' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/share-support-2.request.json" \
  -D "$LAB/share-support-2.headers" -o "$LAB/share-support-2.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/share-support-2.http" &
printf '%s\n' "$!" > "$LAB/share-support-2.pid"
arrived=false
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/share-support-2" -o "$LAB/share-support-2.receipt.json"
  if jq -e '.count == 1' "$LAB/share-support-2.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
```

**Step 6 — Expect HTTP 429 for `share-same-tenant`**

Write `share-same-tenant.request.json` with the displayed editable JSON input. Send `share-same-tenant` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 429 for `share-same-tenant`.

```bash
cat > "$LAB/share-same-tenant.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "share-same-tenant"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support-secondary.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: share-same-tenant' -H 'X-Request-Id: share-same-tenant' \
  --data-binary "@$LAB/share-same-tenant.request.json" \
  -D "$LAB/share-same-tenant.headers" -o "$LAB/share-same-tenant.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/share-same-tenant.http"
if test -f "$LAB/share-same-tenant.pid"; then
  wait "$(cat "$LAB/share-same-tenant.pid")"
fi
test "$(cat "$LAB/share-same-tenant.http")" = 429
```

**Step 7 — Check `share-same-tenant` was refused, then send `share-other-tenant`**

Read `share-same-tenant` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `share-same-tenant`. Write `share-other-tenant.request.json` with the displayed editable JSON input. Send `share-other-tenant` through the Gateway from the namespace shown below; retain its HTTP status and response separately.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/share-same-tenant" -o "$LAB/share-same-tenant.receipt.json"
jq -e '.count == 0' "$LAB/share-same-tenant.receipt.json"
jq -e '((.["error"] == "admission_tenant_share"))' "$LAB/share-same-tenant.response.json"
cat > "$LAB/share-other-tenant.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "share-other-tenant"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: share-other-tenant' -H 'X-Request-Id: share-other-tenant' \
  --data-binary "@$LAB/share-other-tenant.request.json" \
  -D "$LAB/share-other-tenant.headers" -o "$LAB/share-other-tenant.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/share-other-tenant.http"
```

**Step 8 — Confirm `share-other-tenant` succeeds and release support holds**

Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `share-other-tenant`. Read `share-other-tenant` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `share-other-tenant`. Release the held backend request `share-support-1` so its capacity can return to the Gateway. Release the held backend request `share-support-2` so its capacity can return to the Gateway. Require saved HTTP 200 for `share-support-1`. Read `share-support-1` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `share-support-1`. Require saved HTTP 200 for `share-support-2`. Read `share-support-2` directly from the backend receipt endpoint; this observation bypasses the Gateway.

```bash
if test -f "$LAB/share-other-tenant.pid"; then
  wait "$(cat "$LAB/share-other-tenant.pid")"
fi
test "$(cat "$LAB/share-other-tenant.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/share-other-tenant" -o "$LAB/share-other-tenant.receipt.json"
jq -e '.count == 1' "$LAB/share-other-tenant.receipt.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/share-support-1" | jq .
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/share-support-2" | jq .
if test -f "$LAB/share-support-1.pid"; then
  wait "$(cat "$LAB/share-support-1.pid")"
fi
test "$(cat "$LAB/share-support-1.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/share-support-1" -o "$LAB/share-support-1.receipt.json"
jq -e '.count == 1' "$LAB/share-support-1.receipt.json"
if test -f "$LAB/share-support-2.pid"; then
  wait "$(cat "$LAB/share-support-2.pid")"
fi
test "$(cat "$LAB/share-support-2.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/share-support-2" -o "$LAB/share-support-2.receipt.json"
```

**Step 9 — Wait for the pool to return to idle**

Require backend receipt count 1 for `share-support-2`. Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
jq -e '.count == 1' "$LAB/share-support-2.receipt.json"
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/scheduling-state-21.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 0 and .queued == 0' "$LAB/scheduling-state-21.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/scheduling-state-21.json"
```

Tenant share is local to this pool. Cross-node limits need a separate contract. Continue to [floor and reserve](capacity.md).

## Check your result

Prove a backlog and actual backend admission order; eventual completion order is not dispatch order.

Keep the configured policy, HTTP status, resolved identity, and independent backend receipt together. A rejected request must have receipt 0; a successful request must have receipt 1. A missing receipt response is a failed observation, never a zero.

## Next steps and cleanup

Continue in the documented order with the same LAB. Remove an experiment's binding or temporary rule before the next experiment; stop the shared lab only at the final cleanup chapter. Read the [lab starting point](setup.md) if required values are missing. Use [cleanup and recovery](cleanup.md) when ending the run.
