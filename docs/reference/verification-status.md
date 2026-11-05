# Verification status

This page identifies exactly which public source artifacts support the
monitoring claims in these docs. It separates source presence, workflow
membership, recorded scenario assertions, and deployment qualification. A
scenario checked into the repository—or referenced by a workflow—is not by
itself evidence that its latest run passed.

The frozen source for this page is Gateway commit
`b954a57582b6bb702b5bfa2606817ee77857ae5e`. Git object IDs for every listed
scenario, validation script, and workflow are retained in the docs contract
fixture and checked for drift.

The Gateway commit pins eBPF submodule commit
`b131098ebdbb573cdffb04379821f44e7106f087`. The comparison release
`v0.9.8.9-rc.1` pins
`5536a2117ad2ad1128900a0d808ad7dec2eee2b5`. This records the source delta; it
does not qualify either eBPF revision on a kernel or installed host.

The selected CLI source is
`28832f0c60ab717d8cb5133114edf2c45e22a85c`; its release comparison remains
`v0.9.8.9-rc.2`. This tuple is the current documentation baseline. Historical
model evaluations retain their original source and artifact identities.

## Evidence lanes

| Lane | Status represented here | What it proves | What it does not prove |
| --- | --- | --- | --- |
| Source/static | Frozen and validated | Metric names, labels, activation classes, writer mapping, scenario code, and exact assertion IDs exist at the frozen commit | That any deployment emitted the series or passed a scenario |
| Public workflow membership | `wired` or `not wired` below | Whether the frozen workflow source invokes that scenario | A current green run, coverage of every case, or release qualification |
| Scenario assertions | Exact case IDs below | The public validation script contains those named checks | That those checks ran successfully against this docs change |
| Linux/runtime | Requires separate execution evidence | — | Installed-host behavior, backend delivery, or restart behavior |
| GPU/engine | Requires separate execution evidence | — | GPU model correctness, throughput, or engine-version qualification |
| Two-node HA | Requires separate execution evidence | — | Failover completeness, peer security, or loss-free state transfer |
| Release/product | Not established here | — | Approval, packaging, immutable artifact, or production readiness |

## Frozen claim ledger

| Claim area | Public source | Workflow membership | Exact frozen assertions | Claim boundary |
| --- | --- | --- | --- | --- |
| JWT policy and token accounting | [`cicd/ai-jwtauth`](https://github.com/loxilb-io/loxilb-inference-gateway/tree/b954a57582b6bb702b5bfa2606817ee77857ae5e/cicd/ai-jwtauth) | `wired`: `ai-gateway-sanity.yml` invokes the scenario | `G2`, `M4`, `U1`, `U2`, `UH1`, `UH2`, `UE`, `UE3` | Policy-store behavior and token-accounting assertions only; this set does not directly runtime-assert every JWT/JWKS metric |
| QoS HA and quota-scope metrics | [`cicd/ai-qos-ha-sync`](https://github.com/loxilb-io/loxilb-inference-gateway/tree/b954a57582b6bb702b5bfa2606817ee77857ae5e/cicd/ai-qos-ha-sync) | `wired`: `ha-two-node-nightly.yml` invokes the scenario | `SYNC-1`, `SYNC-2`, `QOS-METRIC-1`, `QOS-METRIC-2`, `QOS-HA-013`, `QOS-HA-014` | Source/workflow membership only; no current public workflow-run or two-node qualification claim |
| P/D and worker scrape metrics | [`cicd/vllm-pd-disagg`](https://github.com/loxilb-io/loxilb-inference-gateway/tree/b954a57582b6bb702b5bfa2606817ee77857ae5e/cicd/vllm-pd-disagg) | `wired`: `ai-gateway-sanity.yml` invokes the scenario | `TH1`, `TH2`, `TH3`, `TH4`, `TH5a`, `TM1b`, `TM2d`, `TN1`, `TN2b`, `TN3b`, `TN4b`, `TN5a`, `TN6b` | Source membership only; a current run and real GPU backend are separate evidence |
| Sockmap observability | [`cicd/sockmap-fullproxy`](https://github.com/loxilb-io/loxilb-inference-gateway/tree/b954a57582b6bb702b5bfa2606817ee77857ae5e/cicd/sockmap-fullproxy) | `not wired` to a frozen GitHub workflow | `O-1`, `O-2`, `O-3`, `O-5`, `O-6` | Uses status/counter/reset observations; the manifest has no dedicated sockmap Prometheus family |
| Monitoring stack | [`cicd/monitoring`](https://github.com/loxilb-io/loxilb-inference-gateway/tree/b954a57582b6bb702b5bfa2606817ee77857ae5e/cicd/monitoring) | `wired`: `monitoring-e2e.yml` and `monitoring-drill.yml` reference the scenario | Scenario-level validation; no stable public case IDs | Workflow membership is not a current run result |

## Metric evidence classes

The generated [metrics reference](metrics.md) records all 298 families marked
`release` in the frozen manifest. It distinguishes four upstream evidence
classes:

- `verified-runtime`: the upstream manifest records runtime evidence;
- `verified-static`: the writer is supported by static or unit evidence;
- `conditional-with-proven-writer`: the writer exists, but emission depends on
  an activated feature path;
- `writer-mapped`: a writer source is mapped, but runtime emission is not
  verified.

These classifications are per metric family. They do not promote the docs
build into Linux, GPU, HA, or release evidence. For an operational decision,
pair the catalog with a raw scrape, a controlled stimulus, an independent
backend or state oracle, and the deployment's immutable build identity.

## How drift is detected

The docs gate regenerates a candidate contract from a selected Gateway commit
and fails on changes to either Swagger file, the engine support catalog, the
metric manifest, the claim-evidence object IDs, or the existing engine scenario
evidence. PromQL examples are checked against the frozen release-scope family
names, label schemas, and documented closed label values.

This is a static consistency gate. Runtime, GPU, HA, and release approval stay
independent.


The selected CLI is regenerated from source alongside the Gateway candidate.
A regression check compares this page's source tuple and metric-family count to
the frozen contracts. See the [example quality contract](example-quality-contract.md)
for static parser, response assertion, file-body, and runtime coverage limits.

The source tuple above supersedes the earlier documentation baseline. Earlier
Quickstart execution results belong to their original image and source tuple;
they do not qualify this newer Gateway revision. The request and P/D closed
label values and allowed combinations are extracted from the selected Go
recorder source. The source hash and complete mapping are retained in the
contract; a changed declaration must be reviewed before regeneration succeeds.
