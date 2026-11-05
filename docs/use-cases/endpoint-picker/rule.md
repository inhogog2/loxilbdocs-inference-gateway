# Create the EPP rule

One rule carries the whole configuration. Create it directly through the REST API, or let kube-loxilb create it from the `InferencePool` and an `HTTPRoute`; the gateway treats the result the same way.

<!-- example-status-default: illustrative-only -->

## Before you start

The gateway from [Deploy loxilb-igw](gateway.md) lists `epp` in `features`. Use one of the two paths per VIP:port; the chapters after this one apply to both.

**Focus of this page:** `eppEndpoint` names the EPP, `eppFailureMode` decides what happens without it, `sel` is the fallback.

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

One rule carries the whole configuration. There are two ways to create it, and the gateway treats the result the same way. Use one of them per VIP:port: [Smoke test](smoke-test.md) onward applies to both.

| | Direct rule | kube-loxilb |
|---|---|---|
| Who writes the rule | you, through the gateway's REST API | kube-loxilb, from the `InferencePool` and an `HTTPRoute` |
| Extra components | none | kube-loxilb, Gateway API CRDs, `GatewayClass`, `Gateway`, `HTTPRoute` |
| Pods are recreated | re-run `rule.sh` | endpoints follow the pods |
| EPP Service gets a new ClusterIP | re-run `rule.sh` | picked up from the Service |
| Use it for | measurements, debugging, a gateway without Kubernetes controllers | clusters where the rule should follow Kubernetes objects |

### Direct rule

Create it with `rule.sh`, which reads the pod IPs and the EPP's ClusterIP from the cluster and posts the rule:

```bash
export VIP=192.0.2.10 PORT=8080 LB=http://192.0.2.10:11111/netlox/v1
bash "$MF/rule.sh" epp
bash "$MF/rule.sh" show
```

The rule it posts, with the values from the cluster above:

```json
{
  "serviceArguments": {
    "externalIP": "192.0.2.10", "port": 8080, "protocol": "tcp", "mode": 4,
    "sel": 0,
    "name": "igw-epp",
    "eppEndpoint": "203.0.113.6:9002",
    "eppFailureMode": "FailClose",
    "eppTimeoutMs": 3000
  },
  "endpoints": [
    {"endpointIP": "198.51.100.11", "targetPort": 8000, "weight": 1},
    {"endpointIP": "198.51.100.13", "targetPort": 8000, "weight": 1},
    {"endpointIP": "198.51.100.12", "targetPort": 8000, "weight": 1}
  ]
}
```

| Field | Meaning |
|---|---|
| `mode: 4` | fullproxy: the gateway terminates the client connection and opens its own to the pod, which is where it can consult the EPP per request. Required with `eppEndpoint`. |
| `sel` | the rule's own selector, `0` round robin or `8` CHWBL (consistent hashing on the prompt prefix). With an EPP attached it is used only on `FailOpen` fallback. |
| `eppEndpoint` | `host:port` of the EPP's ext_proc gRPC server; the Service ClusterIP works because the gateway runs on a cluster node. At most 255 bytes. Not patchable: recreate the rule to change it. |
| `eppFailureMode` | `FailClose` (default): 503 `epp_unavailable` when the EPP does not answer, 503 `epp_no_endpoint` when nothing it named is usable. `FailOpen`: fall back to `sel`. |
| `eppPlaintext` | `true` connects without TLS. The default `false` uses TLS without certificate verification, which matches the self-signed certificate the llm-d image serves. |
| `eppTimeoutMs` | the wait for the EPP's decision, dial included. Default 3000. |
| `endpoints` | the pods the gateway may forward to. A candidate the EPP names must be in this list, or it is skipped. Pod IPs change when pods are recreated: re-run `rule.sh`. |

The REST calls behind the script, for reference (`rule.json` is the document above):

```bash
curl -s -X POST   $LB/config/loadbalancer -H 'Content-Type: application/json' -d @rule.json      # create
curl -s           $LB/config/loadbalancer/externalipaddress/$VIP/port/$PORT/protocol/tcp         # read one
curl -s -X DELETE $LB/config/loadbalancer/externalipaddress/$VIP/port/$PORT/protocol/tcp         # delete
curl -s           $LB/config/loadbalancer/all                                                    # list
```

### kube-loxilb

