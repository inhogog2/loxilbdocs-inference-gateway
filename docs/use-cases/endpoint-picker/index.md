# Route LLM requests through the Gateway API Inference Extension Endpoint Picker

Run three vLLM pods, one Endpoint Picker (EPP) and loxilb-igw, with one load-balancer rule that asks the EPP where every request should go. This family ends where the [measurements](measurements.md) begin: a request sent to the gateway VIP shows up in the EPP log, in the gateway log and metric, and on the pod that served it.

<!-- example-status-default: illustrative-only -->

## Before you start

Choose this family when a Kubernetes cluster already serves a model with vLLM, or will, and request routing should follow the prefix cache instead of round robin. The rule fields and the behaviours an operator meets afterwards are in [26 — Endpoint Picker (EPP) operator notes](https://github.com/loxilb-io/loxilb-inference-gateway/blob/main/docs/load-balancing/26-endpoint-picker-epp.md). This page is the order of operations.

**Focus of this page:** The EPP decides, the gateway enforces; both are observable per request.

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

### What you will have

```
client ──> VIP:8080 on the gateway node
               │ loxilb-igw (DaemonSet, hostNetwork)
               │   rule: mode 4, eppEndpoint = <EPP ClusterIP>:9002
               ├──> EPP (Deployment + ClusterIP Service, ext_proc gRPC :9002)
               │        reads the InferencePool, picks a pod, answers with its address
               └──> vLLM pod :8000 named by the EPP
```

Every manifest below is in [the `manifests/` folder](../../assets/endpoint-picker/manifests/README.md). The resource names follow the llm-d chart release they were captured from; the chart itself is not needed.

### Reading path

| Operator task | Chapter | Outcome |
|---|---|---|
| Install the CRDs, choose the gateway node, download the files | [Prerequisites & Downloads](prepare.md) | a shell that reaches the cluster, the REST API and the pods |
| Run the model servers and the Endpoint Picker | [Model Servers & Endpoint Picker](model-servers.md) | three Ready vLLM pods, an EPP with a ClusterIP, an `InferencePool` |
| Run the gateway | [Deploy loxilb-igw](gateway.md) | a DaemonSet whose `/version` lists `epp` |
| Attach the EPP to a rule, by hand or through kube-loxilb | [Create the EPP Rule](rule.md) | one rule on the VIP with `eppEndpoint` set |
| Send one request and read it at four points | [Smoke Test](smoke-test.md) | the same pod named by the EPP, the gateway and the pod's own counter |
| Change between EPP, CHWBL and round robin | [Switching Routing Modes](modes.md) | the same rule with two fields changed |
| Know what to read while it runs | [Observability](observability.md) | gateway log and metrics, EPP log and metrics, pod metrics |
| Rerun the measurements | [Reproduction Harness](harness.md) | one command per measured section |
| Diagnose and remove it | [Troubleshooting & Teardown](troubleshooting.md) | symptom table, teardown in order |
| Read what was measured | [Measurements](measurements.md) | EPP vs. CHWBL vs. round robin on cache reuse, TTFT and throughput |

Two things are fixed throughout. The Endpoint Picker is the llm-d router EPP image; its scheduling profile (prefix-cache affinity filter, load scorers, max-score picker) is the one the chapters measure against. The addresses are documentation addresses: the gateway VIP is `192.0.2.10`, the three pods are `198.51.100.11`, `.12` and `.13`, the EPP's ClusterIP is `203.0.113.6`. Substitute your own; the harness and the rule script read the pod and Service addresses from the cluster.

## Check your result

You can name, for each chapter, the one observation that proves it worked: Ready pods, a ClusterIP, `epp` in `features`, a rule with `eppEndpoint`, matching addresses at four points.

## Next steps and cleanup

Start with [Prerequisites & Downloads](prepare.md). Nothing in this family changes a running production service; it builds a dedicated pool and a dedicated rule and removes them in [Teardown](troubleshooting.md#teardown).
