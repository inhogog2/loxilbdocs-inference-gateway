# Observability

Where each component writes what it did with a request: gateway log and metrics, EPP log and metrics, and the pods' own counters.

<!-- example-status-default: illustrative-only -->

## Before you start

Any of the three routing modes is active. EPP per-request lines need `--v=4` ([smoke test](smoke-test.md)).

**Focus of this page:** Pod metrics are the attribution of record; they do not depend on the routing mode under test.

## Topology and execution locations

--8<-- "snippets/use-cases/topology/endpoint-picker.md"

| Where | What happens here |
|---|---|
| Operator shell (the control-plane node in this guide) | `kubectl`, `curl` against the gateway's REST API on `:11111`, the harness, pod `:8000/metrics` reads |
| Client | sends OpenAI-style requests to the gateway VIP, `192.0.2.10:8080` |
| loxilb-igw (DaemonSet, hostNetwork on the control-plane node) | holds the rule, asks the EPP per request, forwards to the pod it names |
| Endpoint Picker (Deployment + ClusterIP Service) | watches the `InferencePool`, keeps the prefix-cache index, answers over ext_proc gRPC `:9002` |
| vLLM pods (one per GPU node) | serve the model on `:8000`; their metrics are the independent attribution of which pod served a request |

## Reading path and reference

| Source | Command | Lines and names |
|---|---|---|
| gateway log | `kubectl -n kube-system logs ds/loxilb-lb` | `[EPP] fd= sid= -> ip:port (epN, candidate k of n)` per forwarded request; `[EPP] … FailOpen` when the fallback selector was used |
| gateway metrics | `curl $LB/metrics` | `loxilb_ai_epp_requests_total`, `loxilb_ai_epp_duration_seconds` (histogram of the wait for the EPP), `loxilb_ai_epp_inflight`, `loxilb_ai_epp_pending` |
| EPP log | `kubectl -n $NS logs deploy/pd-disaggregation-epp -c epp` | at `--v=4`: `Request handled` (request id, endpoint); `Selecting endpoints from candidates sorted by max score` with `num-of-candidates` and the scored list; one `Calculated score` per plugin per candidate |
| EPP metrics | `curl http://<EPP pod IP>:9090/metrics` | the Inference Extension's `inference_*` series |
| pod metrics | `curl http://<pod IP>:8000/metrics` | `vllm:request_success_total` (which pod served), `vllm:prefix_cache_queries_total` and `vllm:prefix_cache_hits_total` (how much of the prompt was already cached) |

Pod metrics are the attribution of record in the measurement post: they do not depend on the routing mode under test.

## Check your result

For one request you can point at the line or counter in every row of the table above.

## Next steps and cleanup

Continue with the [Reproduction Harness](harness.md).
