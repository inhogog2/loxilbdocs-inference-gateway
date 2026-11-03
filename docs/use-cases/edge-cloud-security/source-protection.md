# Protect sources before the proxy

Apply XDP source filtering and isolate source packet-rate guards before adding a shared-service fence.

<!-- example-status-default: illustrative-only -->

!!! note "Continue in the same lab"
    Use the same root Bash session from [setup](setup.md). Follow the
    [common evidence and rollback conventions](common.md) throughout the exercises.

## Before you start

Start from the plain baseline with the documented A/B/C/D source roles.

**Focus of this page:** Change XDP source controls and source/aggregate packet budgets before HTTP handling.

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

### Prerequisites and source-only baseline

Start with the plain setup rule: no allowedSources fence, no rate policy or firewall. A and B must
both return200/receipt 1 with the lab key. This prevents a TC fence from masquerading as XDP blocking.

```bash
docker exec -i uc7-b curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-source-before" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/source-before.txt" 2> "$LAB/source-before.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/source-before.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-source-before" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

### Configure and verify XDP blacklist

`cidr` identifies B's ingress source; this is not a model or key filter. The list/prefix forms the
DELETE key. `priority` is integer0..65535, larger wins; zone is0 or omitted because filtering precedes
zone classification. A matching whitelist wins equal priority. Keep backend/store/event sources out
of blacklist tests.

**Step 1 — Blacklist source B and probe B and A**

Write `blacklist.json`, apply it to drop source B (192.0.2.51), and read back the IP filters. Then send a warm-up and a denied request from B, check that the backend received no denied request, and send a normal request from A.

```bash
cat > "$LAB/blacklist.json" <<'JSON'
{
  "filterType": "blacklist",
  "cidr": "192.0.2.51/32",
  "action": "drop",
  "priority": 210
}
JSON
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/ipfilter" < "$LAB/blacklist.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/ipfilter/all" > "$LAB/ipfilter.json"
jq . "$LAB/ipfilter.json"
docker exec -i uc7-b curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-blacklist-warmup" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/blacklist-warmup.txt" 2> "$LAB/blacklist-warmup.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/blacklist-warmup.txt"
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/before.prom"
docker exec -i uc7-b curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-blacklist-denied" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/blacklist-denied.txt" 2> "$LAB/blacklist-denied.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/blacklist-denied.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-blacklist-denied" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-blacklist-normal" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/blacklist-normal.txt" 2> "$LAB/blacklist-normal.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/blacklist-normal.txt"
```

**Step 2 — Confirm A's receipt and the blacklist drop delta**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-blacklist-normal" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/after.prom"
python3 "$INPUTS/metric-delta.py" "$LAB/before.prom" "$LAB/after.prom" loxilb_ipfilter_blacklist_packets_total
```

Expected: POST/GET 200; B HTTP 000/curl 28/receipt 0, A: 200/curl 0/receipt 1, and blacklist delta>0.
The warm-up establishes a real exported series and is separate from the measured case. If a sample
is still absent after bounded re-scrapes, record observation failure. Never replace it with0.

Verify malformed input rejects without replacing the existing policy. Save the canonical list before/after.

