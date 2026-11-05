# Switching routing modes

EPP, loxilb-igw CHWBL and loxilb-igw RR are the same rule with two fields changed. This page switches between them with the rule script or, under kube-loxilb, on the pool.

<!-- example-status-default: illustrative-only -->

## Before you start

The rule from [Create the EPP Rule](rule.md) is in place and the [smoke test](smoke-test.md) passed.

**Focus of this page:** `eppEndpoint` cannot be patched, so a mode change is a delete and a create.

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

The three modes in the measurement post are the same rule with two fields changed. `rule.sh` deletes and recreates it, because `eppEndpoint` cannot be patched:

| Mode | `eppEndpoint` | `sel` | Command |
|---|---|---|---|
| EPP | set | `0` (fallback only) | `bash "$MF/rule.sh" epp` |
| loxilb-igw CHWBL | absent | `8` | `bash "$MF/rule.sh" chwbl` |
| loxilb-igw RR | absent | `0` | `bash "$MF/rule.sh" rr` |

`FAILMODE=FailOpen bash "$MF/rule.sh" epp` creates the EPP rule that falls back to `sel` instead of answering 503 when the EPP is down. With kube-loxilb the same changes go on the pool, and kube-loxilb updates the rule:

```bash
kubectl -n $NS patch inferencepool pd-disaggregation --type merge -p '{"spec":{"endpointPickerRef":{"failureMode":"FailClose"}}}'     # FailClose (the manifest ships FailOpen)
kubectl -n $NS patch inferencepool pd-disaggregation --type json -p '[{"op":"remove","path":"/spec/endpointPickerRef"}]'               # no EPP
kubectl -n $NS annotate inferencepool pd-disaggregation loxilb.io/epselect=chwbl --overwrite                                        # selector: chwbl or rr
```

Deleting the last rule on a VIP:port keeps the listener open and answering `503 no_route` until a new rule takes it over; see [26 § A listener kept after its last rule is deleted](https://github.com/loxilb-io/loxilb-inference-gateway/blob/main/docs/load-balancing/26-endpoint-picker-epp.md#a-listener-kept-after-its-last-rule-is-deleted).

## Check your result

`rule.sh show` (or `GET /config/loadbalancer/all`) shows the expected `sel` and the presence or absence of `eppEndpoint`; a request to the VIP returns 200.

## Next steps and cleanup

Continue with [Observability](observability.md). Leave the rule in EPP mode before running the [harness](harness.md); it creates its own rules anyway.
