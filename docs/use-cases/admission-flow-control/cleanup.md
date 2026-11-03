# Restore the lab and interpret failures

Remove only resources created by these exercises and preserve the bootstrap topology, credentials and original evidence.

<!-- example-status-default: illustrative-only -->

!!! note "Lab sequence and validation scope"
    Start with [lab preparation](setup.md) and [common API conventions](common.md).
    These commands belong to a multi-page lab, not standalone mutations.
    The [Quickstart](../../getting-started/quickstart.md) provides the canonical mutation lifecycle.
    Read the [evidence limits](index.md#verification-and-evidence-limits) before recording a result.

## Before you start

Save original scope requests and stop sending new load.

**Focus of this page:** Restore policy scopes and delete exact listener/profile/certificate keys before lifecycle teardown.

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

### Prerequisites and scoped cleanup

Record the full keys actually created and distinguish them from existing rules. First restore policy-store GRANT, unpause Keycloak, set maintenance enabled=false, release holders and restore quotas/defaults using the earlier chapters. Save the final results before stopping any lab fixture.

The explicit deletion list below is a **menu**: run only lines for keys that this lab actually created, after checking their saved inputs. Never assume deleting2210 deletes2211 or another model on the same port. The full key includes host, externalIP, port, protocol, path_prefix/path_match_mode and model_name. No bootstrap ports2040–2070 are deleted. Port2244/kc-manual is handled separately in the identity chapter. GET the exact key after every delete; the final lab filter should be[].

Certificate deletion occurs after removing referencing rules. Expect referenced DELETE400 with GET200, then unreferenced DELETE204/GET404. Stop foreground fixtures via their own Ctrl-C; for a detached process compare recorded PID, start time and exact command before termination. Keep shared echo/Keycloak/PostgreSQL/network and the Gateway server certificate. The last rm removes only the two copied lab frontend-CA files, after all references and fixtures are gone.

```bash
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2210/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS "$API/config/loadbalancer/all" | \
  jq '[.lbAttr[] | select(.serviceArguments.port>=2210 and .serviceArguments.port<=2243)]'
```

**Step 1 — Delete the lab rules on ports 2211–2231**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2211/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2212/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2213/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2214/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2215/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2216/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2217/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2218/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2219/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2220/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2221/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2231/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
```

**Step 2 — Delete ports 2232–2243 and confirm no lab rules remain**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2232/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2233/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2234/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2235/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2236/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2240/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2241/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2242/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS -i -X DELETE \
  "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/2243/protocol/tcp?path_prefix=/&path_match_mode=prefix&model_name=llama-70b"
sudo ip netns exec l3h1 curl -sS "$API/config/loadbalancer/all" | jq '[.lbAttr[] | select(.serviceArguments.port>=2210 and .serviceArguments.port<=2244)]'
```

```bash
sudo ip netns exec l3h1 curl -sS -i -X DELETE "$API/config/cert/manual-backend-client"
sudo ip netns exec l3h1 curl -sS -i "$API/config/cert/manual-backend-client"
sudo ip netns exec l3h1 curl -sS -i -X DELETE "$API/config/cert/manual-backend-ca"
sudo ip netns exec l3h1 curl -sS -i -X DELETE "$API/config/cert/manual-other-ca"
sudo ip netns exec l3h1 curl -sS -i -X DELETE "$API/config/cert/manual-wrong-client"
sudo ip netns exec l3h1 curl -sS -i "$API/config/cert/manual-backend-ca"
sudo ip netns exec l3h1 curl -sS -i "$API/config/cert/manual-other-ca"
sudo ip netns exec l3h1 curl -sS -i "$API/config/cert/manual-wrong-client"
```

```bash
sudo docker exec llb1 rm -f /opt/loxilb/cert/manual-client-ca.crt /opt/loxilb/cert/manual-other-client-ca.crt
```

### Verify expected final state

GET no lab listeners or kc-manual profile; user policies404, tenant aggregate0 and each lab model limit cleared; defaults absent or exactly restored; maintenance active; Keycloak/PostgreSQL running and unpaused. Reissue Alice's token and repeat baseline200 with Llama receipt1/Mistral0. Keep original result files and token/key material in the private LAB directory, outside the public documentation tree.

### Tear down a dedicated disposable host lab

Chapter cleanup above preserves the bootstrap for the next exercise. When the entire campaign is finished, first save the results privately and stop every added foreground fixture. Confirm that all six bootstrap containers and four namespace names were absent before this campaign and belong to this disposable clone. Review the selected upstream rmconfig.sh and any helper PID file before executing it from the same scenario directory. Some bootstrap revisions do not write that file: its absence does not mean that namespace helpers have stopped. Record the exact hdr_echo.py/h2c_echo.py/rawsink.py processes under this disposable scenario path and stop each by its verified PID and start time before teardown. Do not use this teardown on an existing deployment.

```bash
test ! -f .loxi-helpers.pid || cat .loxi-helpers.pid
cat rmconfig.sh
bash rmconfig.sh
docker ps -a --format '{{.Names}}'
sudo ip netns list
```

For each helper, compare the saved command and process start time immediately before sending TERM; do not use a process-name-wide kill. A failed bootstrap can leave an anonymous PostgreSQL volume too. Prove ownership using the recorded container mount or Docker create/mount events before removing that exact volume.

The owned llb1/l3h1/l3ep1/l3ep2/kc-aigw/pg-jwtauth containers and llb1/l3h1/l3ep1/l3ep2 namespaces must be absent. Check recorded fixture PID/start time and listeners too: namespaces share the host PID namespace. Compare volumes, images, host interfaces and installed dependencies with the pre-lab inventory. Remove only new objects whose ownership was recorded for this campaign. Do not run Docker prune, remove pre-existing images/volumes, or change the host's existing network interfaces. Retain the private evidence before removing disposable working files.

### Troubleshooting

| Symptom | Next check |
|---|---|
| JWT profile API404 | Running image/version and capability, not local HEAD |
| All JWT requests503 | Gateway→JWKS reachability and key cache, then policy-store error |
| 401 | exp plus leeway, issuer/audiences, tenant/sub claims |
| 403 | Exact body model vs allowed model role, positive allowed-model control |
| Unexpected429 | Typed error, explicit/default rows, quota and admission state |
| Second RPS request200 | Pair elapsed time, bucket refill, burst and exact subject |
| GET applied but TLS fails | Served cert fingerprint/SAN, CA and peer handshake |
| mTLS only fails after update | New listener takeover event and client credential policy |
| Queue stuck | Effective wait, holder receipt/release, queued/inflight and cancellation |
| Recovery probe still fails | Maintenance false, GRANT restored, fresh token, exact original policy |

Do not convert a timeout, missing receipt file, failed scrape, skipped or unexecuted case into PASS. A grep receipt count0 has exit1; separately ensure the file exists and the server is ready.

### Result record

For each case record UTC time, selected source/submodule/image/binary identities, OS, original and changed request JSON, management status and exact GET/effective values, client HTTP version/status/exit, nonce and independent receipt count, peer fingerprint, metric deltas/epoch/elapsed time, relevant redacted error, and deletion/recovery readback plus actual normal traffic. Keep runtime, static, failed, skipped and inconclusive results distinct.


### Troubleshooting and cleanup

Use [diagnosis and scoped cleanup](cleanup.md). Restore this chapter's changes before moving to another policy experiment.

## Check your result

Prove ordinary departmental traffic and independent receipts before removing the disposable bootstrap.

Compare API readback with the normal request, the deliberate denial, and an independent backend observation. Check the chapter's exact HTTP code and error body; HTTP 200 alone does not prove quota, identity, queue order, or resource return.

## Next steps and cleanup

Choose explicitly whether to retain the healthy bootstrap for another chapter or tear down the entire disposable lab. Do not bootstrap over the retained containers. After full teardown, keep the private scope backups and observations, and use a new owned run for another complete replay.
