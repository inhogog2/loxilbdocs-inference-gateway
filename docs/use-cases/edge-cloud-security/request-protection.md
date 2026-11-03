# Authenticate workloads and separate key and tenant request budgets

Verify HTTP identity and request limits without confusing them with packet or connection controls.

<!-- example-status-default: illustrative-only -->

!!! note "Continue in the same lab"
    Use the same root Bash session from [setup](setup.md). Follow the
    [common evidence and rollback conventions](common.md) throughout the exercises.

## Before you start

Return packet/connection controls to the documented baseline and retain private API-key files.

**Focus of this page:** Apply key, tenant and request budgets after the connection has reached HTTP handling.

## Topology and execution locations

--8<-- "snippets/use-cases/topology/edge.md"

All seven containers are on the isolated Docker network 192.0.2.0/24; they are not seven physical machines. No host port is published. A host localhost curl cannot replace docker exec into uc7-gw. Source and service protections act before the request reaches the CPU backend.

| Where | What happens here |
|---|---|
| Host root Bash | Own WORK/LAB, lifecycle inputs and private curl credential files. |
| uc7-a / b / c / d | Send source-specific traffic; preserve the A/B/C/D roles in each experiment. |
| uc7-gw | Run REST curl against localhost:11111 inside the container; enforce controls on inference 8080. |
| uc7-ep | Keep the nonce journal, direct backend observations and optional synthetic KV publisher. |
| uc7-pg | Store policy/keys on .30; interrupt it only in the recovery chapter. |

## Walkthrough

### Prerequisites and a complete authentication result

Use the plain baseline rule with source controls removed. Management JWT and inference key are
separate; `KEY_ID` is a management handle, never the inference credential. The setup key has no
RPS ceiling yet. Full key field/rotation semantics remain in [API key management](../../ai-gateway/api-key-management.md).

```bash
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-key-valid" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/key-valid.txt" 2> "$LAB/key-valid.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/key-valid.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-key-valid" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-key-missing" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/key-missing.txt" 2> "$LAB/key-missing.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/key-missing.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-key-missing" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Require200/receipt 1 and401/receipt 0 respectively. A failed scrape or client timeout is not an
authentication verdict. The backend journal must show `key_present:false` for admitted requests.

### Configure key RPS and verify burst, refusal and refill

A key PATCH updates only named writable fields. Rate1 request/s with burst1 permits one immediate
request after refill. Concurrent requests must return either200 or typed429, with backend receipts
only for admitted nonces. A new connection is not a separate key budget.

```bash
cat > "$LAB/key-rate.json" <<'JSON'
{
  "rate_limit_rps": 1,
  "burst_size": 1
}
JSON
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X PATCH -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/ai/apikey/$KEY_ID" < "$LAB/key-rate.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/ai/apikey/$KEY_ID" > "$LAB/key-readback.json"
jq . "$LAB/key-readback.json"
sleep 15
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-key-first" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/key-first.txt" 2> "$LAB/key-first.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/key-first.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-key-first" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-key-too-soon" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/key-too-soon.txt" 2> "$LAB/key-too-soon.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/key-too-soon.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-key-too-soon" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
sleep 2
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-key-refilled" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/key-refilled.txt" 2> "$LAB/key-refilled.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/key-refilled.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-key-refilled" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Expected: first200/receipt 1, immediate second429/receipt 0, refill200/receipt 1. Inspect the typed
reason/Retry-After where provided; if too much time elapsed between manual requests, use the two
starts below and require an observed429, retaining all attempts.

```bash
sleep 2
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-key-parallel-one" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/key-parallel-one.txt" 2> "$LAB/key-parallel-one.err" &
KEY_ONE=$!
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-key-parallel-two" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/key-parallel-two.txt" 2> "$LAB/key-parallel-two.err" &
KEY_TWO=$!
wait "$KEY_ONE" "$KEY_TWO"
cat "$LAB/key-parallel-one.txt" "$LAB/key-parallel-two.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg prefix "$RUN-key-parallel-" '[.[] | select(.event=="uc7_receipt" and (.nonce | startswith($prefix)))] | {admitted:length,credentials_absent:all(.key_present==false)}' "$LAB/journal.jsonl"
```

