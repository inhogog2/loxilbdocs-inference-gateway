# Troubleshooting and teardown

Symptoms you may meet at each step, what causes them and where to look, followed by the teardown in reverse order of deployment.

<!-- example-status-default: illustrative-only -->

## Before you start

Have the chapter that produced the symptom open; the `Check` column names the command or page.

**Focus of this page:** Most symptoms are a stale rule (pods or the EPP Service were recreated) or a gateway build without `epp`.

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

### Symptoms

| Symptom | Cause | Check |
|---|---|---|
| `503 {"error":"epp_unavailable","detail":"the endpoint picker did not answer"}` | the EPP is not reachable from the gateway node: no pod behind the Service, wrong ClusterIP or port in `eppEndpoint`, TLS mismatch (`eppPlaintext`), or the decision took longer than `eppTimeoutMs` | `kubectl -n $NS get pod,svc -l app.kubernetes.io/name=pd-disaggregation-epp`; `loxilb_ai_epp_duration_seconds` buckets; `rule.sh show` |
| `503 {"error":"epp_no_endpoint", ...}` | the EPP named a pod that is not in the rule's `endpoints`, or is marked down: pods were recreated and the rule still lists the old IPs | compare `kubectl get pod -o wide` with `rule.sh show`; re-run `rule.sh epp` |
| rule POST rejected | `mode` is not 4, or `eppEndpoint` is longer than 255 bytes | the error body names the field |
| `loxilb_ai_epp_requests_total` does not move | the request hit a different VIP:port, or the rule has no `eppEndpoint` | `rule.sh show`; `curl $LB/config/loadbalancer/all` |
| no `Request handled` lines | the EPP runs at `--v=2`, or the log was read from the wrong container | [Smoke test](smoke-test.md)'s patch; `-c epp` |
| all rules gone after the gateway pod restarted | `/etc/loxilb` is not mounted from the host | `kubectl -n kube-system get ds loxilb-lb -o jsonpath='{.spec.template.spec.volumes}'` |
| `503 no_route` from the VIP | the last rule on that VIP:port was deleted and the listener is kept open | create the rule |
| kube-loxilb: no `<pool>-inference` Service | kube-loxilb runs without `--inferenceExtension`, or the pool is not attached by an `HTTPRoute` to a `Gateway` of class `loxilb-gc` | `kubectl -n kube-system logs deploy/kube-loxilb`; `kubectl -n $NS get gateway,httproute` |
| kube-loxilb rejects `--inferenceExtension` at start | the image is not `:epp-annotation` (an older tag has no `InferencePool` manager), or `--gatewayAPI` is missing | `kubectl -n kube-system get deploy kube-loxilb -o jsonpath='{.spec.template.spec.containers[0].image}'`; `kubectl -n kube-system logs deploy/kube-loxilb` |
| kube-loxilb: `InferenceGatewayRequired` event on the pool's Service | the gateway behind `--loxiURL` is plain loxilb, not loxilb-igw | [Deploy loxilb-igw](gateway.md)'s `/version` check: `product` must be `loxilb-inference-gateway` |
| kube-loxilb: `ExternalIPUnavailable` event right after applying the Gateway | the Gateway's ingress Service held the listener port for a moment before the route was seen | wait; the pool's Service takes the port once it is released |
| kube-loxilb: `ResolvedRefs=False`, reason `InvalidExtensionRef` | the Service is missing from the pool's namespace, headless or `ExternalName`, or `port` is missing or not on the Service | the condition's message names the cause |
| kube-loxilb: pool `Accepted=False`, reason `NotSupportedByParent` | `lbmode` is not `fullproxy`, `pd-disagg` is set, or the pool has more than one `targetPorts` entry | the condition's message |
| kube-loxilb: `LoxiLBRejected`, `externalIP <VIP> is not an address of this gateway` | the VIP in `--cidrPools` is not configured on the gateway node | `ip addr` on that node |
| kube-loxilb: `EndpointPickerUnsupported` event | the gateway build does not list `epp` | [Deploy loxilb-igw](gateway.md)'s `/version` check |
| guidellm's prefix-cache reuse is far from the post's numbers | `TOKENIZER` differs from the served model | `config.env` |
| the SSH session to the gateway node drops when the gateway pod restarts | eBPF programs reload on the node's interfaces | [26 § Restarting the gateway on a node that carries other traffic](https://github.com/loxilb-io/loxilb-inference-gateway/blob/main/docs/load-balancing/26-endpoint-picker-epp.md#restarting-the-gateway-on-a-node-that-carries-other-traffic) |

### Teardown { #teardown }

```bash
bash "$MF/rule.sh" delete                                                # direct rule
kubectl delete -f "$MF/50-gateway.yaml"                                  # kube-loxilb path: the generated Service and rule go with these; kube-loxilb stays
kubectl -n $NS patch deploy pd-disaggregation-epp --type=json -p "[{\"op\":\"replace\",\"path\":\"$P\",\"value\":\"--v=2\"}]"   # $P from the smoke test
kubectl delete -f "$MF/40-loxilb-igw.yaml"
kubectl delete -f "$MF/30-inferencepool.yaml" -f "$MF/23-epp-service.yaml" -f "$MF/22-epp.yaml" -f "$MF/21-epp-rbac.yaml" -f "$MF/20-epp-config.yaml" -f "$MF/10-vllm.yaml"
kubectl delete -f "$MF/01-namespace.yaml"
```

The harness's result folders under `~/epp_repro_*` are left in place.

## Check your result

After teardown: `GET /config/loadbalancer/all` lists no rule on the VIP:port; `kubectl get ns llm-d-pd-disaggregation` reports not found; `kubectl -n kube-system get ds loxilb-lb` reports not found.

## Next steps and cleanup

The harness's result folders under `~/epp_repro_*` are left in place. kube-loxilb, if you used it, is untouched.