```bash
jq '.zone=1' "$LAB/blacklist.json" > "$LAB/ipfilter-invalid.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/ipfilter/all" > "$LAB/ipfilter-before.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/ipfilter" < "$LAB/ipfilter-invalid.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/ipfilter/all" > "$LAB/ipfilter-after.json"
jq -S 'walk(if type=="object" then del(.packets,.bytes) else . end)' "$LAB/ipfilter-before.json" > "$LAB/ipfilter-before.canonical.json"
jq -S 'walk(if type=="object" then del(.packets,.bytes) else . end)' "$LAB/ipfilter-after.json" > "$LAB/ipfilter-after.canonical.json"
cmp "$LAB/ipfilter-before.canonical.json" "$LAB/ipfilter-after.canonical.json"
docker exec uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X DELETE -w '\nHTTP:%{http_code}\n' "$API/config/ipfilter?filterType=blacklist&cidr=192.0.2.51/32"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/ipfilter/all" > "$LAB/ipfilter-removed.json"
jq . "$LAB/ipfilter-removed.json"
docker exec -i uc7-b curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-blacklist-recovered" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/blacklist-recovered.txt" 2> "$LAB/blacklist-recovered.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/blacklist-recovered.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-blacklist-recovered" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Expected: invalid zone400 with canonical policy unchanged, then exact-prefix absence and B: 200/receipt 1.

### Configure source packet rate and verify recovery

The complete eight required fields below are a replacement, even for disabled guards. SYN and
connection-rate controls both count SYN packets, not completed handshakes. UDP byte limits are MiB/s.
First exercise UDP by itself so that a SYN drop cannot explain the result.

**Step 1 — Apply a UDP-only guard and measure blocked datagrams**

Write `rate-source.json`, derive a UDP-only variant with a threshold of 2 packets, apply it and read it back. Then send UDP bursts from C and measure the change in `loxilb_security_udp_blocked_total`.

```bash
cat > "$LAB/rate-source.json" <<'JSON'
{
  "synEnabled": true,
  "synThreshold": 10,
  "cookieThreshold": 5,
  "connRateEnabled": true,
  "ratePerSec": 5,
  "udpEnabled": true,
  "udpPktThreshold": 100,
  "udpBandwidthMB": 100
}
JSON
jq '.synEnabled=false | .connRateEnabled=false | .udpPktThreshold=2' "$LAB/rate-source.json" > "$LAB/rate-udp.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/securityrate" < "$LAB/rate-udp.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/securityrate/all" > "$LAB/rate-readback.json"
jq . "$LAB/rate-readback.json"
docker exec uc7-c bash -c 'for n in {1..20}; do printf edge > /dev/udp/192.0.2.10/8080; done'
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/udp-before.prom"
sleep 2
docker exec uc7-c bash -c 'for n in {1..20}; do printf edge > /dev/udp/192.0.2.10/8080; done'
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/udp-after.prom"
python3 "$INPUTS/metric-delta.py" "$LAB/udp-before.prom" "$LAB/udp-after.prom" loxilb_security_udp_blocked_total
```

**Step 2 — Confirm normal TCP delivery from A under the UDP guard**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-udp-normal" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/udp-normal.txt" 2> "$LAB/udp-normal.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/udp-normal.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-udp-normal" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Require the UDP blocked counter to increase and normal TCP200/receipt 1. Twenty datagrams may span
aligned windows; do not assert exact pass/drop cardinality from a shell timing assumption. This
exercise proves guard activity and unaffected TCP delivery, not UDP backend delivery or byte shaping.

To isolate SYN versus connection-SYN, use the full input below in two separate arms. The URL glob
produces20 fresh requests with up to16 transfers. Save curl errors as observations; a timeout alone
is insufficient. Record the named counter, then disable protection and require normal recovery.

```bash
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/securityrate/all" > "$LAB/syn-before.json"
jq '[.securityrateAttr[] | {synBlocked:(.synBlocked // 0)}]' "$LAB/syn-before.json"
jq '.synEnabled=true | .synThreshold=2 | .cookieThreshold=1 | .connRateEnabled=false | .udpEnabled=false' "$LAB/rate-source.json" > "$LAB/rate-syn.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/securityrate" < "$LAB/rate-syn.json"
docker exec uc7-c curl --parallel --parallel-immediate --parallel-max 16 -sS --max-time 2 -o /dev/null -w '%{http_code}
' 'http://192.0.2.10:8080/v1/models?probe=[1-20]' > "$LAB/syn-probes.txt" 2> "$LAB/syn-probes.err"
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/securityrate/all" > "$LAB/syn-counters.json"
jq . "$LAB/syn-counters.json"
jq -en --slurpfile before "$LAB/syn-before.json" --slurpfile after "$LAB/syn-counters.json" '($after[0].securityrateAttr | map(.synBlocked // 0) | add // 0) > ($before[0].securityrateAttr | map(.synBlocked // 0) | add // 0)'
docker exec uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X DELETE -w '\nHTTP:%{http_code}\n' "$API/config/securityrate"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/securityrate/all" > "$LAB/conn-syn-before.json"
jq '.synEnabled=false | .connRateEnabled=true | .ratePerSec=2 | .udpEnabled=false' "$LAB/rate-source.json" > "$LAB/rate-conn-syn.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/securityrate" < "$LAB/rate-conn-syn.json"
docker exec uc7-c curl --parallel --parallel-immediate --parallel-max 16 -sS --max-time 2 -o /dev/null -w '%{http_code}
' 'http://192.0.2.10:8080/v1/models?probe=[1-20]' > "$LAB/conn-syn-probes.txt" 2> "$LAB/conn-syn-probes.err"
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/securityrate/all" > "$LAB/conn-syn-counters.json"
jq . "$LAB/conn-syn-counters.json"
jq -en --slurpfile before "$LAB/conn-syn-before.json" --slurpfile after "$LAB/conn-syn-counters.json" '($after[0].securityrateAttr | map(.connBlocked // 0) | add // 0) > ($before[0].securityrateAttr | map(.connBlocked // 0) | add // 0)'
docker exec uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X DELETE -w '\nHTTP:%{http_code}\n' "$API/config/securityrate"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-source-rate-recovered" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/source-rate-recovered.txt" 2> "$LAB/source-rate-recovered.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/source-rate-recovered.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-source-rate-recovered" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Expect the isolated SYN or connection blocked counter to increase over its pre-arm readback, then
A: 200/receipt 1 after DELETE. The saved pre-arm JSON and positive comparison distinguish retained counters from new blocks. Disabled guards may omit a zero-valued counter; this API representation is separate from a missing Prometheus series.
`cookieThreshold` telemetry is not kernel-cookie proof. Do not count401s as accepted inference requests.

