# Separate minimum progress from emergency headroom

A floor helps a waiting band obtain a returned permit. A reserve prevents other bands from consuming critical headroom even when no critical request is waiting.

<!-- example-status-default: illustrative-only -->

The two experiments change different fields in the visible service JSON. fc_band_min_share_pct is a critical:standard:sheddable triple; fc_critical_reserve_pct is a separate scalar. Edit the percentages and fc_max_outstanding together, then observe the effective integer inflight/queued counts.

## Before you start

Complete scheduling. Prepare all floor/reserve steps before starting their timed traffic.

**Focus of this page:** Change band floors and critical reserve as separate experiments.

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

### Floor: unused capacity is borrowable

Complete [dispatch](scheduling.md). At ceiling 4 with a 25% sheddable floor, standard requests from support and research can occupy all four units while batch is idle. Once batch and critical are both waiting, releasing a standard permit gives the below-floor batch band a turn. Existing work remains running.

**Step 1 — Set ceiling 4 with a 25% sheddable floor**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 200 for the saved management response before continuing.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
jq '.serviceArguments += {
  "fc_max_outstanding": 4,
  "fc_band_min_share_pct": "0:0:25",
  "fc_tenant_max_share_pct": 100
}' \
  "$LAB/base-rule.json" > "$LAB/capacity-rule-1.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/capacity-rule-1.request.json" \
  -D "$LAB/capacity-rule-1.headers" -o "$LAB/capacity-rule-1.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/capacity-rule-1.response.json"
test "$status" = 200
```

**Step 2 — Start the held `floor-1` support request**

Write `floor-1.request.json` with the displayed editable JSON input. Send `floor-1` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/floor-1.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "floor-1"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: floor-1' -H 'X-Request-Id: floor-1' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/floor-1.request.json" \
  -D "$LAB/floor-1.headers" -o "$LAB/floor-1.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/floor-1.http" &
printf '%s\n' "$!" > "$LAB/floor-1.pid"
arrived=false
```

**Step 3 — Confirm the backend received `floor-1`**

Read `floor-1` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `floor-1`. Write `floor-2.request.json` with the displayed editable JSON input.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/floor-1" -o "$LAB/floor-1.receipt.json"
  if jq -e '.count == 1' "$LAB/floor-1.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
cat > "$LAB/floor-2.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "floor-2"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 4 — Start `floor-2` and confirm its receipt**

Send `floor-2` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps. Read `floor-2` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `floor-2`.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: floor-2' -H 'X-Request-Id: floor-2' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/floor-2.request.json" \
  -D "$LAB/floor-2.headers" -o "$LAB/floor-2.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/floor-2.http" &
printf '%s\n' "$!" > "$LAB/floor-2.pid"
arrived=false
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/floor-2" -o "$LAB/floor-2.receipt.json"
  if jq -e '.count == 1' "$LAB/floor-2.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
```

**Step 5 — Start the held `floor-3` research request**

Write `floor-3.request.json` with the displayed editable JSON input. Send `floor-3` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/floor-3.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "floor-3"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: floor-3' -H 'X-Request-Id: floor-3' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/floor-3.request.json" \
  -D "$LAB/floor-3.headers" -o "$LAB/floor-3.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/floor-3.http" &
printf '%s\n' "$!" > "$LAB/floor-3.pid"
arrived=false
```

**Step 6 — Confirm the backend received `floor-3`**

Read `floor-3` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `floor-3`. Write `floor-4.request.json` with the displayed editable JSON input.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/floor-3" -o "$LAB/floor-3.receipt.json"
  if jq -e '.count == 1' "$LAB/floor-3.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
cat > "$LAB/floor-4.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "floor-4"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 7 — Start `floor-4` and confirm its receipt**

Send `floor-4` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps. Read `floor-4` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `floor-4`.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: floor-4' -H 'X-Request-Id: floor-4' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/floor-4.request.json" \
  -D "$LAB/floor-4.headers" -o "$LAB/floor-4.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/floor-4.http" &
printf '%s\n' "$!" > "$LAB/floor-4.pid"
arrived=false
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/floor-4" -o "$LAB/floor-4.receipt.json"
  if jq -e '.count == 1' "$LAB/floor-4.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
reached=false
```

**Step 8 — Confirm all four permits are in use**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/capacity-state-3.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 4 and .queued == 0' "$LAB/capacity-state-3.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/capacity-state-3.json"
```

