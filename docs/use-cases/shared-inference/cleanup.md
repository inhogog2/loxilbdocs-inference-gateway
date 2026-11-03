# Remove the lab with explicit commands

Verify both departments still work, then remove the rule and keys before stopping the exact processes and namespaces created during setup. Keep LAB for private evidence and recovery inputs.

<!-- example-status-default: illustrative-only -->

## Before you start

Finish recovery with a healthy store and both departmental keys.

**Focus of this page:** Delete owned configuration before stopping exact PIDs, containers and namespaces.

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

### Finish traffic and remove configuration

The final service still owns five API keys, two tenants and two objectives. First prove inflight0/queued0 and successful traffic for both departments. A public GET response is not a rollback payload; the original request files under LAB remain your editable inputs.

**Step 1 — Wait for an idle queue and read network identities**

Send the displayed management request to `/config/loadbalancer/all` and retain its response. Inspect the displayed effective inflight/queue condition; a successful configuration response alone does not prove this state. Send the displayed management request to `/config/ai/netidentity` and retain its response.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
reached=false
for attempt in $(seq 1 80); do
  ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
    -o "$LAB/cleanup-state-1.json"
  if jq -e --argjson port "$PORT" \
    '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective |
     .inflight == 0 and .queued == 0' "$LAB/cleanup-state-1.json" >/dev/null; then
    reached=true
    break
  fi
  sleep 0.1
done
test "$reached" = true
jq --argjson port "$PORT" \
  '.lbAttr[] | select(.serviceArguments.port == $port) | .serviceArguments.fc_effective' \
  "$LAB/cleanup-state-1.json"
status=$(ip netns exec share-a curl -sS --max-time 10 -X GET \
  -D "$LAB/cleanup-config-2.headers" -o "$LAB/cleanup-config-2.response.json" \
  -w '%{http_code}' "$API/config/ai/netidentity")
printf 'HTTP %s\n' "$status"
jq . "$LAB/cleanup-config-2.response.json"
```

**Step 2 — Send `final-support` and retain the response**

Require HTTP 200 for the saved management response before continuing. Write `final-support.request.json` with the displayed editable JSON input. Send `final-support` through the Gateway from the namespace shown below; retain its HTTP status and response separately. Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `final-support`.

```bash
test "$status" = 200
cat > "$LAB/final-support.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "final-support"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-a curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/support.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: final-support' -H 'X-Request-Id: final-support' \
  --data-binary "@$LAB/final-support.request.json" \
  -D "$LAB/final-support.headers" -o "$LAB/final-support.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/final-support.http"
if test -f "$LAB/final-support.pid"; then
  wait "$(cat "$LAB/final-support.pid")"
fi
test "$(cat "$LAB/final-support.http")" = 200
```

**Step 3 — Send `final-research` and retain the response**

Read `final-support` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `final-support`. Write `final-research.request.json` with the displayed editable JSON input. Send `final-research` through the Gateway from the namespace shown below; retain its HTTP status and response separately.

```bash
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/final-support" -o "$LAB/final-support.receipt.json"
jq -e '.count == 1' "$LAB/final-support.receipt.json"
cat > "$LAB/final-research.request.json" <<'JSON'
{
  "model": "shared-model",
  "messages": [
    {
      "role": "user",
      "content": "final-research"
    }
  ],
  "max_tokens": 4
}
JSON
ip netns exec share-b curl --http1.1 -sS --max-time 55 \
  --config "$LAB/keys/research.curl" \
  -H 'Content-Type: application/json' \
  -H 'X-Test-Nonce: final-research' -H 'X-Request-Id: final-research' \
  --data-binary "@$LAB/final-research.request.json" \
  -D "$LAB/final-research.headers" -o "$LAB/final-research.response.json" \
  -w '%{http_code}\n' "$INFER" > "$LAB/final-research.http"
```

**Step 4 — Confirm `final-research` HTTP 200 and backend receipt**

Wait for the saved client PID in this same parent Bash before checking its final response. Require saved HTTP 200 for `final-research`. Read `final-research` directly from the backend receipt endpoint; this observation bypasses the Gateway. Require backend receipt count 1 for `final-research`.

```bash
if test -f "$LAB/final-research.pid"; then
  wait "$(cat "$LAB/final-research.pid")"
fi
test "$(cat "$LAB/final-research.http")" = 200
ip netns exec share-backend curl -fsS --max-time 3 \
  "http://127.0.0.1:8080/receipt/final-research" -o "$LAB/final-research.receipt.json"
