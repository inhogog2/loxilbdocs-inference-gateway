# Prerequisites and downloads

What the cluster, the gateway node and your shell need before anything is deployed, and where the files come from.

<!-- example-status-default: illustrative-only -->

## Before you start

You need a Kubernetes cluster with GPU nodes, one node you can run a privileged hostNetwork pod on, and a shell that reaches both.

**Focus of this page:** Every later chapter assumes the CRDs, the variables and the downloads from here.

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

| Requirement | Used here |
|---|---|
| Kubernetes cluster with GPU worker nodes and the NVIDIA device plugin (`nvidia.com/gpu` schedulable) | RKE2 v1.36.4, Calico, 3 × A100 80GB, one GPU per node |
| For the kube-loxilb method ([kube-loxilb path](rule.md#kube-loxilb)): kube-loxilb `ghcr.io/loxilb-io/kube-loxilb:epp-annotation` running with `--gatewayAPI --inferenceExtension`, pointed at the gateway's REST API | that tag carries the `InferencePool` manager (kube-loxilb branch `feat/auth-annotation`); its [Inference gateway guide](https://github.com/loxilb-io/kube-loxilb/blob/feat/auth-annotation/INFERENCE_GATEWAY.md) is the reference for everything the pool can carry |
| One node that can run a privileged hostNetwork pod and whose IP clients can reach. Its IP becomes the VIP. | the control-plane node, 192.0.2.10 |
| The `InferencePool` CRD (`inference.networking.k8s.io/v1`), and for the kube-loxilb method the Gateway API CRDs | installed from the release manifests below |
| A shell with `kubectl`, `curl` and `python3` that can reach the gateway's REST API (`:11111` on the gateway node) and every vLLM pod's `:8000` | the same control-plane node |
| The model's weights reachable from the GPU nodes (Hugging Face download or a local mirror) | `Qwen/Qwen3-32B-FP8`, a public model |

Install the CRDs first:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/download/v1.6.2/manifests.yaml
kubectl get crd inferencepools.inference.networking.k8s.io

# only for the kube-loxilb method; the Inference Extension manifest does not include these
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
```

On RKE2 the control-plane node's `kubectl` is the bundled binary with the server kubeconfig. Either export it once or alias it; every command below says `kubectl`:

```bash
export KUBECONFIG=/etc/rancher/rke2/rke2.yaml PATH=$PATH:/var/lib/rancher/rke2/bin
```

Network paths that must be open: client → VIP:8080; gateway node → pod IPs :8000; gateway node → EPP ClusterIP :9002; your shell → pod IPs :8000 (for the metrics reads in the measurement post).

### Downloads

Every file this family uses is under `docs/assets/endpoint-picker/` in the documentation checkout. Set `DOCS` to that checkout and `MF` to the manifests folder once; every command below uses them:

```bash
export DOCS="${DOCS:?path to the documentation checkout}"
export MF="$DOCS/docs/assets/endpoint-picker/manifests"
ls "$MF"
```

| Download | Purpose | What to customize |
|---|---|---|
| [`01-namespace.yaml`](../../assets/endpoint-picker/manifests/01-namespace.yaml) | namespace `llm-d-pd-disaggregation` | the name, everywhere at once |
| [`10-vllm.yaml`](../../assets/endpoint-picker/manifests/10-vllm.yaml) | three vLLM pods, one GPU each | model, image tag, replicas, GPU resources |
| [`20-epp-config.yaml`](../../assets/endpoint-picker/manifests/20-epp-config.yaml) | the EPP scheduling profile | plugin set, only if you measure another profile |
| [`21-epp-rbac.yaml`](../../assets/endpoint-picker/manifests/21-epp-rbac.yaml) | ServiceAccount and ClusterRole for the EPP | nothing |
| [`22-epp.yaml`](../../assets/endpoint-picker/manifests/22-epp.yaml) | the EPP Deployment | image tag, `--v` |
| [`23-epp-service.yaml`](../../assets/endpoint-picker/manifests/23-epp-service.yaml) | the EPP ClusterIP Service (9002, 9003, 9090) | nothing |
| [`30-inferencepool.yaml`](../../assets/endpoint-picker/manifests/30-inferencepool.yaml) | the `InferencePool` and its `endpointPickerRef` | `failureMode` |
| [`40-loxilb-igw.yaml`](../../assets/endpoint-picker/manifests/40-loxilb-igw.yaml) | the loxilb-igw DaemonSet | image tag, `--blacklist`, node placement |
| [`50-gateway.yaml`](../../assets/endpoint-picker/manifests/50-gateway.yaml) | GatewayClass, Gateway, HTTPRoute for the kube-loxilb path | listener port |
| [`rule.sh`](../../assets/endpoint-picker/manifests/rule.sh) | creates the rule in EPP, CHWBL or RR mode from live pod IPs | `VIP`, `PORT`, `FAILMODE` as environment variables |
| [`repro/`](../../assets/endpoint-picker/repro/README.md) | the reproduction harness (`run.sh`, `config.env`) | `config.env` |
| [`baseline/`](../../assets/endpoint-picker/baseline/vllm-pods.txt) | the vLLM, EPP, `InferencePool` and rule objects as captured at measurement time | reference only |
| [`epp-measurements-2026-10.tgz`](../../assets/endpoint-picker/epp-measurements-2026-10.tgz) ([sha256](../../assets/endpoint-picker/epp-measurements-2026-10.tgz.sha256)) | raw logs, summaries and the original scripts behind the [measurements](measurements.md) | reference only |

## Check your result

`kubectl get crd inferencepools.inference.networking.k8s.io` returns the CRD, `ls "$MF"` lists the ten manifests and `rule.sh`.

## Next steps and cleanup

Continue with [Model Servers & Endpoint Picker](model-servers.md). Nothing has been created in the cluster yet except the CRDs.