**Step 9 — Queue `floor-batch` as a sheddable request**

Write `floor-batch.request.json` with the displayed editable JSON input. Send `floor-batch` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/floor-batch.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "floor-batch"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support-batch.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: floor-batch' -H 'X-Request-Id: floor-batch' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/floor-batch.request.json" \
  -D "$LAB/floor-batch.headers" -o "$LAB/floor-batch.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/floor-batch.http" &
printf '%s\n' "$!" > "$LAB/floor-batch.pid"
```

**Step 10 — Queue `floor-critical` as an interactive request**

Write `floor-critical.request.json` with the displayed editable JSON input. Send `floor-critical` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/floor-critical.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "floor-critical"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: floor-critical' -H 'X-Request-Id: floor-critical' \
  -H 'X-Test-Hold: 1' \
  -H x-llm-d-inference-objective:interactive \
  --data-binary "@$LAB/floor-critical.request.json" \
  -D "$LAB/floor-critical.headers" -o "$LAB/floor-critical.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/floor-critical.http" &
printf '%s\n' "$!" > "$LAB/floor-critical.pid"
reached=false
```

**Step 11 — Wait for two waiters, then release `floor-1`**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Release the held backend request `floor-1` so its capacity can return to the Gateway.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/capacity-state-4.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 4 and .queued == 2' "$LAB/capacity-state-4.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/capacity-state-4.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/floor-1" | jq .
arrived=false
```

**Step 12 — Confirm `floor-batch` takes the freed permit**

Read `floor-batch` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `floor-batch`. Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/floor-batch" -o "$LAB/floor-batch.receipt.json"
  if jq -e '.count == 1' "$LAB/floor-batch.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/capacity-state-5.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 4 and .queued == 1' "$LAB/capacity-state-5.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
```

**Step 13 — Release `floor-2` and confirm `floor-critical` dispatch**

Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Read `floor-critical` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `floor-critical`. Release the held backend request `floor-2` so its capacity can return to the Gateway. Require backend receipt count 1 for `floor-critical`. Release the held backend request `floor-3` so its capacity can return to the Gateway. Release the held backend request `floor-4` so its capacity can return to the Gateway.

```bash
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/capacity-state-5.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/floor-critical" -o "$LAB/floor-critical.receipt.json"
jq -e '.count == 0' "$LAB/floor-critical.receipt.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/floor-2" | jq .
arrived=false
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/floor-critical" -o "$LAB/floor-critical.receipt.json"
  if jq -e '.count == 1' "$LAB/floor-critical.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/floor-3" | jq .
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/floor-4" | jq .
```

**Step 14 — Release `floor-batch` and `floor-critical`, then check results**

Release the held backend request `floor-batch` so its capacity can return to the Gateway. Release the held backend request `floor-critical` so its capacity can return to the Gateway. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `floor-1`. Read `floor-1` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `floor-1`. Require saved HTTP 200 for `floor-2`. Read `floor-2` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `floor-2`. Require saved HTTP 200 for `floor-3`. Read `floor-3` directly from the backend receipt endpoint; this observation bypasses the Gateway.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/floor-batch" | jq .
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/floor-critical" | jq .
if test -f "$LAB/floor-1.pid"; then
  wait "$(cat "$LAB/floor-1.pid")"
fi
test "$(cat "$LAB/floor-1.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/floor-1" -o "$LAB/floor-1.receipt.json"
jq -e '.count == 1' "$LAB/floor-1.receipt.json"
if test -f "$LAB/floor-2.pid"; then
  wait "$(cat "$LAB/floor-2.pid")"
fi
test "$(cat "$LAB/floor-2.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/floor-2" -o "$LAB/floor-2.receipt.json"
jq -e '.count == 1' "$LAB/floor-2.receipt.json"
if test -f "$LAB/floor-3.pid"; then
  wait "$(cat "$LAB/floor-3.pid")"
fi
test "$(cat "$LAB/floor-3.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/floor-3" -o "$LAB/floor-3.receipt.json"
```

**Step 15 — Verify `floor-4`, `floor-batch` and `floor-critical` results**

Require backend receipt count 1 for `floor-3`. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `floor-4`. Read `floor-4` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `floor-4`. Require saved HTTP 200 for `floor-batch`. Read `floor-batch` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `floor-batch`. Require saved HTTP 200 for `floor-critical`. Read `floor-critical` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `floor-critical`.

```bash
jq -e '.count == 1' "$LAB/floor-3.receipt.json"
if test -f "$LAB/floor-4.pid"; then
  wait "$(cat "$LAB/floor-4.pid")"
