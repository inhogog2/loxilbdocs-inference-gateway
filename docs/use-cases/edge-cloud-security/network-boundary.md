# Fence a shared service and verify peer deletion

Distinguish an explicit TC drop from the source policy shared by models on one listener.

<!-- example-status-default: illustrative-only -->

!!! note "Continue in the same lab"
    Use the same root Bash session from [setup](setup.md). Follow the
    [common evidence and rollback conventions](common.md) throughout the exercises.

## Before you start

Remove prior source controls before isolating this layer.

**Focus of this page:** Change service-scoped source fences and the operator TC firewall at the shared VIP.

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

### Prerequisites and TC baseline

Remove source controls first. The plain baseline lets D reach the backend before the operator drop.
Firewall `protocol:6` means TCP; zero ports mean wildcard, so specify both ends of this destination
port range. `preference` participates in the rule identity and precedence;65010 precedes the generated
shared-listener allow65000. Do not use duplicate POST as an update.

**Step 1 — Send a baseline from D, then add a firewall drop**

Send a baseline request from source D and save its backend receipt. Then write `firewall-drop.json`, apply it to drop D (192.0.2.53) on port 8080, and read back the firewall rules. Change the source address to match your lab before running.

```bash
docker exec -i uc7-d curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-fw-before" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/fw-before.txt" 2> "$LAB/fw-before.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/fw-before.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-fw-before" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
cat > "$LAB/firewall-drop.json" <<'JSON'
{
  "ruleArguments": {
    "sourceIP": "192.0.2.53/32",
    "destinationIP": "192.0.2.10/32",
    "minDestinationPort": 8080,
    "maxDestinationPort": 8080,
    "protocol": 6,
    "preference": 65010
  },
  "opts": {
    "drop": true
  }
}
JSON
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/firewall" < "$LAB/firewall-drop.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/firewall/all" > "$LAB/firewall-readback.json"
jq . "$LAB/firewall-readback.json"
docker exec -i uc7-d curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-fw-warmup" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/fw-warmup.txt" 2> "$LAB/fw-warmup.err"
```

**Step 2 — Verify the D drop and A delivery, then delete the rule**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/fw-warmup.txt"
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/fw-before.prom"
docker exec -i uc7-d curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-fw-denied" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/fw-denied.txt" 2> "$LAB/fw-denied.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/fw-denied.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-fw-denied" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-fw-normal" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/fw-normal.txt" 2> "$LAB/fw-normal.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/fw-normal.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-fw-normal" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
sleep 12
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/metrics" > "$LAB/fw-after.prom"
python3 "$INPUTS/metric-delta.py" "$LAB/fw-before.prom" "$LAB/fw-after.prom" loxilb_fw_rule_drop_packets_total
docker exec uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X DELETE -w '\nHTTP:%{http_code}\n' "$API/config/firewall?sourceIP=192.0.2.53/32&destinationIP=192.0.2.10/32&minDestinationPort=8080&maxDestinationPort=8080&protocol=6&preference=65010"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/firewall/all" > "$LAB/firewall-removed.json"
jq . "$LAB/firewall-removed.json"
docker exec -i uc7-d curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-fw-recovered" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/fw-recovered.txt" 2> "$LAB/fw-recovered.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/fw-recovered.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
```

**Step 3 — Confirm D's recovered request reached the backend**

Read only the fields used by this experiment. Check the exact condition instead of inferring success from a printed JSON document; do not POST a readback envelope as a configuration request.

```bash
jq -s --arg nonce "$RUN-fw-recovered" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Expected: POST/GET 200, D timeout/curl 28/receipt 0 with drop delta>0 while A: 200/receipt 1, exact tuple
removed, then D: 200/receipt 1. A synthetic fence is not an ordinary public firewall list row.

### Configure two models on one source-fenced listener

Source policy belongs to normalized VIP/port/protocol, not to an HTTP model name. Allow A/C/D,
exclude B, and give both peer rules identical prefixes. Save the original writable plain rule.

**Step 1 — Save a copy of the plain model rule**

Run these commands in order and stop if a check fails. Keep the original inputs and results available for diagnosis before making the next change.

```bash
cp "$LAB/model.json" "$LAB/plain-model.json"
```

**Step 2 — Prepare `lb-allowed-sources.json`**

Write the complete input before sending it. This step creates a local file; it does not apply policy. Change the displayed values here, then use this same file in the following request.