The background PID identifies only this host `docker exec`; waiting another PID can hang on a
publisher. Any non200/429 result is a separate failure, not part of an accepted subset.

### Compare two keys in one tenant with another tenant

Clear key RPS before testing the tenant bucket. Create a second key in `edge-team` and a control
key in `edge-control`; keep their files/handles distinct. No default quota ladder or JWT lab is needed.

```bash
cat > "$LAB/key-unlimited.json" <<'JSON'
{
  "rate_limit_rps": 0,
  "burst_size": 0
}
JSON
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X PATCH -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/ai/apikey/$KEY_ID" < "$LAB/key-unlimited.json"
```

```bash
cat > "$LAB/key-second-create.json" <<'JSON'
{
  "tenant_id": "edge-team",
  "name": "edge-second",
  "allowed_models": [
    "Qwen/Qwen3-0.6B"
  ],
  "rate_limit_rps": 0,
  "burst_size": 0,
  "tokens_per_min": 100000,
  "enabled": true
}
JSON
docker exec -i uc7-gw curl -fsS --config /etc/loxilb/control.curl -H 'Content-Type: application/json' --data-binary @- "$API/config/ai/apikey" < "$LAB/key-second-create.json" > "$LAB/key-second.private.json"
export SECOND_KEY_ID=$(jq -er .key_id "$LAB/key-second.private.json")
jq -r '.raw_key | "header = \"X-Api-Key: " + . + "\""' "$LAB/key-second.private.json" > "$LAB/key-second.curl"
docker cp "$LAB/key-second.curl" uc7-c:/run/edge-key.curl
```

```bash
cat > "$LAB/key-control-create.json" <<'JSON'
{
  "tenant_id": "edge-control",
  "name": "edge-control",
  "allowed_models": [
    "Qwen/Qwen3-0.6B"
  ],
  "rate_limit_rps": 0,
  "burst_size": 0,
  "tokens_per_min": 100000,
  "enabled": true
}
JSON
docker exec -i uc7-gw curl -fsS --config /etc/loxilb/control.curl -H 'Content-Type: application/json' --data-binary @- "$API/config/ai/apikey" < "$LAB/key-control-create.json" > "$LAB/key-control.private.json"
export CONTROL_KEY_ID=$(jq -er .key_id "$LAB/key-control.private.json")
jq -r '.raw_key | "header = \"X-Api-Key: " + . + "\""' "$LAB/key-control.private.json" > "$LAB/key-control.curl"
docker cp "$LAB/key-control.curl" uc7-d:/run/edge-key.curl
```