fi
test "$(cat "$LAB/floor-4.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/floor-4" -o "$LAB/floor-4.receipt.json"
jq -e '.count == 1' "$LAB/floor-4.receipt.json"
if test -f "$LAB/floor-batch.pid"; then
  wait "$(cat "$LAB/floor-batch.pid")"
fi
test "$(cat "$LAB/floor-batch.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/floor-batch" -o "$LAB/floor-batch.receipt.json"
jq -e '.count == 1' "$LAB/floor-batch.receipt.json"
if test -f "$LAB/floor-critical.pid"; then
  wait "$(cat "$LAB/floor-critical.pid")"
fi
test "$(cat "$LAB/floor-critical.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/floor-critical" -o "$LAB/floor-critical.receipt.json"
jq -e '.count == 1' "$LAB/floor-critical.receipt.json"
reached=false
```

**Step 16 — Wait for the pool to return to idle**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/capacity-state-6.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 0 and .queued == 0' "$LAB/capacity-state-6.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/capacity-state-6.json"
```

Expected: all four standard holders enter; waiting sheddable enters on the first release while critical still has receipt 0. Floors act under demand, select a highest-ranked below-floor runnable band, and do not evict inflight requests. Small ceilings and integer rounding matter; validate your effective cap rather than extrapolating percentages from this four-unit example.

### Reserve: keep an idle critical unit

Reserve 25% at ceiling 4 with floors reset. Three standard holders enter, the fourth waits despite one idle unit, and a critical request can use it. This is the intentional throughput/headroom tradeoff.

**Step 1 — Set ceiling 4 with a 25% critical reserve**

Send the displayed management request to `/config/loadbalancer` and retain its response. Require HTTP 200 for the saved management response before continuing.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
jq '.serviceArguments += {
  "fc_max_outstanding": 4,
  "fc_critical_reserve_pct": 25
}' \
  "$LAB/base-rule.json" > "$LAB/capacity-rule-7.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/capacity-rule-7.request.json" \
  -D "$LAB/capacity-rule-7.headers" -o "$LAB/capacity-rule-7.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
printf 'HTTP %s\n' "$status"
jq . "$LAB/capacity-rule-7.response.json"
test "$status" = 200
```

**Step 2 — Start the held `reserve-1` request**

Write `reserve-1.request.json` with the displayed editable JSON input. Send `reserve-1` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/reserve-1.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "reserve-1"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: reserve-1' -H 'X-Request-Id: reserve-1' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/reserve-1.request.json" \
  -D "$LAB/reserve-1.headers" -o "$LAB/reserve-1.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/reserve-1.http" &
printf '%s\n' "$!" > "$LAB/reserve-1.pid"
arrived=false
```

**Step 3 — Confirm the backend received `reserve-1`**

Read `reserve-1` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-1`. Write `reserve-2.request.json` with the displayed editable JSON input.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/reserve-1" -o "$LAB/reserve-1.receipt.json"
  if jq -e '.count == 1' "$LAB/reserve-1.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
cat > "$LAB/reserve-2.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "reserve-2"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 4 — Start `reserve-2` and confirm its receipt**

Send `reserve-2` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps. Read `reserve-2` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-2`.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: reserve-2' -H 'X-Request-Id: reserve-2' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/reserve-2.request.json" \
  -D "$LAB/reserve-2.headers" -o "$LAB/reserve-2.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/reserve-2.http" &
printf '%s\n' "$!" > "$LAB/reserve-2.pid"
arrived=false
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/reserve-2" -o "$LAB/reserve-2.receipt.json"
  if jq -e '.count == 1' "$LAB/reserve-2.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
```

**Step 5 — Start the held `reserve-3` request**

Write `reserve-3.request.json` with the displayed editable JSON input. Send `reserve-3` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps.

```bash
cat > "$LAB/reserve-3.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "reserve-3"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: reserve-3' -H 'X-Request-Id: reserve-3' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/reserve-3.request.json" \
  -D "$LAB/reserve-3.headers" -o "$LAB/reserve-3.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/reserve-3.http" &
printf '%s\n' "$!" > "$LAB/reserve-3.pid"
arrived=false
```

**Step 6 — Confirm the backend received `reserve-3`**

Read `reserve-3` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-3`. Write `reserve-4.request.json` with the displayed editable JSON input.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/reserve-3" -o "$LAB/reserve-3.receipt.json"
  if jq -e '.count == 1' "$LAB/reserve-3.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