### Optional aggregate replacement and invalid-input check

Per-source limits allow each new source its own budget. Aggregate limits share one aligned-window
budget across listeners/interfaces/families, before tenant authentication. They can also reject
normal traffic. Whitelisted sources bypass rate guards, and their map is shared with IP filters.

```bash
cat > "$LAB/rate-aggregate.json" <<'JSON'
{
  "synEnabled": false,
  "synThreshold": 100,
  "cookieThreshold": 50,
  "connRateEnabled": false,
  "ratePerSec": 100,
  "udpEnabled": false,
  "udpPktThreshold": 100,
  "udpBandwidthMB": 100,
  "whitelistIps": [],
  "aggregateSynThreshold": 120,
  "aggregateConnRatePerSec": 0,
  "aggregateUdpPktThreshold": 120,
  "aggregateUdpBandwidthMB": 0
}
JSON
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/securityrate" < "$LAB/rate-aggregate.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/securityrate/all" > "$LAB/aggregate-readback.json"
jq . "$LAB/aggregate-readback.json"
jq '.aggregateSynThreshold=0 | .aggregateUdpPktThreshold=0' "$LAB/rate-aggregate.json" > "$LAB/rate-invalid.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/securityrate" < "$LAB/rate-invalid.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/securityrate/all" > "$LAB/aggregate-after-invalid.json"
jq . "$LAB/aggregate-after-invalid.json"
docker exec uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X DELETE -w '\nHTTP:%{http_code}\n' "$API/config/securityrate"
```

Expected aggregate-only POST 200 with source flags false; all-off POST 400 and original aggregate
values retained. This configuration check alone does not qualify aggregate packet blocking. For
packet-count/whitelist/byte-window tests use the separate [advanced scope](advanced.md), keeping the
same complete replacement and both source controls independent.

### Verify a small distributed UDP aggregate and whitelist arm

This bounded packet test turns source guards off and sets a shared UDP2-packet budget. Two sources
send10 datagrams each; retain all20 sends and allow the aligned-window boundary to vary the exact
cardinality. Require a positive **aggregate** owning counter rather than inferring protection from
a source counter. The warm-up creates an observed series before the measured interval.

**Step 1 — Set a shared UDP budget and flood from A and C**

Wait for the relevant client and check its saved HTTP code. Fetch receipts directly from the backend namespace: accepted traffic and policy denials have different expected counts.

