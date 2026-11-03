# Forward identity and survive policy dependency faults

Distinguish verified identity forwarding, cached-key validation and confirmed policy state during bounded dependency faults.

<!-- example-status-default: illustrative-only -->

!!! note "Lab sequence and validation scope"
    Start with [lab preparation](setup.md) and [common API conventions](common.md).
    These commands belong to a multi-page lab, not standalone mutations.
    The [Quickstart](../../getting-started/quickstart.md) provides the canonical mutation lifecycle.
    Read the [evidence limits](index.md#verification-and-evidence-limits) before recording a result.

## Before you start

Use only the lab-owned dependency containers and retain their healthy baseline.

**Focus of this page:** Interrupt one policy or identity dependency while keeping a normal control path.

## Topology and execution locations

--8<-- "snippets/use-cases/topology/admission.md"

These are Linux containers/namespaces on one disposable host. The model names identify synthetic echoes, not loaded GPU models. The baseline listener is VIP 192.0.2.254:2040; TLS, capacity and failure exercises add the explicit listener ports shown in their steps. Keycloak/JWKS and PostgreSQL use inspected Docker-bridge addresses.

| Where | What happens here |
|---|---|
| Host operator | Prepare private LAB files, issue credentials and run namespace commands. |
| l3h1 | Send management calls and client traffic into llb1. |
| llb1 | Enforce identity, quota and capacity before choosing a backend. |
| l3ep1 / l3ep2 | Observe independent Llama/Mistral receipt and hold/release fixtures. |
| kc-aigw / pg-jwtauth | Supply identity and policy state; they are not on the inference response path. |

## Walkthrough

### Prerequisites and identity verification

Run only on the disposable lab; leave the bootstrap profiles intact. kc/2040 strips Authorization and client X-Auth fields, kc-fwd/2045 injects verified tenant/user without bearer passthrough, kc-pass/2046 explicitly forwards Authorization. Profile forward_identity and authorization_passthrough are independent booleans, false by default. Send forged X-Auth-Tenant/User with a valid JWT: the backend must see tenant-a and Alice sub, never the forged values. Compare with 2040 and 2046.

Chunked H1 skips identity injection in this contract; a Content-Length test is not chunked/H2 parity. Raw Authorization capture is limited to 4095 bytes (4088 for the JWT after Bearer plus space). Do not print backend echoes containing bearer material into public evidence.

```bash
sudo ip netns exec l3h1 curl -sS -i --config "$LAB/alice.curl" \
  -H 'Content-Type: application/json' -H 'X-Auth-Tenant: forged-tenant' \
  -H 'X-Auth-User: forged-user' -H "X-Test-Nonce: $RUN-identity" \
  --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2045/v1/chat/completions"
```

### Verify cached JWKS versus never-fetched keys

First warm 2047 with a valid Alice request and confirm receipt1. Keep the existing token unexpired, then pause the lab Keycloak. New token issuance times out; cached verification on 2047 continues while keyset freshness and token validity permit. The never-fetched blackhole profile on 2044 must return 503 `policy_store_unavailable` with receipt0. The outage profile refresh is ten seconds; the default maximum key staleness is 24 hours, not indefinite fail-open. Always unpause Keycloak and verify new issuance plus normal requests afterwards.

```bash
sudo ip netns exec l3h1 curl -sS -i --max-time 15 --config "$LAB/alice.curl" \
  -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-idp-warm" \
  --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2047/v1/chat/completions"
docker pause kc-aigw
curl -sS --max-time 3 -X POST "$TOKEN_URL" \
  --data-urlencode 'client_id=aigw-client' --data-urlencode 'grant_type=password' \
  --data-urlencode 'username=alice' --data-urlencode 'password=alicepw' -o "$LAB/paused-token.json"
sudo ip netns exec l3h1 curl -sS -i --config "$LAB/alice.curl" \
  -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-idp-cached" \
  --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2047/v1/chat/completions"
sudo ip netns exec l3h1 curl -sS -i --config "$LAB/alice.curl" \
  -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-idp-never" \
  --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2044/v1/chat/completions"
docker unpause kc-aigw
```

### Configure confirmed policy states, inject and recover a store fault

The commands source the private bootstrap .state locally for PG owner/database/role values; never print it. Warm f1/f2 on 2063. Set f1 RPS1; create then DELETE f2 so the store has confirmed absence. Do not pre-query 2066: GET/traffic can warm the supposedly unread rung.

Revoke only data-plane role aigwuser's schema USAGE; keep administrator access. The diagnostic SQL must immediately report permission denied; a timeout is not valid fault-injection evidence. While revoked, send f1 twice quickly (200 then429), f2 (200 known-absent), unread 2066 (503/receipt0), and credential-free 2064 (200 for its opt-in keyless behavior). The commands place these requests **between REVOKE and GRANT**, while each condition holds. Do not perform them after recovery.

GRANT is the first recovery action even if a probe fails. After GRANT require 2066 200/receipt1 and unchanged Gateway StartedAt. Do not substitute DB pause: an open query can hang instead of returning an error. Finally delete the f1 row, GET both rows404 and confirm kc/pg running, unpaused.

```bash
source .state
export F1_SUB=$(jq -r .sub "$LAB/f1.claims.json")
export F2_SUB=$(jq -r .sub "$LAB/f2.claims.json")
jq -n --arg u "$F1_SUB" '{tenant_id:"tenant-qf",user_id:$u,rps:1,burst_size:1}' > "$LAB/f1-rps.json"
sudo ip netns exec l3h1 curl -sS -i -X POST "$API/config/ai/user/ratelimit" \
  -H 'Content-Type: application/json' --data-binary @"$LAB/f1-rps.json"
sudo ip netns exec l3h1 curl -sS -i "$API/config/ai/user/ratelimit/$(jq -r .tenant_id "$LAB/f1-rps.json")/$(jq -r .user_id "$LAB/f1-rps.json")"
```

```bash
sudo ip netns exec l3h1 curl -sS -i --config "$LAB/f1.curl" -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-store-warm-f1" --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2063/v1/chat/completions"
sudo ip netns exec l3h1 curl -sS -i --config "$LAB/f2.curl" -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-store-warm-f2" --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2063/v1/chat/completions"
jq -n --arg u "$F2_SUB" '{tenant_id:"tenant-qf",user_id:$u,rps:1}' > "$LAB/f2-rps.json"
sudo ip netns exec l3h1 curl -sS -i -X POST "$API/config/ai/user/ratelimit" -H 'Content-Type: application/json' --data-binary @"$LAB/f2-rps.json"
sudo ip netns exec l3h1 curl -sS -i "$API/config/ai/user/ratelimit/$(jq -r .tenant_id "$LAB/f2-rps.json")/$(jq -r .user_id "$LAB/f2-rps.json")"
sudo ip netns exec l3h1 curl -sS -i -X DELETE "$API/config/ai/user/ratelimit/tenant-qf/$F2_SUB"
```

**Step 1 — Revoke store access and probe each rung during the fault**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
sleep 2
export GW_START_BEFORE=$(docker inspect -f '{{.State.StartedAt}}' llb1)
docker exec "$PG_NAME" psql -U "$PG_OWNER" -d "$PG_DB" -Atc \
  'REVOKE USAGE ON SCHEMA aigw FROM aigwuser'
timeout 5 docker exec -e PGPASSWORD="$PG_DP_PW" "$PG_NAME" \
  psql -U aigwuser -h 127.0.0.1 -d "$PG_DB" -Atc \
  'SELECT count(*) FROM aigw.rate_limit_defaults'
sudo ip netns exec l3h1 curl -sS -i --max-time 15 --config "$LAB/alice.curl" \
  -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-store-unread" \
  --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2066/v1/chat/completions"
sudo ip netns exec l3h1 curl -sS -i --max-time 15 --config "$LAB/f1.curl" \
  -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-store-f1-1" \
  --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2063/v1/chat/completions"
sudo ip netns exec l3h1 curl -sS -i --max-time 15 --config "$LAB/f1.curl" \
  -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-store-f1-2" \
  --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2063/v1/chat/completions"
sudo ip netns exec l3h1 curl -sS -i --max-time 15 --config "$LAB/f2.curl" \
  -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-store-f2" \
  --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2063/v1/chat/completions"
sudo ip netns exec l3h1 curl -sS -i --max-time 15 \
  -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-store-keyless" \
  --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2064/v1/chat/completions"
docker exec "$PG_NAME" psql -U "$PG_OWNER" -d "$PG_DB" -Atc \
  'GRANT USAGE ON SCHEMA aigw TO aigwuser'
```

**Step 2 — Confirm 2066 recovery after GRANT and delete the f1 row**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
sudo ip netns exec l3h1 curl -sS -i --config "$LAB/alice.curl" \
  -H 'Content-Type: application/json' -H "X-Test-Nonce: $RUN-store-recovery" \
  --data-binary @"$LAB/examples/llama-request.json" "http://$VIP:2066/v1/chat/completions"
printf 'before=%s after=%s\n' "$GW_START_BEFORE" "$(docker inspect -f '{{.State.StartedAt}}' llb1)"
sudo ip netns exec l3h1 curl -sS -i -X DELETE "$API/config/ai/user/ratelimit/tenant-qf/$F1_SUB"
```

```bash
sudo ip netns exec l3h1 curl -sS "$API/config/ai/jwtauthprofile" | jq '[.jwtAuthProfileAttr[] | select(.name=="kc-fwd" or .name=="kc-pass")]'
sudo ip netns exec l3h1 curl -sS "$API/config/loadbalancer/all" | jq '[.lbAttr[] | select(.serviceArguments.port==2045 or .serviceArguments.port==2046)]'
sudo ip netns exec l3h1 curl -sS -i "$API/config/ai/user/ratelimit/tenant-qf/$F1_SUB"
sudo ip netns exec l3h1 curl -sS -i "$API/config/ai/user/ratelimit/tenant-qf/$F2_SUB"
docker inspect -f '{{.Name}} paused={{.State.Paused}} running={{.State.Running}}' kc-aigw pg-jwtauth
```


### Troubleshooting and cleanup

Use [diagnosis and scoped cleanup](cleanup.md). Restore this chapter's changes before moving to another policy experiment.

## Check your result

Separate cached/applied decisions, fresh dependency access and recovery; never leave a dependency paused.

Compare API readback with the normal request, the deliberate denial, and an independent backend observation. Check the chapter's exact HTTP code and error body; HTTP 200 alone does not prove quota, identity, queue order, or resource return.

## Next steps and cleanup

Restore the chapter's temporary policy before continuing in the same lab. Keep the original configuration and private evidence; use the final cleanup chapter when the entire lab is finished. Read the [lab starting point](setup.md) if required values are missing. Use [cleanup and recovery](cleanup.md) when ending the run.
