# Converged RR and KV-Exact: Five-Model Guide

## Before you start

Choose the model/engine tuple from the result ledger before starting.

**Focus of this page:** One converged pool, three replicas, one complete six-step guide.

## Topology and execution locations

--8<-- "snippets/use-cases/topology/converged.md"

This diagram shows the converged three-worker guide. Choose one engine and one model per run: workers 1/2/3 are replicas of that choice, not vLLM, SGLang and TensorRT-LLM mixed together. Select actual host addresses in the model-selection step; documentation addresses are examples. Each converged worker performs both prefill and decode.

| Where | What happens here |
|---|---|
| Operator terminal | Select the version tuple, private run directory, model snapshot and profiles. |
| Gateway host / namespace | Start the dedicated Gateway; apply and read back only the selected service. |
| Each worker host | Launch the chosen engine and prove direct inference before Gateway traffic. |
| Client | Send the same request through the Gateway and retain its HTTP/SSE observations. |
| Independent evidence | Correlate worker requests/receipts with the selected rule and request identifiers. |

## Reading path and reference

Use this ordered guide to prepare a three-worker converged service and choose RR
or strict KV-Exact. Every worker performs both prefill and decode. Follow the
steps in order; later pages reuse the variables and evidence directory selected
in Step 1. Commands are individual, editable operator actions.

| Step | Outcome |
|---|---|
| [1. Select a model and check prerequisites](select.md) | Check model access, actual case results, versions, hardware and allocated addresses; initialize one run directory |
| [2. Prepare models and profiles](prepare.md) | Verify snapshot/image integrity; for Exact, stage the engine-specific evaluation registry |
| [3. Launch engine workers](launch.md) | Run one selected engine on each worker and check direct inference |
| [4. Configure Gateway routing](configure.md) | Start the dedicated Gateway, publish the staged registry when selected, then apply/read back one RR/Exact rule |
| [5. Verify requests and routing](verify.md) | Complete chat/SSE, correlate independent receipts and reject invalid changes without mutation |
| [6. Switch modes, clean up and roll back](lifecycle.md) | Drain, replace or delete only owned resources and prove restoration |

The evaluated baseline is **vLLM 0.31.0, SGLang 0.5.19 and TRT 1.3.0rc29/PyTorch**.
Check [functional results](results.md) before selecting a tuple: 26 bounded
functional PASS and four native architecture BLOCKED cases. TRT Gemma2/EXAONE
are blocked on this pinned backend in both modes. Gemma's earlier load failures
remain open. These are source-built, isolated proxy-only observations, not
release, capacity, P/D, host eBPF/HA or full fail-over qualification.

For model-specific identities and exceptions, see [Model Matrix and Notes](models.md).
For catalog membership and the pending registration proposal, see
[Profile Catalog](profiles.md) and [Catalog/Installer Compatibility](catalog-installer.md).
These five QA profiles are not installed by candidate opt-in against the reviewed
source catalog. Download the [configuration ZIP](../../assets/model-engine-standard.zip)
and follow Step 1 to verify it. Historical inputs remain separate from current
`matrix-configurations/` and `evaluation-profiles/` inputs.

## Check your result

The input model, snapshot, tokenizer and profile identity must remain consistent across selection, launch and routing.

Select a supported model/engine tuple before interpreting results. Keep direct-worker success separate from Gateway delivery, routing evidence, engine cache reuse, performance and release qualification. Historical PASS, FAIL and BLOCKED results retain their original artifact identities.

## Next steps and cleanup

Use the canonical deployment sequence rather than combining fragments from different engine/version pages. Drain before switching or deleting owned resources; retained result pages are evidence, not another deployment recipe. Read the [lab starting point](../model-engine-standard/select.md) if required values are missing. Use [cleanup and recovery](../model-engine-standard/lifecycle.md) when ending the run.

<!-- Previous section IDs: kept so old deep links redirect to the current page. -->
<div class="legacy-anchors" markdown>

- <span id="matrix-model-selection"></span>[matrix-model-selection](select.md#matrix-model-selection)
- <span id="matrix-registry-preparation"></span>[matrix-registry-preparation](prepare.md#matrix-registry-preparation)
- <span id="matrix-engine-launch"></span>[matrix-engine-launch](launch.md#matrix-engine-launch)
- <span id="matrix-rule-application"></span>[matrix-rule-application](configure.md#matrix-rule-application)
- <span id="matrix-request-verification"></span>[matrix-request-verification](verify.md#matrix-request-verification)
- <span id="matrix-lifecycle"></span>[matrix-lifecycle](lifecycle.md)
- <span id="matrix-results"></span>[matrix-results](results.md#matrix-results)
- <span id="1-versions-and-verification-scope"></span>[1-versions-and-verification-scope](select.md#versions-and-verification-scope)
- <span id="9-remaining-qualification-and-rerun-conditions"></span>[9-remaining-qualification-and-rerun-conditions](qualification-todo.md)
- <span id="five-model-rr-and-kv-exact-configuration-and-verification"></span>[five-model-rr-and-kv-exact-configuration-and-verification](matrix-manual.md)

</div>
