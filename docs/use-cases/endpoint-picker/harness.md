# Run the reproduction harness

`run.sh` reruns every measured section with one command each; `config.env` is the only file to edit for another cluster.

<!-- example-status-default: illustrative-only -->

## Before you start

The layout from the previous chapters: pods selected by a label, the EPP as a Deployment with a ClusterIP Service, an `InferencePool`, the gateway's REST API reachable. Run it on a cluster that is not serving other traffic through the same EPP.

**Focus of this page:** Pod IPs, pod count and the EPP ClusterIP are read from the cluster; they are not in the config.

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

[`repro/`](../../assets/endpoint-picker/repro/README.md) holds `run.sh` and `config.env`, the consolidated form of the scripts behind the post. It expects the layout this guide built: pods selected by a label, the EPP as a Deployment with a ClusterIP Service, an `InferencePool`, and the gateway's REST API reachable. Pod IPs, pod count and the EPP's ClusterIP are read from the cluster at run time, so they are not in the config.

```bash
cd "$DOCS/docs/assets/endpoint-picker/repro" && $EDITOR config.env
```

| `config.env` | Meaning | Value in this guide |
|---|---|---|
| `KUBECTL` | how to invoke kubectl | `kubectl`; the RKE2 sudo form is given in a comment in the file |
| `NS`, `POD_LABEL`, `TARGET_PORT` | namespace and label of the vLLM pods, their port | `llm-d-pd-disaggregation`, `llm-d.ai/role=aggregated`, `8000` |
| `EPP_DEPLOY`, `EPP_SVC`, `EPP_CONTAINER`, `EPP_GRPC_PORT` | EPP resources | `pd-disaggregation-epp`, `pd-disaggregation-epp`, `epp`, `9002` |
| `POOL_NAME`, `POOL_DEFAULT_SELECTOR` | the `InferencePool` and its selector, used to restore it after `verify-decides` | `pd-disaggregation`, `{"llm-d.ai/guide":"pd-disaggregation"}` |
| `LOXILB_API`, `VIP`, `PORT` | the gateway's REST base URL and the test rule's address | `http://192.0.2.10:11111/netlox/v1`, `192.0.2.10`, `8080` |
| `LOXILB_LOG_NS`, `LOXILB_LOG_SEL` | where the gateway log is read from | `kube-system`, `ds/loxilb-lb` |
| `MODEL`, `TOKENIZER` | the served model and the tokenizer guidellm uses. They must match, or the measured cache reuse is wrong | `Qwen/Qwen3-32B-FP8`, same |
| `STREAMS`, `SWEEP_STREAMS`, `TURNS_*`, `PREFIX_*`, `PREFIX_COUNT`, `BENCH_DUR`, `VERIFY_N` | workload sizes | the post's values |

```bash
bash run.sh prereq          # pods Ready, REST reachable, EPP ClusterIP found, guidellm installed (pip --user if missing), tokenizer loads
bash run.sh verify-path     # Step 1: sent == gateway metric == gateway log == EPP log, per-pod distributions equal
bash run.sh verify-decides  # Step 2, pool-independent form: RR alone scatters conversations, the EPP pins them
bash run.sh verify-failmode # EPP scaled to 0: FailClose 503, FailOpen 200, recovery
bash run.sh bench-cache     # multi-turn EPP / CHWBL / RR, long and short conversations
bash run.sh bench-sweep     # concurrency 1 to 64
```

Results land in `~/epp_repro_<timestamp>/` as summary `.tsv`/`.txt` files plus the raw logs and JSON. Each command creates its own rule on `VIP:PORT` and deletes it afterwards, and puts back what it changed: the EPP's `--v`, the EPP's replica count (`verify-failmode` scales it to 0 and back), and the `InferencePool` selector. Run it on a cluster that is not serving other traffic through the same EPP. The harness drives the gateway's REST API directly, so with the kube-loxilb method delete the `HTTPRoute` and the `Gateway` first, or give the harness a different `PORT`. Deleting only the route hands the listener back to the Gateway's ingress Service.

## Check your result

`bash run.sh prereq` prints the Ready pods, `200` for the REST API, the EPP ClusterIP, a guidellm version and `OK` for the tokenizer. Each later command ends with a summary table and names the files it wrote under `~/epp_repro_<timestamp>/`.

## Next steps and cleanup

Compare your summaries with the [Measurements](measurements.md). Then [Troubleshooting & Teardown](troubleshooting.md).