```bash
cat > "$LAB/tenant-rate.json" <<'JSON'
{
  "tenant_id": "edge-team",
  "rps": 1,
  "tokens_per_min": 100000,
  "burst_pct": 0
}
JSON
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/ai/tenant/ratelimit" < "$LAB/tenant-rate.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/ai/tenant/ratelimit/edge-team" > "$LAB/tenant-readback.json"
jq . "$LAB/tenant-readback.json"
sleep 15
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-tenant-first" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/tenant-first.txt" 2> "$LAB/tenant-first.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/tenant-first.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-tenant-first" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-c curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-tenant-second-key" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/tenant-second-key.txt" 2> "$LAB/tenant-second-key.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/tenant-second-key.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-tenant-second-key" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-d curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-tenant-control" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/tenant-control.txt" 2> "$LAB/tenant-control.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/tenant-control.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-tenant-control" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Expected edge-team first200, second key429 with receipt 0, independent edge-control200/receipt 1.
This is process-local aggregation across keys; it is not a distributed quota. `burst_pct` concerns
TPM capacity, not an RPS burst. Omitted tenant aggregate fields write0; model_limits use per-model
upsert, not whole-row replacement. Preserve all prior aggregates/model rows when customizing.

### Pool share is a different resource

The [admission reference](../../ai-gateway/admission-flow-control.md#tenant-fair-share) explains
`fc_tenant_max_share_pct` and effective provenance. RPS limits admissions per second; share limits
how one tenant occupies executing/queued units **in a pool**. A second key in the same tenant does
not create another share. A low process accept valve precedes authentication and cannot reserve slots
for a normal tenant. Do not claim normal-tenant SLA from this short tenant-RPS test. Held-stream,
H2 cancellation and sustained-fairness qualification are [separate experiments](advanced.md).

### Verify a bounded pool-share control with the public hold fixture

Reuse CICD's [HTTP/2 admission backend](https://github.com/loxilb-io/loxilb-inference-gateway/blob/0f78cc3329e23934be4924069b137bfbe557e8f2/cicd/ai-admission/h2c_backend.py)
in the existing backend namespace on8088. It adds one owned host process, not another deployment.
Its delay/nonce headers are fixture controls, not product API fields. The private venv adds pinned h2; it does not modify host Python. The H2 path needs an H2-capable backend: an HTTP/1-only mock produces backend503 instead of an admission verdict.
Clear tenant RPS first so that an RPS429 cannot explain a pool-share rejection. A separate listener8088
uses pool capacity4/share50; two held edge-team requests occupy its2-unit share. H2 requests refuse
instead of entering the H1 queue. The control tenant must still be able to execute.

**Step 1 — Clear tenant RPS and start the H2 hold backend**

Run this in the same Bash session. A trailing & keeps the client active while the following steps inspect contention; its PID must remain a child of this shell for the later wait.

```bash
jq '.rps=0 | .tokens_per_min=0' "$LAB/tenant-rate.json" > "$LAB/tenant-fairness.json"
docker exec -i uc7-gw curl -sS --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- "$API/config/ai/tenant/ratelimit" < "$LAB/tenant-fairness.json"
export EP_PID=$(docker inspect -f '{{.State.Pid}}' uc7-ep)
"$EDGE_VENV/bin/python" -m pip install h2==4.3.0
"$EDGE_VENV/bin/python" -m pip freeze > "$LAB/fairness-dependencies.txt"
nsenter -t "$EP_PID" -n "$EDGE_VENV/bin/python" "$SRC/cicd/ai-admission/h2c_backend.py" edge-share 8088 > "$LAB/fairness-backend.log" 2>&1 &
FAIR_PID=$!
FAIR_TICK=$(awk '{print $22}' "/proc/$FAIR_PID/stat")
sleep 2
docker exec uc7-c curl --http2-prior-knowledge -fsS -w '\n' http://192.0.2.21:8088/__receipts/ready-probe
```

**Step 2 — Prepare `fairness-rule.json`**

Write the complete input before sending it. This step creates a local file; it does not apply policy. Change the displayed values here, then use this same file in the following request.

```bash
cat > "$LAB/fairness-rule.json" <<'JSON'
{
  "serviceArguments": {
    "externalIP": "192.0.2.10",
    "port": 8088,
    "protocol": "tcp",
    "mode": 4,
    "host": "192.0.2.10",
    "model_name": "Qwen/Qwen3-0.6B",
    "api_key_auth": "required",
    "sse_mode": true,
    "fc_mode": "enforce",
    "fc_max_outstanding": 4,
    "fc_tenant_max_share_pct": 50
  },
  "endpoints": [
    {
      "endpointIP": "192.0.2.21",
      "targetPort": 8088,
      "weight": 1
    }
  ]
}
JSON
```

**Step 3 — Hold two requests, then test same-tenant and control access**

Wait for the relevant client and check its saved HTTP code. Fetch receipts directly from the backend namespace: accepted traffic and policy denials have different expected counts.

```bash
docker exec -i uc7-gw curl -sS --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- "$API/config/loadbalancer" < "$LAB/fairness-rule.json"
jq '{model:.model,messages:[{role:"user",content:"fairness"}],max_tokens:8}' "$LAB/request.json" > "$LAB/fairness-request.json"
docker exec -i uc7-a curl --http2-prior-knowledge -sS --max-time 25 --config /run/edge-key.curl -H 'Content-Type: application/json' -H 'X-Test-Delay-Ms: 12000' -H "X-Test-Nonce: $RUN-held-one" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' http://192.0.2.10:8088/v1/chat/completions < "$LAB/fairness-request.json" > "$LAB/held-one.txt" 2> "$LAB/held-one.err" &
HELD_ONE=$!
docker exec -i uc7-c curl --http2-prior-knowledge -sS --max-time 25 --config /run/edge-key.curl -H 'Content-Type: application/json' -H 'X-Test-Delay-Ms: 12000' -H "X-Test-Nonce: $RUN-held-two" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' http://192.0.2.10:8088/v1/chat/completions < "$LAB/fairness-request.json" > "$LAB/held-two.txt" 2> "$LAB/held-two.err" &
HELD_TWO=$!
sleep 2
kill -0 "$HELD_ONE" "$HELD_TWO"
printf 'HELD_ONE_RECEIPTS='
docker exec uc7-c curl --http2-prior-knowledge -fsS -w '\n' "http://192.0.2.21:8088/__receipts/$RUN-held-one"
printf 'HELD_TWO_RECEIPTS='
docker exec uc7-c curl --http2-prior-knowledge -fsS -w '\n' "http://192.0.2.21:8088/__receipts/$RUN-held-two"
docker exec uc7-gw curl -fsS --config /etc/loxilb/control.curl "$API/config/loadbalancer/all" > "$LAB/fairness-effective.json"
jq -e '.lbAttr[] | select(.serviceArguments.port==8088) | .serviceArguments.fc_effective | select(.inflight==2 and .effective_max_outstanding==4 and .tenant_max_share_pct==50)' "$LAB/fairness-effective.json"
docker exec -i uc7-a curl --http2-prior-knowledge -sS --max-time 5 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-share-denied" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' http://192.0.2.10:8088/v1/chat/completions < "$LAB/fairness-request.json"
printf 'SHARE_DENIED_RECEIPTS='
docker exec uc7-c curl --http2-prior-knowledge -fsS -w '\n' "http://192.0.2.21:8088/__receipts/$RUN-share-denied"
docker exec -i uc7-d curl --http2-prior-knowledge -sS --max-time 5 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-share-control" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' http://192.0.2.10:8088/v1/chat/completions < "$LAB/fairness-request.json"
printf 'SHARE_CONTROL_RECEIPTS='
docker exec uc7-c curl --http2-prior-knowledge -fsS -w '\n' "http://192.0.2.21:8088/__receipts/$RUN-share-control"
wait "$HELD_ONE" "$HELD_TWO"
cat "$LAB/held-one.txt" "$LAB/held-two.txt"
docker exec uc7-gw curl -fsS --config /etc/loxilb/control.curl "$API/config/loadbalancer/all" > "$LAB/fairness-released.json"
jq -e '.lbAttr[] | select(.serviceArguments.port==8088) | .serviceArguments.fc_effective | select(.inflight==0)' "$LAB/fairness-released.json"
```

**Step 4 — Delete the 8088 rule and stop the hold backend**

Wait for the relevant client and check its saved HTTP code. Fetch receipts directly from the backend namespace: accepted traffic and policy denials have different expected counts.

```bash
docker exec uc7-gw curl -sS --config /etc/loxilb/control.curl -X DELETE "$API/config/loadbalancer/hosturl/192.0.2.10/externalipaddress/192.0.2.10/port/8088/protocol/tcp?model_name=Qwen%2FQwen3-0.6B"
test "$(awk '{print $22}' "/proc/$FAIR_PID/stat")" = "$FAIR_TICK" && kill "$FAIR_PID"
wait "$FAIR_PID" 2>/dev/null || true
```

Require both still-running holders to have independent backend receipt 1 and effective inflight2/capacity4/share50, same-tenant
third H2 request429 with capacity/share cause and receipt 0, control-tenant H2 request200/receipt 1,
then both held requests200 and effective inflight0 after their12s fixture delays finish. A missing holder or an RPS rejection
makes the share result inconclusive. The same-tenant second key must not get an independent share.
This is a bounded execution-isolation check; each curl uses its own H2 connection, so it does not
qualify multiplexed-stream cancellation or a sustained SLA. Delete the8088 rule and stop only the
recorded fixture process; the main8080 baseline stays intact.

### Restore quotas, prove recovery and cleanup

The tenant row did not exist before this lab. Restore aggregate0/unlimited, rather than inventing a
tenant DELETE endpoint; keep any pre-existing model rows in a customized deployment. Delete the two
extra lab keys and use their same saved credential files to require401/receipt 0 after cache refresh.
Then restore the baseline key in C/D for the next chapter.

**Step 1 — Restore unlimited tenant quotas and revoke the extra keys**

Write `tenant-unlimited.json` and apply it to remove the `edge-team` rate limits, then read back the tenant. Delete the second and control API keys, and send one request with each key to confirm that the backend received neither.

```bash
cat > "$LAB/tenant-unlimited.json" <<'JSON'
{
  "tenant_id": "edge-team",
  "rps": 0,
  "tokens_per_min": 0,
  "burst_pct": 0
}
JSON
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/ai/tenant/ratelimit" < "$LAB/tenant-unlimited.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/ai/tenant/ratelimit/edge-team" > "$LAB/tenant-restored.json"
jq . "$LAB/tenant-restored.json"
docker exec uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X DELETE -w '\nHTTP:%{http_code}\n' "$API/config/ai/apikey/$SECOND_KEY_ID"
docker exec uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X DELETE -w '\nHTTP:%{http_code}\n' "$API/config/ai/apikey/$CONTROL_KEY_ID"
sleep 15
docker exec -i uc7-c curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-second-key-revoked" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/second-key-revoked.txt" 2> "$LAB/second-key-revoked.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/second-key-revoked.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-second-key-revoked" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-d curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-control-key-revoked" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/control-key-revoked.txt" 2> "$LAB/control-key-revoked.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/control-key-revoked.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-control-key-revoked" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