```bash
jq '.aggregateSynThreshold=0 | .aggregateUdpPktThreshold=2' "$LAB/rate-aggregate.json" > "$LAB/aggregate-packets.json"
docker exec -i uc7-gw curl -sS --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- "$API/config/securityrate" < "$LAB/aggregate-packets.json"
docker exec uc7-a bash -c 'for n in {1..10}; do printf edge > /dev/udp/192.0.2.10/8080; done' &
UDP_A=$!
docker exec uc7-c bash -c 'for n in {1..10}; do printf edge > /dev/udp/192.0.2.10/8080; done' &
UDP_C=$!
wait "$UDP_A" "$UDP_C"
sleep 12
docker exec uc7-gw curl -fsS --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/aggregate-before.prom"
sleep 2
docker exec uc7-a bash -c 'for n in {1..10}; do printf edge > /dev/udp/192.0.2.10/8080; done' &
UDP_A=$!
docker exec uc7-c bash -c 'for n in {1..10}; do printf edge > /dev/udp/192.0.2.10/8080; done' &
UDP_C=$!
wait "$UDP_A" "$UDP_C"
sleep 12
docker exec uc7-gw curl -fsS --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/aggregate-after.prom"
python3 "$INPUTS/metric-delta.py" "$LAB/aggregate-before.prom" "$LAB/aggregate-after.prom" loxilb_security_aggregate_udp_blocked_total
jq '.whitelistIps=["192.0.2.50/32"]' "$LAB/aggregate-packets.json" > "$LAB/aggregate-whitelist.json"
docker exec -i uc7-gw curl -sS --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- "$API/config/securityrate" < "$LAB/aggregate-whitelist.json"
docker exec uc7-c bash -c 'for n in {1..20}; do printf edge > /dev/udp/192.0.2.10/8080; done'
sleep 12
docker exec uc7-gw curl -fsS --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/whitelist-before.prom"
docker exec uc7-a bash -c 'for n in {1..20}; do printf edge > /dev/udp/192.0.2.10/8080; done'
```

**Step 2 — Check the whitelist bypass and final B/A delivery**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
sleep 12
docker exec uc7-gw curl -fsS --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/whitelist-after.prom"
grep '^loxilb_security_aggregate_udp_blocked_total ' "$LAB/whitelist-before.prom" > "$LAB/whitelist-before.counter"
grep '^loxilb_security_aggregate_udp_blocked_total ' "$LAB/whitelist-after.prom" > "$LAB/whitelist-after.counter"
test -s "$LAB/whitelist-before.counter"
test -s "$LAB/whitelist-after.counter"
cmp "$LAB/whitelist-before.counter" "$LAB/whitelist-after.counter"
docker exec uc7-c bash -c 'for n in {1..20}; do printf edge > /dev/udp/192.0.2.10/8080; done'
sleep 12
docker exec uc7-gw curl -fsS --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/whitelist-control.prom"
python3 "$INPUTS/metric-delta.py" "$LAB/whitelist-after.prom" "$LAB/whitelist-control.prom" loxilb_security_aggregate_udp_blocked_total
docker exec uc7-gw curl -sS --config /etc/loxilb/control.curl -X DELETE "$API/config/securityrate"
docker exec -i uc7-b curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-source-final-b" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/source-final-b.txt" 2> "$LAB/source-final-b.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/source-final-b.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-source-final-b" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-source-final-a" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/source-final-a.txt" 2> "$LAB/source-final-a.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/source-final-a.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-source-final-a" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Require aggregate delta>0 for the two-source arm, no aggregate blocked increase for whitelisted A,
then positive blocked delta for nonwhitelisted C. This is not exact-cardinality, bandwidth, distributed
attack saturation or wire-loss qualification; those remain [advanced](advanced.md). DELETE clears the
rate-managed whitelist, which shares maps with IP filtering. Confirm B/A normal TCP delivery again.

### Cleanup and troubleshooting

Require blacklist absence, all rate guards disabled/zero and B/A normal delivery before moving on.
If B still times out, inspect remaining ACL/FW layers and routes rather than calling DELETE ineffective.
Capture readback, owning counter and normal control at each arm. Do not reset shared counters to make
an unexplained delta disappear. Continue to [network boundary](network-boundary.md).

## Check your result

Compare the intended source drop and counter change with an allowed control request and backend journal.

Keep a normal control request alongside each denied or interrupted request. Separate packet drop, TCP refusal, HTTP denial, backend receipt, and counter changes. Readback establishes stored policy; client traffic and the backend journal establish delivery.

## Next steps and cleanup

Remove the isolated control before adding the next layer. Recovery restores the complete owned tuple; final cleanup uses the recorded ownership state and must preserve unrelated containers. Read the [lab starting point](setup.md) if required values are missing. Use [cleanup and recovery](cleanup.md) when ending the run.
