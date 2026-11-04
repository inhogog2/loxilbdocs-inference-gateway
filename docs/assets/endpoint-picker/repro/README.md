# Endpoint Picker verification and cache benchmark harness

`run.sh` reruns every measurement behind the Endpoint Picker pages: the data-path and decision checks, the failure-mode check, the multi-turn cache-reuse benchmark and the concurrency sweep. When the cluster or topology changes, edit `config.env` only. Pod IPs, the pod count and the EPP's ClusterIP are read from the cluster on every run.

| File | Role |
|---|---|
| `config.env` | cluster names, addresses and workload sizes (the only file to edit) |
| `run.sh` | every command, as subcommands |

## Before you start

1. Run it on a host that reaches the gateway's REST API (`:11111`), the gateway VIP and every model-server pod's `:8000/metrics`. The control-plane node that runs the gateway is the usual choice.
2. Edit `config.env`: `KUBECTL` (how to call kubectl), the namespace and resource names, `LOXILB_API` / `VIP` / `PORT`, and `MODEL` / `TOKENIZER`. The tokenizer must match the served model, or the measured cache reuse is wrong.
3. `bash run.sh prereq` checks the pods are Ready, the REST API answers, the EPP ClusterIP is found, guidellm is installed (it runs `pip install --user guidellm` if not) and the tokenizer loads.
4. Wait until every model-server pod is Ready before running anything else.

If the login shell prints a banner into the output, run `bash --noprofile --norc run.sh <command>`.

## Commands

```
bash run.sh <command>
```

| Command | What it measures |
|---|---|
| `prereq` | the checks above |
| `verify-path` | every request goes through the EPP: requests sent == gateway metric delta == gateway `-> ip` lines == EPP `Request handled` lines, and the per-pod split is the same on both sides |
| `verify-decides` | the EPP decides: the same conversations under the rule's round robin alone scatter over several pods, under the EPP each stays on one pod |
| `verify-affinity` | prefix-cache affinity, the same measurement as `bench-cache` |
| `verify-vllm` | one model-server pod is force-deleted under load; counts non-200 responses |
| `verify-failmode` | the EPP is scaled to 0: `FailClose` answers 503, `FailOpen` answers 200 through the rule's own selector, then the EPP is scaled back |
| `verify-all` | the four verifications in order |
| `bench-cache` | multi-turn conversations, EPP / CHWBL / RR, long and short: cache reuse, requests per second, TTFT |
| `bench-singleshot` | concurrent single-shot requests with shared prefixes, as a contrast to the multi-turn workload |
| `bench-sweep` | throughput at concurrency 1, 4, 8, 16, 32, 64 per mode |
| `bench-all` | the three benchmarks |
| `all` | everything |

Results go to `~/epp_repro_<timestamp>/`: summary `.tsv` and `.txt` files plus the raw logs and guidellm JSON.

## What a pass looks like

- `verify-path`: the four counts are equal and the per-pod split from the EPP log equals the split from the gateway log.
- `verify-decides`: under RR alone most conversations touch more than one pod; under the EPP every conversation stays on one pod.
- `bench-cache`: EPP and CHWBL reuse well above RR, and higher requests per second.
- `verify-vllm`: no non-200 response while the pod is deleted.
- `verify-failmode`: all 503 under `FailClose`, all 200 under `FailOpen` spread over several pods, and the EPP path works again after scale-up.
- `bench-sweep`: EPP and CHWBL throughput rises with concurrency, RR saturates early.

## What each command changes, and restores

Every command creates its own rule on `VIP:PORT` and deletes it at the end. `verify-path` raises the EPP's `--v` to 4 and puts it back. `verify-failmode` scales the EPP Deployment to 0 and back to its previous replica count. Run the harness on a cluster that is not serving other traffic through the same EPP. The harness drives the gateway's REST API directly; on a cluster where kube-loxilb owns the rule, delete the `HTTPRoute` and `Gateway` first or give the harness a different `PORT`.

## Two things that decide whether numbers are comparable

- The cache-affinity gain of EPP and CHWBL comes from sequential multi-turn conversations. Concurrent single-shot requests (`bench-singleshot`) get no affinity benefit, and spreading them (RR) can do as well or better. The workload shape decides the conclusion.
- guidellm's tokenizer must be the served model's. A stand-in tokenizer changes prompt lengths and with them the measured reuse.

## Two environment notes

- An EPP scheduled on a node that can go down leaves every EPP-routed request at 503 while its pod sits in `Terminating`. Recover with `kubectl -n <NS> delete pod <epp-pod> --grace-period=0 --force`; the EPP needs no GPU and reschedules anywhere.
- guidellm probes the backend before a benchmark. If the EPP is down, the probe gets 503 and guidellm stops with "Backend validation failed". Check that the EPP accepts on `:9002` before an EPP-mode benchmark.