kube-loxilb reads an `InferencePool` that an `HTTPRoute` attaches to a `Gateway`, generates a LoadBalancer Service named `<pool>-inference`, and programs the same rule as above on the gateway. It resolves `endpointPickerRef` to the EPP Service's ClusterIP and never talks to the EPP itself. The direct rule must not be on the same VIP:port, so run `bash "$MF/rule.sh" delete` first if you created one. This section covers the EPP-specific part; kube-loxilb's [Inference gateway guide](https://github.com/loxilb-io/kube-loxilb/blob/feat/auth-annotation/INFERENCE_GATEWAY.md) has every annotation a pool can carry and the full event list.

**Check the running kube-loxilb.** The image is `ghcr.io/loxilb-io/kube-loxilb:epp-annotation`, the build that carries the `InferencePool` manager. The manager starts with `--inferenceExtension`, which needs `--gatewayAPI`; `--loxiURL` must name the REST API from [Deploy loxilb-igw](gateway.md) and `--cidrPools` must contain the VIP. Fullproxy binds a socket on the VIP, so the VIP has to be an address configured on the gateway node; here it is that node's IP, as a `/32`:

```bash
kubectl -n kube-system get deploy kube-loxilb -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}{range .spec.template.spec.containers[0].args[*]}{@}{"\n"}{end}' | grep -E 'kube-loxilb:|loxiURL|cidrPools|gatewayAPI|inferenceExtension'
```
```
ghcr.io/loxilb-io/kube-loxilb:epp-annotation
--loxiURL=http://192.0.2.10:11111
--cidrPools=defaultPool=192.0.2.10/32
--gatewayAPI
--inferenceExtension
```

If kube-loxilb is not running yet, the branch's Gateway API manifest deploys it with that image and these flags. The sample's `--setRoles` and `--setLBMode` are for a loxilb running outside the cluster and are dropped:

```bash
curl -s https://raw.githubusercontent.com/loxilb-io/kube-loxilb/feat/auth-annotation/manifest/gateway-api/kube-loxilb.yaml \
  | sed -e 's#ghcr.io/loxilb-io/kube-loxilb:latest#ghcr.io/loxilb-io/kube-loxilb:epp-annotation#' \
        -e 's#^\( *\)- --cidrPools=.*#\1- --loxiURL=http://192.0.2.10:11111\n\1- --cidrPools=defaultPool=192.0.2.10/32#' \
        -e 's#^\( *\)- --gatewayAPI#&\n\1- --inferenceExtension#' \
        -e '/- --setRoles=/d' -e '/- --setLBMode=/d' \
  | kubectl apply -f -
kubectl -n kube-system rollout status deploy/kube-loxilb
```

kube-loxilb waits for the `inferencepools.inference.networking.k8s.io` CRD from [Prerequisites](prepare.md) and does nothing with pools until it exists.

**The pool's `endpointPickerRef`.** `30-inferencepool.yaml` from [Model servers](model-servers.md) already carries it; this is the part kube-loxilb reads:

```yaml
spec:
  targetPorts:
    - number: 8000                   # the pods' port; only one entry is allowed with an EPP
  endpointPickerRef:
    name: pd-disaggregation-epp      # a Service in the pool's namespace, with a ClusterIP
    port:
      number: 9002                   # the Service port, not the pod's targetPort; required
    failureMode: FailOpen            # FailClose to answer 503 instead of falling back
```

**Attach the pool to a Gateway.** With the direct rule, `VIP` and `PORT` were shell variables. Here the same two values come from a `Gateway`, and the link between the pool and that Gateway is an `HTTPRoute`. `50-gateway.yaml` holds the three objects:

```bash
kubectl apply -f "$MF/50-gateway.yaml"
```

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: loxilb-gc
spec:
  controllerName: loxilb.io/loxilb   # kube-loxilb's controller name: Gateways of this class belong to it
```

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: inference-gw
  namespace: llm-d-pd-disaggregation
spec:
  gatewayClassName: loxilb-gc
  # No addresses: kube-loxilb assigns one from --cidrPools, here the only one, 192.0.2.10.
  # To pin an address instead:
  # addresses:
  #   - type: IPAddress
  #     value: 192.0.2.10
  listeners:
    - name: http
      protocol: HTTP
      port: 8080                     # becomes the rule's port
      allowedRoutes:
        namespaces:
          from: Same
```

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: llm-route
  namespace: llm-d-pd-disaggregation
spec:
  parentRefs:
    - name: inference-gw
      sectionName: http              # which listener; without it, the first HTTP listener
  rules:
    - backendRefs:
        - group: inference.networking.k8s.io   # required: the backend is a pool, not a Service
          kind: InferencePool
          name: pd-disaggregation
```

Each object settles one thing. The `GatewayClass` says which controller owns the Gateway, so another Gateway API controller in the cluster leaves it alone; one per cluster is enough. The `Gateway` fixes the address and the port: kube-loxilb writes the address into the Gateway's `status.addresses`, and the listener's port is the rule's port. The `HTTPRoute` ties the pool to the Gateway: `parentRefs` names the Gateway and listener, `backendRefs` names the pool. When all three are in place kube-loxilb creates the LoadBalancer Service `pd-disaggregation-inference`, and its usual Service path turns that into the rule. The Service's fields come from these places:

| Service / rule field | Where it comes from |
|---|---|
| namespace | the `InferencePool`'s namespace |
| `externalIP` | the Gateway's address: `spec.addresses` if set, otherwise one from `--cidrPools`, assigned the same way as for a manual LoadBalancer Service |
| `port` | the Gateway listener's port |
| `endpoints`, `targetPort` | the pods the pool's `selector` matches, on `targetPorts[0]`. The selector must match only model servers; pod changes need no action |
| `mode: 4` | `loxilb.io/lbmode` defaults to `fullproxy`, and `loxilb.io/usepodnetwork: "yes"` is always set, since the endpoints are pods |
| `sel` | annotation `loxilb.io/epselect` on the pool or route; default `rr`, `chwbl` for CHWBL |
| `eppEndpoint` | `endpointPickerRef` (`name`, `port`) resolved to `<ClusterIP>:<port>`. A `loxilb.io/epp-endpoint` annotation on the pool or route is discarded |
| `eppFailureMode` | `endpointPickerRef.failureMode`; the API default is `FailClose` |
| `eppTimeoutMs`, `eppPlaintext` | annotations `loxilb.io/epp-timeout-ms` and `loxilb.io/epp-plaintext: "true"`, on the pool or route |
| `loadBalancerClass` | kube-loxilb's `--loxilbLoadBalancerClass`, default `loxilb.io/loxilb` |

A listener that an `InferencePool` is attached to is left out of the Gateway's own `<gateway>-ingress-service`, so the two never claim the same address and port.

**Verify.** The pool should report `Accepted` and `ResolvedRefs` as `True`, the generated Service should hold the VIP, and the rule should carry the EPP's address:

```bash
NS=llm-d-pd-disaggregation; LB=http://192.0.2.10:11111/netlox/v1
kubectl -n $NS get inferencepool pd-disaggregation -o jsonpath='{range .status.parents[*].conditions[*]}{.type}={.status} {.message}{"\n"}{end}'
kubectl -n $NS get svc pd-disaggregation-inference
curl -s $LB/config/loadbalancer/all | python3 -m json.tool | grep -E '"(externalIP|name|mode|sel|eppEndpoint|eppFailureMode|endpointIP)"'
```

`ResolvedRefs` names the address it found, as `endpoint picker "pd-disaggregation-epp" resolved to 203.0.113.6:9002 (failureMode FailOpen)`. If the reference does not resolve, `ResolvedRefs` is `False` with reason `InvalidExtensionRef`. A `FailOpen` pool is then served by `epselect`. A `FailClose` pool keeps its rule, pointed at `127.0.0.1:1`, and answers 503 `epp_unavailable` until the reference resolves.

Checked on 2026-11-04 with kube-loxilb `:epp-annotation` (commit 3c98a39) and the llm-d Endpoint Picker v1.0.0, against a pool and route of this shape: the rule kube-loxilb programmed differed from the direct rule only in its id and `name`; 6 of 6 requests sent to the VIP went through the EPP and returned 200; deleting and recreating the EPP Service moved the rule's `eppEndpoint` to the new ClusterIP without touching the pool.

The gateway must list `epp` under `features` ([Deploy loxilb-igw](gateway.md)). Without it, kube-loxilb refuses a `FailClose` pool and sends a `FailOpen` pool without the EPP, both with an `EndpointPickerUnsupported` event. kube-loxilb also refuses a pool that sets both an EPP and `loxilb.io/pd-disagg`, reported as `Accepted=False` with reason `NotSupportedByParent`.

## Check your result

Direct rule: `rule.sh show` returns the rule with `eppEndpoint` set to the EPP ClusterIP and port. kube-loxilb: the pool reports `Accepted=True` and `ResolvedRefs=True`, the Service `pd-disaggregation-inference` holds the VIP, and `GET /config/loadbalancer/all` shows the same rule.

## Next steps and cleanup

Continue with the [Smoke Test](smoke-test.md). `bash "$MF/rule.sh" delete` removes the direct rule; deleting the `HTTPRoute` removes the kube-loxilb one.
