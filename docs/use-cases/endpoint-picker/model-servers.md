# Deploy the model servers and the Endpoint Picker

Apply the vLLM Deployment, the EPP with its scheduling profile and RBAC, and the `InferencePool` that tells the EPP which pods it may choose.

<!-- example-status-default: illustrative-only -->

## Before you start

Keep `DOCS` and `MF` from [Prerequisites & Downloads](prepare.md). The first `vllm serve` on a node downloads the weights; allow up to an hour.

**Focus of this page:** The pod flags and the EPP profile are pinned so that the EPP's prefix-cache index matches what the pods hold.

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

Apply the namespace, the vLLM Deployment, the EPP and its `InferencePool`:

```bash
kubectl apply -f "$MF/01-namespace.yaml"
kubectl -n llm-d-pd-disaggregation create secret generic llm-d-hf-token --from-literal=HF_TOKEN="$HF_TOKEN"   # optional for public models; the Deployment tolerates a missing secret
kubectl apply -f "$MF/10-vllm.yaml"
kubectl apply -f "$MF/20-epp-config.yaml" -f "$MF/21-epp-rbac.yaml" -f "$MF/22-epp.yaml" -f "$MF/23-epp-service.yaml"
kubectl apply -f "$MF/30-inferencepool.yaml"
```

What the manifests pin, and why it matters to the EPP:

- **vLLM** (`10-vllm.yaml`): `vllm/vllm-openai:v0.30.0`, three replicas spread one per node by pod anti-affinity, `--block-size=16` and `--prefix-caching-hash-algo=sha256_cbor`. The EPP's `approx-prefix-cache-producer` models the prefix cache in 16-token blocks; keeping the pod at the same block size keeps the EPP's index aligned with what the pod actually holds. The pods carry two labels that matter here: `llm-d.ai/guide: pd-disaggregation`, which the `InferencePool` selects on, and `llm-d.ai/role: aggregated`, which the rule script selects on.
- **EPP** (`22-epp.yaml`): `ghcr.io/llm-d/llm-d-router-endpoint-picker:main`, one container, args `--pool-name pd-disaggregation --pool-namespace llm-d-pd-disaggregation --pool-group inference.networking.k8s.io --config-file /config/epp-config.yaml --grpc-health-port 9003 --v=2`. Port 9002 is the ext_proc gRPC endpoint loxilb-igw connects to; 9003 answers gRPC health; 9090 serves Prometheus metrics. `--v` is the klog verbosity: 2 logs startup and errors, 4 logs one `Request handled` line per request and the scheduler's per-candidate scores (used in [Smoke test](smoke-test.md)).
- **EPP scheduling profile** (`20-epp-config.yaml`, an `EndpointPickerConfig`): `prefix-cache-affinity-filter` narrows the candidates to pods that hold the prompt's prefix, `token-load-scorer` and `active-request-scorer` score what remains, `max-score-picker` takes the best. The two producers feed the filter and the scorers.
- **RBAC** (`21-epp-rbac.yaml`): the EPP watches the `InferencePool` and the pods it selects.
- **InferencePool** (`30-inferencepool.yaml`): `selector.matchLabels` is the EPP's view of the pool. `endpointPickerRef` is used only by the kube-loxilb method, which turns it into the rule's `eppEndpoint` and `eppFailureMode`. With a rule you create yourself, loxilb-igw takes both from the rule and the values here have no effect on it.

**Verify.** All three pods Ready, each on its own node with its own IP; the EPP Service with a ClusterIP; the pool present:

```bash
kubectl -n llm-d-pd-disaggregation get pod -l llm-d.ai/role=aggregated -o wide
```
```
NAME                                                            READY   STATUS    RESTARTS   AGE     IP              NODE
pd-disaggregation-nvidia-gpu-vllm-aggregated-646b4c9b66-8m75l   1/1     Running   0          3h17m   198.51.100.11   gpu-node-1
pd-disaggregation-nvidia-gpu-vllm-aggregated-646b4c9b66-8nt4n   1/1     Running   0          3h17m   198.51.100.12   gpu-node-2
pd-disaggregation-nvidia-gpu-vllm-aggregated-646b4c9b66-dwhxv   1/1     Running   0          3h17m   198.51.100.13   gpu-node-3
```
```bash
curl -s http://198.51.100.11:8000/v1/models | python3 -m json.tool | grep '"id"'      # one pod answers with the model id
kubectl -n llm-d-pd-disaggregation get inferencepool pd-disaggregation
kubectl -n llm-d-pd-disaggregation get svc pd-disaggregation-epp -o jsonpath='{.spec.clusterIP}{"\n"}'
```
```
NAME                AGE
pd-disaggregation   2d
203.0.113.6
```

The first `vllm serve` on a node downloads the weights and compiles; the startup probe allows an hour. `kubectl -n llm-d-pd-disaggregation logs deploy/pd-disaggregation-epp` ends with `gRPC server listening ... "port":9002` when the EPP is up.

## Check your result

Three pods `Running 1/1`, one per node; `curl` to one pod's `/v1/models` returns the model id; the EPP Service has a ClusterIP; the EPP log ends with `gRPC server listening`.

## Next steps and cleanup

Continue with [Deploy loxilb-igw](gateway.md). To remove what this chapter created, follow [Teardown](troubleshooting.md#teardown) from the bottom up.
