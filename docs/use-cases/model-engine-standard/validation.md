# QA, Performance and Evidence Limits

<!-- example-status-default: illustrative-only -->

This appendix is separate from the [installation path](matrix-manual.md). Ordinary
operators first need healthy engines, correct Gateway state and completed chat/SSE.
A performance claim requires a controlled workload and independent verification.

## Before you start

Use this page to decide which additional checks your deployment needs.

**Focus of this page:** Separate functional delivery from GPU, release, fail-over and production acceptance.

## Topology and execution locations

--8<-- "snippets/use-cases/topology/llm-reference.md"

This reference diagram locates the client, Gateway and engine evidence. It does not prescribe a replica count or promote historical results to a new topology. Use the exact worker count, roles, ports and artifact identities from the selected runbook or retained result; do not mix that tuple with another guide.

| Where | What happens here |
|---|---|
| Operator terminal | Select the version tuple, private run directory, model snapshot and profiles. |
| Gateway host / namespace | Start the dedicated Gateway; apply and read back only the selected service. |
| Each worker host | Launch the chosen engine and prove direct inference before Gateway traffic. |
| Client | Send the same request through the Gateway and retain its HTTP/SSE observations. |
| Independent evidence | Correlate worker requests/receipts with the selected rule and request identifiers. |

## Reading path and reference

### What is established, and what is still required

| Evidence lane | Scope of this guide | What it does not establish |
|---|---|---|
| Historical original manual observations | Four recommended vLLM converged baselines; Gemma limited; eight startup references; two missing TRT procedures | Supported status of a different released image or optimum for another GPU/workload |
| Current five-model evaluation | vLLM 0.31.0 / SGLang 0.5.19 / TRT rc29: 26 bounded functional PASS and four native architecture BLOCKED across 30 RR/Exact cases; 195-request public ledger | Release-image, capacity, P/D, eBPF/HA or full fail-over qualification |
| Public files | Explicit model revisions, engine digests, rule/request JSON, manifests, fixtures and YAML | Success on your own deployment |
| Documentation checks | Syntax/schema/address hygiene, links, navigation and local site build | Linux/eBPF data plane, real GPU traffic, performance, browser interaction or release qualification |
| Bounded R1 1.5B vLLM 0.31 GPU QA | Three-worker RR/Exact, direct and Gateway chat/SSE, receipts, worker stop/recovery and mode switching; [scope and remaining gates](routing-choice.md#what-was-verified-for-vllm-031) | Original five cards, SGLang/TRT, capacity, full fault/cancellation acceptance, host eBPF/HA or release-image qualification |
| Local service checks to perform | Direct engines, exact rule readback, strict status where used, complete chat/SSE and independent backend receipts | Sustained capacity or lossless fail-over |
| Qualification still required | Your immutable Gateway/model/engine tuple, negative/recovery cases, capacity and application SLO | Approval to release merely because a build or request passed |

The [five-model manual](matrix-manual.md) supplies paired RR/Exact evaluation profiles and records current per-case runtime evidence. These bounded functional checks do not promote upstream catalog support or erase older load failures. The four archived Exact shapes retain historical settings.

The public example inventory labels commands **illustrative-only**. That label
is independent of historical model-card recommendations. The configuration ZIP
contains no private receipts or internal candidate runtime; therefore readers
cannot independently reproduce the original numerical comparisons from this
package. This guide deliberately publishes no numerical speedup or capacity claim.
Keep operational failure limitations visible rather than promoting successful
subsets into a performance result.

### Historical operating lessons

The original comparison used three L4 24 GB workers in a converged pool. vLLM
prefix caching was enabled for both RR and Exact. Exact changed worker placement;
it did not turn engine caching on for the first time.

- Qwen/Llama/R1/EXAONE vLLM baselines had completed comparison conditions and
  form the historical recommended set. Benefits depended on prefix reuse,
  arrivals, output length, queueing and KV pressure.
- Qwen/R1 long-output high-pressure conditions could have worse first-token
  tails with Exact. Less prefill work does not guarantee higher decode throughput
  or lower queue delay. Use RR as a controlled comparator when this matters.
- Gemma failed the historical normal-completion load gate, including direct
  engine comparisons. No sole Gateway cause, fixed capacity or successful
  production optimum follows. Preserve the failure; start with sequential RR
  checks before any controlled capacity study.
- The original SGLang and TRT recipes were startup references. The current
  manual records fresh bounded functional results separately; native architecture
  support alone does not qualify a model/engine/Gateway tuple.
- The original observations used a candidate runtime and registration assets.
  They are not a pure binary-only comparison against arbitrary current releases.
  They do not prove P/D behavior or a new fail-over campaign.

### Measurement and failure qualification

Use [Performance Measurement](../performance-methodology.md) for the common
A/B protocol, input table, complete-population accounting and interpretation.
Use [Step 5](verify.md#negative-and-recovery-checks) for controlled fault checks
and [Step 6](lifecycle.md) for scoped cleanup and restoration. Preserve failed
arms, interrupted streams and independent per-endpoint receipts. The current
functional result does not close capacity, full fail-over or release gates.

## Check your result

Treat an unrun dimension as unqualified even when another dimension passed.

Select a supported model/engine tuple before interpreting results. Keep direct-worker success separate from Gateway delivery, routing evidence, engine cache reuse, performance and release qualification. Historical PASS, FAIL and BLOCKED results retain their original artifact identities.

## Next steps and cleanup

Use the canonical deployment sequence rather than combining fragments from different engine/version pages. Drain before switching or deleting owned resources; retained result pages are evidence, not another deployment recipe. Read the [lab starting point](../model-engine-standard/select.md) if required values are missing. Use [cleanup and recovery](../model-engine-standard/lifecycle.md) when ending the run.

<!-- Previous section IDs: kept so old deep links redirect to the current page. -->
<div class="legacy-anchors" markdown>

- <span id="plan-an-independent-ab-measurement"></span>[plan-an-independent-ab-measurement](../performance-methodology.md)
- <span id="collect-and-interpret-results"></span>[collect-and-interpret-results](../performance-methodology.md)
- <span id="failure-recovery-and-cleanup-gate"></span>[failure-recovery-and-cleanup-gate](verify.md#negative-and-recovery-checks)

</div>