cat > "$LAB/reserve-4.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "reserve-4"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 7 — Send `reserve-4` and confirm it waits**

Send `reserve-4` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps. Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: reserve-4' -H 'X-Request-Id: reserve-4' \
  -H 'X-Test-Hold: 1' \
  --data-binary "@$LAB/reserve-4.request.json" \
  -D "$LAB/reserve-4.headers" -o "$LAB/reserve-4.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/reserve-4.http" &
printf '%s\n' "$!" > "$LAB/reserve-4.pid"
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/capacity-state-9.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 3 and .queued == 1' "$LAB/capacity-state-9.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
```

**Step 8 — Confirm `reserve-4` has not reached the backend**

Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Read `reserve-4` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 0 for `reserve-4`. Write `reserve-urgent.request.json` with the displayed editable JSON input.

```bash
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/capacity-state-9.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/reserve-4" -o "$LAB/reserve-4.receipt.json"
jq -e '.count == 0' "$LAB/reserve-4.receipt.json"
cat > "$LAB/reserve-urgent.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "reserve-urgent"
    }
  ],
  "max_tokens": 4
}
JSON
```

**Step 9 — Send `reserve-urgent` into the reserved unit**

Send `reserve-urgent` through the Gateway from the namespace shown below; retain its HTTP status and response separately. This client runs in the background; keep the same Bash session for the later release and wait steps. Read `reserve-urgent` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-urgent`.

```bash
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: reserve-urgent' -H 'X-Request-Id: reserve-urgent' \
  -H 'X-Test-Hold: 1' \
  -H x-llm-d-inference-objective:interactive \
  --data-binary "@$LAB/reserve-urgent.request.json" \
  -D "$LAB/reserve-urgent.headers" -o "$LAB/reserve-urgent.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/reserve-urgent.http" &
printf '%s\n' "$!" > "$LAB/reserve-urgent.pid"
arrived=false
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/reserve-urgent" -o "$LAB/reserve-urgent.receipt.json"
  if jq -e '.count == 1' "$LAB/reserve-urgent.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
reached=false
```

**Step 10 — Confirm full use, then release `reserve-urgent`**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Release the held backend request `reserve-urgent` so its capacity can return to the Gateway. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `reserve-urgent`. Read `reserve-urgent` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-urgent`.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/capacity-state-10.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 4 and .queued == 1' "$LAB/capacity-state-10.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/capacity-state-10.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/reserve-urgent" | jq .
if test -f "$LAB/reserve-urgent.pid"; then
  wait "$(cat "$LAB/reserve-urgent.pid")"
fi
test "$(cat "$LAB/reserve-urgent.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/reserve-urgent" -o "$LAB/reserve-urgent.receipt.json"
jq -e '.count == 1' "$LAB/reserve-urgent.receipt.json"
```

**Step 11 — Confirm three running and one waiting, then release `reserve-1`**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Release the held backend request `reserve-1` so its capacity can return to the Gateway.

```bash
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/capacity-state-11.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 3 and .queued == 1' "$LAB/capacity-state-11.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/capacity-state-11.json"
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/reserve-1" | jq .
arrived=false
```

**Step 12 — Confirm `reserve-4` dispatches and release the holds**

Read `reserve-4` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-4`. Release the held backend request `reserve-2` so its capacity can return to the Gateway. Release the held backend request `reserve-3` so its capacity can return to the Gateway. Release the held backend request `reserve-4` so its capacity can return to the Gateway. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `reserve-1`. Read `reserve-1` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-1`.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-backend curl -fsS --max-time 3 \
    "http://127.0.0.1:8080/receipt/reserve-4" -o "$LAB/reserve-4.receipt.json"
  if jq -e '.count == 1' "$LAB/reserve-4.receipt.json" >/dev/null; then
    arrived=true
    break
  fi
  sleep 0.1
done
test "$arrived" = true
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/reserve-2" | jq .
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/reserve-3" | jq .
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/release/reserve-4" | jq .
if test -f "$LAB/reserve-1.pid"; then
  wait "$(cat "$LAB/reserve-1.pid")"