jq -e '.count == 1' "$LAB/final-research.receipt.json"
```

Delete the exact model/host/path service key and verify its absence. If you changed the VIP, port or model, change the same values here. Key deletion normally returns 204; verify GET404 using the returned key_id. There is no tenant DELETE endpoint in this walkthrough. Removing the dedicated DB container stops access to its remaining tenant/objective rows, but the database files remain under LAB/database for private retention. Apply your own retention policy to those files; never reset another deployment's tenants to imitate this cleanup.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
MODEL_ENCODED=$(printf '%s' "$MODEL" | jq -sRr @uri)
status=$(ip netns exec share-a curl -sS --max-time 10 -X DELETE \
  -o "$LAB/delete-rule.response.json" -w '%{http_code}' \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/$PORT/protocol/tcp?model_name=$MODEL_ENCODED&path_prefix=%2F&path_match_mode=prefix")
test "$status" = 200
ip netns exec share-a curl -fsS --max-time 5 "$API/config/loadbalancer/all" \
  -o "$LAB/rules-after-delete.json"
jq -e --argjson port "$PORT" \
  '[.lbAttr[]? | select(.serviceArguments.port == $port)] | length == 0' \
  "$LAB/rules-after-delete.json"
for identity in support support-batch research research-batch support-secondary; do
  key_id=$(jq -er .key_id "$LAB/keys/$identity.json")
  status=$(ip netns exec share-a curl -sS --max-time 10 -X DELETE \
    -o "$LAB/$identity-delete.response" -w '%{http_code}' "$API/config/ai/apikey/$key_id")
  test "$status" = 204
  status=$(ip netns exec share-a curl -sS --max-time 5 \
    -o "$LAB/$identity-after-delete.json" -w '%{http_code}' "$API/config/ai/apikey/$key_id")
  test "$status" = 404
done
```

### Stop only owned processes and remove their networks

Before stopping anything, compare each container's label to this LAB. Check the backend PID's start time before sending SIGTERM, then wait for that exact process to disappear. Do not substitute a global process-name kill or Docker prune.

**Step 1 — Verify ownership and stop the backend**

After matching the saved PID start time, stop only the owned backend process and wait for it to disappear.

```bash
set -euo pipefail
umask 077
source "${LAB:?set LAB to your private run directory}/env"
for name in share-gateway share-pg; do
  test "$(docker inspect -f '{{index .Config.Labels "shared-lab"}}' "$name")" = "$LAB"
done
backend_pid=$(cat "$LAB/backend.pid")
backend_start=$(cat "$LAB/backend.starttime")
if test -f "/proc/$backend_pid/stat"; then
  test "$(awk '{print $22}' "/proc/$backend_pid/stat")" = "$backend_start"
  kill -TERM "$backend_pid"
fi
helper_stopped=false
for attempt in $(seq 1 30); do
  if ! test -f "/proc/$backend_pid/stat"; then
    helper_stopped=true
    break
  fi
  if test "$(awk '{print $22}' "/proc/$backend_pid/stat")" != "$backend_start"; then
    helper_stopped=true
    break
  fi
  sleep 0.1
done
```

**Step 2 — Delete the owned containers and namespaces**

Remove the two previously ownership-checked containers and their anonymous volumes, then delete the four lab namespaces and prove their absence.

```bash
test "$helper_stopped" = true
docker rm -f -v share-gateway share-pg
ip netns del share-backend
ip netns del share-b
ip netns del share-a
ip netns del share-gateway
for name in share-gateway share-pg; do
  if docker inspect "$name" >/dev/null 2>&1; then
    printf 'Container remains: %s\n' "$name" >&2
    exit 1
  fi
done
for name in share-gateway share-a share-b share-backend; do
  if ip netns list | awk '{print $1}' | grep -Fxq "$name"; then
    printf 'Namespace remains: %s\n' "$name" >&2
    exit 1
  fi
done
jq -n '{containers_absent:["share-gateway","share-pg"],
        namespaces_absent:["share-gateway","share-a","share-b","share-backend"],
        helpers_absent:true,data_preserved:true}' > "$LAB/cleanup.json"
cat "$LAB/cleanup.json"
docker ps -a --format '{{.Names}} {{.Status}}'
ip netns list
```

Expected: the two containers and all four namespaces are absent, the backend helper has exited, and cleanup.json records the checks. Private keys, original request/response/receipt files, passwords and DB files remain under LAB; retain or delete them under your own data policy.

If you stopped during setup, first inventory which of these exact resources were created. Skip API deletion for objects that were never created, and run only the matching resource cleanup commands. If the DB is paused, unpause share-pg before inspecting it. If an ownership or PID check fails, preserve the evidence and resolve the mismatch; do not sweep names. A complete retry uses a new LAB and the full chapter sequence.

## Check your result

Prove inflight/queued zero, absence of owned resources and preservation of private LAB/database files.

Keep the configured policy, HTTP status, resolved identity, and independent backend receipt together. A rejected request must have receipt 0; a successful request must have receipt 1. A missing receipt response is a failed observation, never a zero.

## Next steps and cleanup

The run is finished only when the owned containers, namespaces and backend process are absent and the final record has been saved. Type `exit` to leave the dedicated lab shell and return to your original terminal. Keep LAB/database, private credentials and evidence under your own retention policy. If an ownership check fails, diagnose that exact resource before attempting another run.
