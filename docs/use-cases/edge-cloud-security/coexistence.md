# Keep routing and streaming working with the controls enabled

Combine proven layers and retain independent normal delivery, protocol and routing observations.

<!-- example-status-default: illustrative-only -->

!!! note "Continue in the same lab"
    Use the same root Bash session from [setup](setup.md). Follow the
    [common evidence and rollback conventions](common.md) throughout the exercises.

## Before you start

Complete isolated controls and restore the baseline before combining their exact tuple.

**Focus of this page:** Add synthetic KV events and retain H2/SSE delivery with all selected protections enabled.

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

### Prerequisites: one explicit tuple

Complete isolated controls and restore their baseline state. This chapter deliberately combines
A/C/D allowedSources, B blacklist, D operator TC drop, source rate10/5/100, keyRPS1/burst1,
listener slots4/process context bound16 and synthetic KV/H2/SSE. C is allowed by the fence and may
be rate limited; B is never an alternate normal control. Do not mix another campaign's source roles.
Byte-shaper performance is covered by [QoS](../../operations/ai-qos.md); it is not added as another
bandwidth campaign here.

### Configure synthetic KV and prove a positive baseline

Replace the lab's plain baseline with a fresh KV rule: delete only the owned full key, then create
its KV configuration as shown below. Keep the publisher, inventory, positive hit delta and independent
backend receipt checks together. A policy POST or effective label alone does not establish routing.

Use the fixed tokenizer/corpus prepared by CICD. Model name, request prompt bytes, tokenizer, block16,
sha256_cbor and seed0 must agree. The source's legacy fixture is explicitly **unattested**. A routing
hit is not real engine reuse. On a source with a migration fence, stop; do not disable its guard.
Use [profiles/readiness](../../ai-gateway/model-profiles-kv-readiness.md) for strict production bindings.

**Step 1 — Prepare `lb-coexistence.json`**

Write the complete input before sending it. This step creates a local file; it does not apply policy. Change the displayed values here, then use this same file in the following request.

```bash
cat > "$LAB/lb-coexistence.json" <<'JSON'
{
  "serviceArguments": {
    "externalIP": "192.0.2.10",
    "port": 8080,
    "protocol": "tcp",
    "mode": 4,
    "host": "192.0.2.10",
    "model_name": "Qwen/Qwen3-0.6B",
    "inactiveTimeOut": 60,
    "connectionLimit": 4,
    "api_key_auth": "required",
    "kvExactMode": 3,
    "kvZmqPort": 5557,
    "kvHashAlgo": "sha256_cbor",
    "kvBlockSize": 16,
    "kvEngineType": "vllm",
    "sse_mode": true
  },
  "endpoints": [
    {
      "endpointIP": "192.0.2.21",
      "targetPort": 80,
      "weight": 1
    }
  ],
  "allowedSources": [
    {
      "prefix": "192.0.2.50/32"
    },
    {
      "prefix": "192.0.2.52/32"
    },
    {
      "prefix": "192.0.2.53/32"
    }
  ]
}
JSON
```

**Step 2 — Apply the KV rule, start the publisher and send baselines**

Run this in the same Bash session. A trailing & keeps the client active while the following steps inspect contention; its PID must remain a child of this shell for the later wait.

```bash
cp "$LAB/lb-coexistence.json" "$LAB/model.json"
docker exec uc7-gw curl -sS --config /etc/loxilb/control.curl -X DELETE "$API/config/loadbalancer/hosturl/192.0.2.10/externalipaddress/192.0.2.10/port/8080/protocol/tcp?model_name=Qwen%2FQwen3-0.6B"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/loadbalancer" < "$LAB/model.json"
export EP_PID=$(docker inspect -f '{{.State.Pid}}' uc7-ep)
PYTHONHASHSEED=0 nsenter -t "$EP_PID" -n "$EDGE_VENV/bin/python" "$SRC/cicd/vllm-kvcache-routing-cpu/kv_event_publisher.py" --corpus "$LAB/corpus.json" --tokenizer "$SRC/cicd/common/kv_hash/fixtures/tokenizers/Qwen__Qwen3-0.6B/tokenizer.json" --vectors "$SRC/cicd/common/kv_hash/fixtures/kv_hash_vectors.json" --bind 192.0.2.21 --port 5557 --algo sha256_cbor --block-size 16 --repeat 100 --repeat-interval 5 --no-vocabulary > "$LAB/publisher.log" 2>&1 &
export PUB_PID=$!
export PUB_TICK=$(awk '{print $22}' /proc/"$PUB_PID"/stat)
sleep 12
kill -0 "$PUB_PID"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-kv-warmup" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/kv-warmup.txt" 2> "$LAB/kv-warmup.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/kv-warmup.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-kv-warmup" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/kv-before.prom"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-kv-delivered" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/kv-delivered.txt" 2> "$LAB/kv-delivered.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/kv-delivered.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-kv-delivered" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/kv-after.prom"
python3 "$INPUTS/metric-delta.py" "$LAB/kv-before.prom" "$LAB/kv-after.prom" loxilb_pd_kv_tier15_hits_total
```

