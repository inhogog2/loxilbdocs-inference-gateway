# Endpoint Picker manifests

Manifests for the [Endpoint Picker use-cases](../../../use-cases/endpoint-picker/index.md). Apply in file order; the chapters set `MF` to this folder.

| File | Creates |
|---|---|
| `01-namespace.yaml` | namespace `llm-d-pd-disaggregation` |
| `10-vllm.yaml` | 3 × vLLM `Qwen/Qwen3-32B-FP8`, one GPU each, label `llm-d.ai/role: aggregated` |
| `20-epp-config.yaml` | `EndpointPickerConfig` (prefix-cache-affinity-filter, token-load-scorer, active-request-scorer, max-score-picker) |
| `21-epp-rbac.yaml` | ServiceAccount, ClusterRole, ClusterRoleBinding for the EPP |
| `22-epp.yaml` | EPP Deployment `pd-disaggregation-epp` (`llm-d-router-endpoint-picker:main`) |
| `23-epp-service.yaml` | ClusterIP Service: 9002 ext_proc gRPC, 9003 health, 9090 metrics |
| `30-inferencepool.yaml` | `InferencePool pd-disaggregation` selecting the vLLM pods, `endpointPickerRef` → the EPP Service |
| `50-gateway.yaml` | kube-loxilb path only: `GatewayClass loxilb-gc`, `Gateway inference-gw` (listener :8080), `HTTPRoute llm-route` → the pool. kube-loxilb turns them into the rule |
| `40-loxilb-igw.yaml` | loxilb-igw DaemonSet in `kube-system`, control-plane nodes, hostNetwork, `/etc/loxilb` persisted |
| `rule.sh` | creates the test rule in EPP / CHWBL / RR mode from live pod IPs and the EPP ClusterIP |

```bash
export VIP=192.0.2.10 PORT=8080 LB=http://$VIP:11111/netlox/v1   # VIP = the gateway node's IP
bash rule.sh epp      # or chwbl | rr | delete | show
```

Or, with kube-loxilb running `--gatewayAPI --inferenceExtension`, skip `rule.sh` and `kubectl apply -f 50-gateway.yaml`; delete the direct rule first if one exists on the same VIP:port.