```bash
cat > "$LAB/lb-allowed-sources.json" <<'JSON'
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
    "api_key_auth": "required"
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

**Step 3 — Apply the fenced rules and probe sources A and B**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
cp "$LAB/lb-allowed-sources.json" "$LAB/model.json"
jq '.serviceArguments.model_name="edge-alias"' "$LAB/model.json" > "$LAB/alias.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/loadbalancer" < "$LAB/model.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/loadbalancer" < "$LAB/alias.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/loadbalancer/all" > "$LAB/acl-before-invalid.json"
jq '.allowedSources=[{prefix:"192.0.2.51/32"}]' "$LAB/model.json" > "$LAB/acl-invalid.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/loadbalancer" < "$LAB/acl-invalid.json"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/loadbalancer/all" > "$LAB/acl-after-invalid.json"
jq '.lbAttr[] | {model:.serviceArguments.model_name,allowedSources,endpoints}' "$LAB/acl-after-invalid.json"
jq -S '.lbAttr | map({model:.serviceArguments.model_name,endpoints,allowedSources}) | sort_by(.model)' "$LAB/acl-before-invalid.json" > "$LAB/acl-before.canonical.json"
jq -S '.lbAttr | map({model:.serviceArguments.model_name,endpoints,allowedSources}) | sort_by(.model)' "$LAB/acl-after-invalid.json" > "$LAB/acl-after.canonical.json"
cmp "$LAB/acl-before.canonical.json" "$LAB/acl-after.canonical.json"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-acl-allowed" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/acl-allowed.txt" 2> "$LAB/acl-allowed.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/acl-allowed.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-acl-allowed" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-b curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-acl-denied" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/acl-denied.txt" 2> "$LAB/acl-denied.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/acl-denied.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-acl-denied" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Expected: matching peers accepted, mismatch400. Material endpoint/model/source configuration remains
unchanged; inspect both saved GETs (ignore live counters/effective timestamps). A: 200/receipt 1,
B timeout/receipt 0. The public firewall list hides generated fence rules; absence there does not
prove a fence is uninstalled. Use saved LB ACL, TC metrics and actual source probes together.

### Verify peer deletion, restore and cleanup

```bash
docker exec uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X DELETE -w '\nHTTP:%{http_code}\n' "$API/config/loadbalancer/hosturl/192.0.2.10/externalipaddress/192.0.2.10/port/8080/protocol/tcp?model_name=edge-alias"
docker exec uc7-gw curl -fsS --max-time 20 --config /etc/loxilb/control.curl "$API/config/loadbalancer/all" > "$LAB/acl-survivor.json"
jq '.lbAttr[] | {model:.serviceArguments.model_name,allowedSources}' "$LAB/acl-survivor.json"
docker exec -i uc7-b curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-peer-survivor-denied" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/peer-survivor-denied.txt" 2> "$LAB/peer-survivor-denied.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/peer-survivor-denied.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-peer-survivor-denied" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
docker exec -i uc7-a curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-peer-survivor-allowed" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/peer-survivor-allowed.txt" 2> "$LAB/peer-survivor-allowed.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/peer-survivor-allowed.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-peer-survivor-allowed" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
cp "$LAB/plain-model.json" "$LAB/model.json"
docker exec -i uc7-gw curl -sS --max-time 20 --config /etc/loxilb/control.curl -X POST -H 'Content-Type: application/json' --data-binary @- -w '\nHTTP:%{http_code}\n' "$API/config/loadbalancer" < "$LAB/model.json"
docker exec -i uc7-b curl -sS --http1.1 --connect-timeout 2 --max-time 6 --config /run/edge-key.curl -H 'Content-Type: application/json' -H "X-Edge-Nonce: $RUN-acl-recovered" --data-binary @- -w '\nHTTP:%{http_code} VERSION:%{http_version}\n' "http://$VIP:8080/v1/completions" < "$LAB/request.json" > "$LAB/acl-recovered.txt" 2> "$LAB/acl-recovered.err"
printf 'CURL_EXIT=%s\n' "$?"
cat "$LAB/acl-recovered.txt"
docker logs uc7-ep > "$LAB/journal.jsonl" 2>&1
jq -s --arg nonce "$RUN-acl-recovered" '[.[] | select(.event=="uc7_receipt" and .nonce==$nonce)] | {count:length,credentials_absent:all(.key_present==false),protocols:map(.proto)}' "$LAB/journal.jsonl"
```

Require only the primary remains with A/C/D prefixes, B still denied and A delivered. Restoring the
single survivor's plain payload lifts the source fence; B must then deliver. Keep this plain state
for [connection protection](connections.md). If a POST is409/no-op inspect actual saved fields;
do not infer failure or replace an entire listener merely to force a success response.

### Troubleshooting

A new model name on the same listener does not grant a different network boundary. An earlier
operator drop can continue denying a source allowed by allowedSources. Check CIDR normalization,
priority, full deletion tuple and other installed layers before diagnosing a policy error.

## Check your result

An ACL refusal must preserve unrelated model/service traffic and have no backend delivery.

Keep a normal control request alongside each denied or interrupted request. Separate packet drop, TCP refusal, HTTP denial, backend receipt, and counter changes. Readback establishes stored policy; client traffic and the backend journal establish delivery.

## Next steps and cleanup

Remove the isolated control before adding the next layer. Recovery restores the complete owned tuple; final cleanup uses the recorded ownership state and must preserve unrelated containers. Read the [lab starting point](setup.md) if required values are missing. Use [cleanup and recovery](cleanup.md) when ending the run.