**Step 3 — Read back the effective KV binding status**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/loadbalancer/externalipaddress/192.0.2.10/port/8080/protocol/tcp/kvexactstatus?model_name=Qwen%2FQwen3-0.6B" > "$LAB/kv-effective.json"
jq . "$LAB/kv-effective.json"
```

Require valid effective legacy binding/inventory,200/receipt 1 and hit delta>0. Generic healthy status
or an earlier candidate's counter is insufficient. Missing positive KV baseline blocks the combined
routing claim. Read [routing verification](../../operations/kv-routing-verification.md) for miss reasons.

### Enable source, service and request protections

```bash
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/ipfilter" < "$LAB/blacklist.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/securityrate" < "$LAB/rate-source.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/firewall" < "$LAB/firewall-drop.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X PATCH -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/ai/apikey/$KEY_ID" < "$LAB/key-rate.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/loadbalancer/all" > "$LAB/all-on-lb.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/securityrate/all" > "$LAB/all-on-rate.json"
sleep 15
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-all-normal" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/all-normal.txt" 2> "$LAB/all-normal.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/all-normal.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-all-normal" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-b curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-all-blacklist" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/all-blacklist.txt" 2> "$LAB/all-blacklist.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/all-blacklist.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-all-blacklist" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-d curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-all-firewall" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/all-firewall.txt" 2> "$LAB/all-firewall.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/all-firewall.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-all-firewall" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-all-missing" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/all-missing.txt" 2> "$LAB/all-missing.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/all-missing.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-all-missing" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Expected A: 200/receipt 1, B/D timeout/receipt 0, A missing-key401/receipt 0. Record installed payloads,
readback, complete errors and backend key stripping. Warm up owning counter series before measuring;
keep that probe outside the before/after interval.

### Verify HTTP/1.1 and actual HTTP/2 streaming

```bash
docker exec uc7-a curl --version
jq '.stream=true' "$LAB/request.json" > "$LAB/stream.json"
sleep 2
docker exec -i uc7-a curl -sS --http1.1 -N --connect-timeout 2 --max-time 10 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-sse-h1" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/stream.json" > "$LAB/sse-h1.txt" 2> "$LAB/sse-h1.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/sse-h1.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-sse-h1" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
sleep 2
docker exec -i uc7-a curl -sS --http2-prior-knowledge -N --connect-timeout 2 --max-time 10 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-sse-h2" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/stream.json" > "$LAB/sse-h2.txt" 2> "$LAB/sse-h2.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/sse-h2.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-sse-h2" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-a curl -sS --http2-prior-knowledge -N --connect-timeout 2 --max-time 10 -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-h2-missing" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/stream.json" > "$LAB/h2-missing.txt" 2> "$LAB/h2-missing.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/h2-missing.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-h2-missing" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
grep -c '^data: \[DONE\]' "$LAB/sse-h1.txt"
grep -c '^data: \[DONE\]' "$LAB/sse-h2.txt"
```