fi
test "$(cat "$LAB/reserve-1.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/reserve-1" -o "$LAB/reserve-1.receipt.json"
jq -e '.count == 1' "$LAB/reserve-1.receipt.json"
```

**Step 13 — Verify `reserve-2` through `reserve-4` results**

Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `reserve-2`. Read `reserve-2` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-2`. Require saved HTTP 200 for `reserve-3`. Read `reserve-3` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-3`. Require saved HTTP 200 for `reserve-4`. Read `reserve-4` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-4`.

```bash
if test -f "$LAB/reserve-2.pid"; then
  wait "$(cat "$LAB/reserve-2.pid")"
fi
test "$(cat "$LAB/reserve-2.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/reserve-2" -o "$LAB/reserve-2.receipt.json"
jq -e '.count == 1' "$LAB/reserve-2.receipt.json"
if test -f "$LAB/reserve-3.pid"; then
  wait "$(cat "$LAB/reserve-3.pid")"
fi
test "$(cat "$LAB/reserve-3.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/reserve-3" -o "$LAB/reserve-3.receipt.json"
jq -e '.count == 1' "$LAB/reserve-3.receipt.json"
if test -f "$LAB/reserve-4.pid"; then
  wait "$(cat "$LAB/reserve-4.pid")"
fi
test "$(cat "$LAB/reserve-4.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/reserve-4" -o "$LAB/reserve-4.receipt.json"
jq -e '.count == 1' "$LAB/reserve-4.receipt.json"
reached=false
```

**Step 14 — Wait for idle, then submit an invalid reserve rule**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Send the displayed management request to `/config/loadbalancer` and retain its response.

```bash
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/capacity-state-12.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 0 and .queued == 0' "$LAB/capacity-state-12.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/capacity-state-12.json"
jq '.serviceArguments += {
  "fc_critical_reserve_pct": 60,
  "fc_band_min_share_pct": "0:50:0"
}' \
  "$LAB/base-rule.json" > "$LAB/capacity-rule-13.request.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X POST \
  -H 'Content-Type: application/json' --data-binary "@$LAB/capacity-rule-13.request.json" \
  -D "$LAB/capacity-rule-13.headers" -o "$LAB/capacity-rule-13.response.json" \
  -w '%{http_code}' "$API/config/loadbalancer")
```

**Step 15 — Confirm HTTP 400 and send `reserve-invalid-preserves`**

Require HTTP 400 for the saved management response before continuing. Write `reserve-invalid-preserves.request.json` with the displayed editable JSON input. Send `reserve-invalid-preserves` through the Gateway from the namespace shown below; retain its HTTP status and response separately.

```bash
printf 'HTTP %s\n' "$status"
jq . "$LAB/capacity-rule-13.response.json"
test "$status" = 400
cat > "$LAB/reserve-invalid-preserves.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "reserve-invalid-preserves"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: reserve-invalid-preserves' -H 'X-Request-Id: reserve-invalid-preserves' \
  --data-binary "@$LAB/reserve-invalid-preserves.request.json" \
  -D "$LAB/reserve-invalid-preserves.headers" -o "$LAB/reserve-invalid-preserves.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/reserve-invalid-preserves.http"
```

**Step 16 — Confirm `reserve-invalid-preserves` succeeded**

Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `reserve-invalid-preserves`. Read `reserve-invalid-preserves` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `reserve-invalid-preserves`.

```bash
if test -f "$LAB/reserve-invalid-preserves.pid"; then
  wait "$(cat "$LAB/reserve-invalid-preserves.pid")"
fi
test "$(cat "$LAB/reserve-invalid-preserves.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/reserve-invalid-preserves" -o "$LAB/reserve-invalid-preserves.receipt.json"
jq -e '.count == 1' "$LAB/reserve-invalid-preserves.receipt.json"
```

The noncritical floors plus reserve must fit the capacity contract. Do not combine floor/reserve percentages as if both were per-tenant quotas. Adaptive ceilings can change effective integer allocation; this lab keeps adaptation off/default and does not qualify that interaction. Continue to [overload](overload.md).

## Check your result

A floor is borrowable while idle; a reserve deliberately keeps noncritical work from using idle headroom.

Keep the configured policy, HTTP status, resolved identity, and independent backend receipt together. A rejected request must have receipt 0; a successful request must have receipt 1. A missing receipt response is a failed observation, never a zero.

## Next steps and cleanup

Continue in the documented order with the same LAB. Remove an experiment's binding or temporary rule before the next experiment; stop the shared lab only at the final cleanup chapter. Read the [lab starting point](setup.md) if required values are missing. Use [cleanup and recovery](cleanup.md) when ending the run.
