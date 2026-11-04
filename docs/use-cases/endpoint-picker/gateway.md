# Deploy loxilb-igw

Run the gateway as a DaemonSet on the control-plane node, check that the build carries the EPP client, and make its rules survive a restart.

<!-- example-status-default: illustrative-only -->

## Before you start

Pods and EPP from [Model Servers & Endpoint Picker](model-servers.md) are Ready. The gateway node's IP is the VIP, `192.0.2.10` here.

**Focus of this page:** `features` must contain `epp`, and `/etc/loxilb` must be a host mount.

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

`40-loxilb-igw.yaml` is a DaemonSet in `kube-system` pinned to control-plane nodes by node affinity, with `hostNetwork: true`, `privileged: true`, the REST API on `:11111`, and `/etc/loxilb` mounted from the host at `/opt/loxilb/config`. Three things to check in it before applying:

1. **Image.** `ghcr.io/loxilb-io/loxilb-inference-gateway:latest`, or a release tag. The L4-only `ghcr.io/loxilb-io/loxilb` image does not carry the EPP client.
2. **`--blacklist`.** The regular expression names the interfaces the gateway must not attach its eBPF programs to: the CNI's veths and tunnels. The shipped value covers Calico and Flannel. For another CNI, add its interface prefixes.
3. **Node placement.** The node affinity selects nodes labelled `node-role.kubernetes.io/control-plane`. To run the gateway elsewhere, change the affinity to a label of your own and add the matching toleration.

```bash
kubectl apply -f "$MF/40-loxilb-igw.yaml"
kubectl -n kube-system rollout status ds/loxilb-lb
curl -s http://192.0.2.10:11111/netlox/v1/version
```
```
{"buildInfo":"...","features":["...","epp","..."],"product":"loxilb-inference-gateway","version":"..."}
```

`features` lists what this build carries. The list differs from release to release and usually has several entries; the check is that `epp` is among them, which is what lets the binary hold an `eppEndpoint` rule. A build without it accepts the field and ignores it.

```bash
curl -s http://192.0.2.10:11111/netlox/v1/version | python3 -c 'import json,sys; f=json.load(sys.stdin)["features"]; print("epp" if "epp" in f else "NO epp", f)'
```

The `/etc/loxilb` mount is what makes rules survive a pod restart: every committed change is written to `/etc/loxilb/snapshot.json` and restored at boot. Without the mount a restart (image change, node reboot, eviction) comes up with no rules. See [Configuration persistence & snapshots](https://github.com/loxilb-io/loxilb-inference-gateway/blob/main/README.md#configuration-persistence--snapshots).

## Check your result

`GET /netlox/v1/version` answers with `product` `loxilb-inference-gateway` and `epp` in `features`; `kubectl -n kube-system rollout status ds/loxilb-lb` is complete.

## Next steps and cleanup

Continue with [Create the EPP Rule](rule.md). Restarting the gateway pod reloads eBPF programs on the node's interfaces; see [Troubleshooting](troubleshooting.md) before doing that on a node that carries other traffic.
