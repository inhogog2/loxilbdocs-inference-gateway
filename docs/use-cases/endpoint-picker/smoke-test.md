# Smoke test: one request, four observation points

Send one request and read it at the client, in the gateway's metric and log, and in the EPP's log. The two addresses must match, and the pod's own counter confirms it independently.

<!-- example-status-default: illustrative-only -->

## Before you start

A rule with `eppEndpoint` exists on the VIP ([Create the EPP Rule](rule.md)). The variables below are the same for both rule paths.

**Focus of this page:** This is the check the [measurements](measurements.md) repeat over 200 requests.

## Topology and execution locations

--8<-- "snippets/use-cases/topology/endpoint-picker.md"

| Where | What happens here |
|---|---|
| Operator shell (the control-plane node in this guide) | `kubectl`, `curl` against the gateway's REST API on `:11111`, the harness, pod `:8000/metrics` reads |
| Client | sends OpenAI-style requests to the gateway VIP, `192.0.2.10:8080` |
| loxilb-igw (DaemonSet, hostNetwork on the control-plane node) | holds the rule, asks the EPP per request, forwards to the pod it names |
| Endpoint Picker (Deployment + ClusterIP Service) | watches the `InferencePool`, keeps the prefix-cache index, answers over ext_proc gRPC `:9002` |
| vLLM pods (one per GPU node) | serve the model on `:8000`; their metrics are the independent attribution of which pod served a request |

## Walkthrough

Raise the EPP's log level to 4 so it records each decision. The container and argument index are found rather than assumed, since chart versions order them differently:

```bash
NS=llm-d-pd-disaggregation; VIP=192.0.2.10; PORT=8080; LB=http://$VIP:11111/netlox/v1
P=$(kubectl -n $NS get deploy pd-disaggregation-epp -o json | python3 -c '
import json,sys
for i,c in enumerate(json.load(sys.stdin)["spec"]["template"]["spec"]["containers"]):
    for j,a in enumerate(c.get("args",[])):
        if a.startswith("--v="): print(f"/spec/template/spec/containers/{i}/args/{j}")')
kubectl -n $NS patch deploy pd-disaggregation-epp --type=json -p "[{\"op\":\"replace\",\"path\":\"$P\",\"value\":\"--v=4\"}]"
kubectl -n $NS rollout status deploy/pd-disaggregation-epp
```

Send one request with a request id you can grep for, and read the four points:

```bash
M(){ curl -s $LB/metrics | awk '/^loxilb_ai_epp_requests_total/{s+=$NF} END{print s+0}'; }
before=$(M); START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://$VIP:$PORT/v1/completions \
  -H 'Content-Type: application/json' -H 'x-request-id: smoke-0001' \
  -d '{"model":"Qwen/Qwen3-32B-FP8","prompt":"name one color.","max_tokens":4}'
echo "metric: $before -> $(M)"
kubectl -n kube-system logs ds/loxilb-lb --since-time=$START | grep '\[EPP\] fd='
kubectl -n $NS logs deploy/pd-disaggregation-epp -c epp --since-time=$START | grep 'smoke-0001' | grep 'Request handled'
```

```
200
metric: 346 -> 347
03:08:20 INFO  sockproxy_ep.c:855: [EPP] fd=756 sid=347 -> 198.51.100.11:8000 (ep2, candidate 1 of 1)
{"timestamp":"2026-10-15T03:08:20.447Z","caller":"requestcontrol/director.go:508","body":"Request handled","x-request-id":"smoke-0001","endpoint":"198.51.100.11:8000"}
```

| Point | Where it comes from | What it tells you |
|---|---|---|
| HTTP status | the client | the request completed |
| `loxilb_ai_epp_requests_total` | the gateway's REST `/metrics`, incremented once per request submitted to the EPP | the rule consulted the EPP |
| `[EPP] fd=… sid=… -> ip:port (epN, candidate k of n)` | the gateway's log, written when it connects to the pod the EPP named. `sid` is the proxy's session number, `epN` the pod's index in the rule, `candidate k of n` which of the EPP's candidates was taken | the gateway forwarded where the EPP said |
| `Request handled` with `x-request-id` and `endpoint` | the EPP's log at `--v=4` | what the EPP decided |

The two addresses must match. The pod side confirms it independently: `vllm:request_success_total` on `http://198.51.100.11:8000/metrics` rose by one. With this in place, the measurement post's Step 1 is the same check over 200 requests.

## Check your result

HTTP 200; `loxilb_ai_epp_requests_total` rose by one; the gateway's `[EPP] ... -> ip:port` line and the EPP's `Request handled` line name the same pod; that pod's `vllm:request_success_total` rose by one.

## Next steps and cleanup

Continue with [Switching Routing Modes](modes.md), or go straight to the [Reproduction Harness](harness.md). Put the EPP back to `--v=2` with the patch in [Teardown](troubleshooting.md#teardown) when you are done reading its per-request lines.
