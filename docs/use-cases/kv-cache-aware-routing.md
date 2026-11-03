# KV Routing: Updated Locations

This page has been consolidated. Continue to the [current documentation](../concepts/kv-routing.md).

<!-- Previous section IDs: kept so old deep links redirect to the current page. -->
<div class="legacy-anchors" markdown>

- <span id="kv-cache-aware-routing"></span>[kv-cache-aware-routing](../concepts/kv-routing.md)
- <span id="1-what-it-is-and-where-it-sits"></span>[1-what-it-is-and-where-it-sits](../concepts/kv-routing.md)
- <span id="2-architecture-inventory-in-go-decision-in-c"></span>[2-architecture-inventory-in-go-decision-in-c](../concepts/kv-routing.md)
- <span id="3-what-exactly-is-synced-and-why-it-is-tiny"></span>[3-what-exactly-is-synced-and-why-it-is-tiny](../concepts/kv-routing.md)
- <span id="consistency-model"></span>[consistency-model](../concepts/kv-routing.md)
- <span id="4-end-to-end-call-flow"></span>[4-end-to-end-call-flow](../concepts/kv-routing.md)
- <span id="worked-example-two-prompts-end-to-end"></span>[worked-example-two-prompts-end-to-end](../concepts/kv-routing.md)
- <span id="5-the-vllm-block-hash-parity-contract"></span>[5-the-vllm-block-hash-parity-contract](../ai-gateway/engine-contracts.md)
- <span id="6-parity-preflight-inspect-what-is-actually-running"></span>[6-parity-preflight-inspect-what-is-actually-running](../ai-gateway/engine-contracts.md)
- <span id="61-the-parity-triad-as-an-operational-checklist"></span>[61-the-parity-triad-as-an-operational-checklist](../concepts/kv-routing.md)
- <span id="62-the-read-only-preflight-read-the-live-container-not-the-script"></span>[62-the-read-only-preflight-read-the-live-container-not-the-script](../concepts/kv-routing.md)
- <span id="63-tested-artifact-rule"></span>[63-tested-artifact-rule](../concepts/kv-routing.md)
- <span id="64-vllm-metric-families-the-collector-needs"></span>[64-vllm-metric-families-the-collector-needs](../concepts/kv-routing.md)
- <span id="65-loxilb-runtime-env-worth-setting-explicitly"></span>[65-loxilb-runtime-env-worth-setting-explicitly](../concepts/kv-routing.md)
- <span id="7-guard-ladder-miss-reasons"></span>[7-guard-ladder-miss-reasons](../operations/kv-routing-verification.md)
- <span id="8-configuration"></span>[8-configuration](model-engine-standard/matrix-manual.md)
- <span id="81-rest-the-load-balancer-rule"></span>[81-rest-the-load-balancer-rule](../concepts/kv-routing.md)
- <span id="82-environment-variables-loxilb-process"></span>[82-environment-variables-loxilb-process](../concepts/kv-routing.md)
- <span id="83-tokenizer-staging"></span>[83-tokenizer-staging](../concepts/kv-routing.md)
- <span id="84-vllm-side-must-match-the-rule"></span>[84-vllm-side-must-match-the-rule](../concepts/kv-routing.md)
- <span id="85-onboarding-a-new-model-one-model-per-rule"></span>[85-onboarding-a-new-model-one-model-per-rule](../concepts/kv-routing.md)
- <span id="9-verify-it-actually-fired-the-mandatory-post-config-check"></span>[9-verify-it-actually-fired-the-mandatory-post-config-check](../operations/kv-routing-verification.md)
- <span id="91-step-1-the-engagement-assertion-on-get-netloxv1metrics"></span>[91-step-1-the-engagement-assertion-on-get-netloxv1metrics](../concepts/kv-routing.md)
- <span id="92-step-2-inventory-check"></span>[92-step-2-inventory-check](../concepts/kv-routing.md)
- <span id="93-step-3-subscriber-count"></span>[93-step-3-subscriber-count](../concepts/kv-routing.md)
- <span id="94-step-4-publisher-side-sanity-on-the-engine-host"></span>[94-step-4-publisher-side-sanity-on-the-engine-host](../concepts/kv-routing.md)
- <span id="10-verify-inventory-metrics-reference"></span>[10-verify-inventory-metrics-reference](../operations/kv-routing-verification.md)
- <span id="101-inspect-the-live-inventory"></span>[101-inspect-the-live-inventory](../concepts/kv-routing.md)
- <span id="102-prometheus-metrics"></span>[102-prometheus-metrics](../concepts/kv-routing.md)
- <span id="103-healthy-warm-route-signature"></span>[103-healthy-warm-route-signature](../concepts/kv-routing.md)
- <span id="11-troubleshoot"></span>[11-troubleshoot](../operations/kv-routing-verification.md)
- <span id="12-known-limits"></span>[12-known-limits](../operations/kv-routing-verification.md)
- <span id="load-blind-argmax-capacity-weighted-blend"></span>[load-blind-argmax-capacity-weighted-blend](../concepts/kv-routing.md)
- <span id="13-advanced-ai-controller-experimental"></span>[13-advanced-ai-controller-experimental](advanced-cache-integrations.md)
- <span id="14-advanced-lmcache-tiered-cache"></span>[14-advanced-lmcache-tiered-cache](advanced-cache-integrations.md)
- <span id="related"></span>[related](../concepts/kv-routing.md)

</div>