**Step 2 — Restore the baseline key and confirm recovery from A**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
docker cp "$LAB/key.curl" uc7-c:/run/edge-key.curl
docker cp "$LAB/key.curl" uc7-d:/run/edge-key.curl
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-tenant-recovered" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/tenant-recovered.txt" 2> "$LAB/tenant-recovered.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/tenant-recovered.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-tenant-recovered" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Expected extra key deletion/absence and same-credential401, restored tenant aggregates0 and baseline
200/receipt 1. Keep the baseline key until final cleanup. [Coexistence](coexistence.md) sets its explicit
RPS1/burst1 again so the all-on tuple has a deliberate request limit.

### Troubleshooting

If both tenants fail, inspect source/global connection controls and key model permissions first.
Do not call request capacity429 an RPS result. Keep status/body, key/tenant identity, elapsed time,
complete readback and per-nonce backend observations. Full TPM/reservation/cancellation tutorials
remain in [quotas](../admission-flow-control/quotas.md) rather than being duplicated here.

## Check your result

Compare valid, invalid and missing credentials with rate decisions and independent nonce observations.

Keep a normal control request alongside each denied or interrupted request. Separate packet drop, TCP refusal, HTTP denial, backend receipt, and counter changes. Readback establishes stored policy; client traffic and the backend journal establish delivery.

## Next steps and cleanup

Remove the isolated control before adding the next layer. Recovery restores the complete owned tuple; final cleanup uses the recorded ownership state and must preserve unrelated containers. Read the [lab starting point](setup.md) if required values are missing. Use [cleanup and recovery](cleanup.md) when ending the run.