Require H1 version1.1 and H2 version2, each200/curl 0/content/usage/**one** DONE/receipt 1 and no
credential upstream. Missing-key H2 is401/version2/receipt 0. H2 nonstream plus H1 stream is not H2
stream qualification. Confirm actual backend protocol in the receipt, not just curl's requested option.

### Verify bounded attack coexistence and owning counter deltas

Measure the same all-on interval. B and D warm-ups above established their series; the normal KV
baseline established its series. Save the before snapshot, stimulate B/D again, and send fresh C
connections while A submits one normal request. C's failed requests are retained, not removed from
the denominator. This is a short controlled experiment, not a sustained tenant SLA.

**Step 1 — Probe B and D, then flood from C while A sends**

Wait for the relevant client and check its saved HTTP code. Fetch receipts directly from the backend namespace: accepted traffic and policy denials have different expected counts.

```bash
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/all-before.prom"
docker exec -i uc7-b curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-measured-blacklist" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/measured-blacklist.txt" 2> "$LAB/measured-blacklist.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/measured-blacklist.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-measured-blacklist" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-d curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-measured-firewall" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/measured-firewall.txt" 2> "$LAB/measured-firewall.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/measured-firewall.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-measured-firewall" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
sleep 2
docker exec uc7-gw curl -fsS --config /etc/loxilb/control.curl "$API/config/securityrate/all" > "$LAB/all-source-before.json"
docker exec uc7-c curl --parallel --parallel-immediate --parallel-max 16 -sS --max-time 1 -o /dev/null -w '%{http_code}\n' 'http://192.0.2.10:8080/v1/models?probe=[1-100]' > "$LAB/flood.txt" 2> "$LAB/flood.err" &
FLOOD_PID=$!
sleep 0.2
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-normal-during-flood" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/normal-during-flood.txt" 2> "$LAB/normal-during-flood.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/normal-during-flood.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-normal-during-flood" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
wait "$FLOOD_PID"
printf 'FLOOD_EXIT=%s\n' "$?"
sleep 2
```

**Step 2 — Send two key-limited requests and compare counter deltas**

Wait for the relevant client and check its saved HTTP code. Fetch receipts directly from the backend namespace: accepted traffic and policy denials have different expected counts.

```bash
docker exec -i uc7-a curl -sS --http1.1 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-all-rps-one" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/all-rps-one.txt" 2> "$LAB/all-rps-one.err" &
ALL_RPS_ONE=$!
docker exec -i uc7-a curl -sS --http1.1 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-all-rps-two" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/all-rps-two.txt" 2> "$LAB/all-rps-two.err" &
ALL_RPS_TWO=$!
wait "$ALL_RPS_ONE" "$ALL_RPS_TWO"
cat "$LAB/all-rps-one.txt" "$LAB/all-rps-two.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg prefix "$RUN-all-rps-" '[.[] | select(.event=="uc7_receipt" and (.nonce | startswith($prefix)))] | {admitted:length,credentials_absent:all(.key_present==false)}' "$LAB/journal.jsonl"
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/all-after.prom"
python3 "$INPUTS/metric-delta.py" "$LAB/all-before.prom" "$LAB/all-after.prom" loxilb_ipfilter_blacklist_packets_total loxilb_fw_rule_drop_packets_total loxilb_pd_kv_tier15_hits_total loxilb_ai_rate_limit_hits_total
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/securityrate/all" > "$LAB/all-source-counters.json"
jq . "$LAB/all-source-counters.json"
python3 - "$LAB/all-source-before.json" "$LAB/all-source-counters.json" <<'PYCODE'
import json, sys
before = json.load(open(sys.argv[1]))['securityrateAttr'][0]['connBlocked']
after = json.load(open(sys.argv[2]))['securityrateAttr'][0]['connBlocked']
assert isinstance(before, int) and isinstance(after, int) and 0 <= before < after
print('source_conn_blocked_delta=' + str(after-before))
PYCODE
```

Require normal-during-flood200/receipt 1, the two all-on key probes to include one200 and one429 with exactly one admitted receipt, plus the named positive deltas and isolated connection-rate
blocked delta over its preceding readback. If A times out, the experiment is RED even if another
normal request succeeds afterwards. Record how long each arm ran and all100 C outcomes.

### Cleanup and troubleshooting

Keep this tuple installed for [recovery](recovery.md). The publisher has100 five-second repeats;
check it is alive before each KV interval and restart only the recorded owned publisher if expired,
recording a new PID/start time. Do not merge a failed baseline and later successful subset.
A snapshot restore can deliberately require KV migration even while ordinary inference still works;
that is addressed in the next chapter, not silently relabelled as a hit.

## Check your result

Synthetic routing hits do not prove native model cache reuse; keep inventory, protocol and receipts separate.

Keep a normal control request alongside each denied or interrupted request. Separate packet drop, TCP refusal, HTTP denial, backend receipt, and counter changes. Readback establishes stored policy; client traffic and the backend journal establish delivery.

## Next steps and cleanup

Remove the isolated control before adding the next layer. Recovery restores the complete owned tuple; final cleanup uses the recorded ownership state and must preserve unrelated containers. Read the [lab starting point](setup.md) if required values are missing. Use [cleanup and recovery](cleanup.md) when ending the run.
