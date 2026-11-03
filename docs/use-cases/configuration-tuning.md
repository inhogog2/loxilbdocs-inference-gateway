# Configuration and Arguments

--8<-- "snippets/common/mutation-fragment-notice.md"

Every operator-facing knob for LoxiLB's AI routing hierarchy — REST rule fields, LoxiLB
environment variables, the vLLM-side matching contract — plus a tuning playbook. KV-specific field definitions and engine parity are
linked from their single reference pages; observability has its own verification guide.

Read [Routing Hierarchy](routing-hierarchy.md) first. Use the
[converged guide](model-engine-standard/matrix-manual.md) for actual onboarding
and [KV-Exact fields](../ai-gateway/kv-caching.md) for the strict binding controls.

## Before you start

Select the corresponding engine/version runbook before copying any setting.

**Focus of this page:** Use this reference to interpret flags and service fields, not to mix independent launch recipes.

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

## Walkthrough

### Configuration surface at a glance

The hierarchy is configured in a few distinct places; each ladder row maps to specific knobs:

| Layer | Where configured | Key knobs |
|---|---|---|
| Rule shape (P/D vs single-pool) | REST rule | `mode`, `pd_disagg_mode`, `ep_role`, `nixl_port` |
| Tier 0 stickiness | REST rule | `pd_session_ttl_sec` (P/D); `sel:3` / session headers (single-pool) |
| Tier 1 trie | REST rule | `pd_cache_aware_mode`, `pd_cache_threshold`, `pd_balance_abs_threshold` |
| Tier 1.5 KV-exact | REST rule + LoxiLB env + vLLM flags | `kvExactMode`, `kvZmqPort`, `kvHashAlgo`, `kvBlockSize`, `LLB_KV_NONE_HASH_SEED`, `LOXILB_KV_MAX_BLOCKS`; vLLM parity triad |
| Tier 1.5 blend law | LoxiLB env | `LOXILB_KV_LB_MODE`, `LOXILB_KV_MEAN_LOAD_FACTOR`, `LOXILB_KV_LOAD_PENALTY`, `LOXILB_KV_SPILL_RELIEF`, `LOXILB_KV_CAP_SUM_MILLI` |
| Admission gate | LoxiLB env | `LLB_PD_MAX_INFLIGHT_PER_EP`, `LLB_PD_QUEUE_DEPTH_PER_EP`, `LLB_PD_MAX_PARK_SEC`, `LLB_PD_MAX_TOTAL_INFLIGHT` |
| Single-pool cache affinity | REST rule | `sel:8/9/10`; current CHWBL constants are fixed in the proxy |
| Controller loop (optional) | LoxiLB env | `LOXILB_AI_CTRL_ADDR` |
| TLS posture | REST rule | `security`, `host`, cert staging |

!!! warning "Environment variables are read once at process start"
    Both the Go `LOXILB_*` family and the C `LLB_*` family are read at startup — changing any of
    them requires **recreating the LoxiLB container**. REST rules can be re-posted at runtime.

### REST rule fields

Endpoint: `POST http://192.0.2.254:11111/netlox/v1/config/loadbalancer`.

!!! warning "Field-casing trap (silent)"
    `pd_disagg_mode`, `pd_cache_aware_mode`, `pd_session_ttl_sec`, `pd_cache_threshold`,
    `pd_balance_abs_threshold`, `ep_role`, `nixl_port` are **snake_case**; `kvExactMode`,
    `kvZmqPort`, `kvHashAlgo`, `kvBlockSize`, `externalIP`, `targetPort` are
    **camelCase**. A wrong-cased field is silently dropped — the API does not error, the feature
    just never engages.

#### Service-level (`serviceArguments`)

Use the single [REST field reference](../ai-gateway/configuration-reference.md)
for types, defaults, allowed values and immutable controls. It owns
[core service fields](../ai-gateway/configuration-reference.md#1-core-service-fields),
[KV fields](../ai-gateway/configuration-reference.md#4-kv-cache-exact-routing),
[CHWBL controls](../ai-gateway/configuration-reference.md#5-chwbl-wrr-hash-tuning-knobs)
and [P/D fields](../ai-gateway/configuration-reference.md#6-prefill-decode-pd-disaggregation).
The tuning sections below explain trade-offs; they do not define a second schema.

#### Endpoint-level (`endpoints[]`)

Use [endpoint fields](../ai-gateway/configuration-reference.md#9-endpoints-endpoints)
and [health/probe fields](../ai-gateway/configuration-reference.md#10-health-probe-fields)
for the complete definitions. Match target ports and probe ports to the actual
engine listener. Role-tagged endpoints belong only to P/D; a converged Exact
pool has no prefill/decode roles. Preserve the exact model/host/VIP/port identity
when replacing or deleting a rule.

### LoxiLB process environment variables

Set with `docker run -e …`; all read once at startup.

#### Go control plane — Tier-1.5 blend, inventory, controller link

| Var | Default | Accepted | Effect |
|---|---|---|---|
| `LOXILB_KV_LB_MODE` | (unset → `hard`) | `off`\|`hard`\|`soft`\|`adaptive`\|`adaptive-soft` | Tier-1.5 selection law. Garbage → warn + `hard` |
| `LOXILB_KV_UNIFIED_MODE` | on | disable: `0/false/off/no` | Legacy toggle, consulted only when `LOXILB_KV_LB_MODE` is unset; disable ⇒ `off` (pure overlap-argmax) |
| `LOXILB_KV_MEAN_LOAD_FACTOR` | 175 (ε = 0.75) | int 100–1000 | Static ε for `hard` mode, as (1+ε)·100 |
| `LOXILB_KV_LOAD_PENALTY` | 32 | int 1–100000 | Static λ for `soft` mode |
| `LOXILB_KV_SPILL_RELIEF` | auto: mode 3 on; mode 1 off | on: `1/true/on/yes`; off: `0/false/off/no`; unset: auto | Hot-prefix pressure relief across the full healthy fleet. Explicit values override all services process-wide. |
| `LOXILB_KV_CAP_SUM_MILLI` | 0 (off) | positive int | Deployment Σcapacity (milli-units) for the capacity-normalized adaptive law; factor clamped [1/8, 8] |
| `LOXILB_KV_TLOAD_LOG` | off | `1` | Promote per-selection totalLoad diagnostics to Info |
| `LOXILB_KV_COLDSTART_SEED_N` | 16 | int ≥0; `0` disables | While a cold eligible endpoint exists, divert every Nth Tier-1.5 hit to rehydrate it. |
| `LOXILB_KV_COLDSTART_MIN_BLOCKS` | 16 | int ≥0; `0` means empty-only | Inventory below this block count is cold for seeding. |
| `LOXILB_KV_MAX_BLOCKS` | 1,000,000 | int 1000–100,000,000 | Per-endpoint inventory cap (FIFO eviction) |
| `LOXILB_AI_CTRL_ADDR` | unset (no controller) | `host:port` | Master gate for the optional external controller applier |
| `LOXILB_AI_CTRL_DECAY_WINDOW_SEC` | 30 | int >0 | Weight-influence decay window after staleness |

#### C data plane — Tier-1.5 parity, admission, timeouts

| Var | Default | Accepted | Effect |
|---|---|---|---|
| `LLB_KV_NONE_HASH_SEED` | Required for vLLM KV-exact; otherwise unset | 1–23 bytes for vLLM KV-exact | **Must equal vLLM's `PYTHONHASHSEED`**. Current Gateway main refuses vLLM `kvExactMode` rule creation with HTTP `412` when the value is unset, empty, or too long. |
| `LLB_KV_HASH_DEBUG` | off | `1` | Per-block hash forensic logging (testbed only) |
| `LLB_KV_LOADGUARD` | off | non-`0` | Hard load-imbalance pre-guard before Tier 1.5 |
| `LLB_PD_PREFILL_TIMEOUT_SEC` | 30 | int | Prefill-leg timeout. **Raise to ≥180 for long-context (32k) fleets** — the 30 s default times out most requests under load. Process-wide; a rule can override it with `pd_prefill_timeout_sec` |
| `LLB_PD_MAX_INFLIGHT_PER_EP` | 0 (off) | 0<n<100000 | Admission: per-endpoint in-flight prefill cap |
| `LLB_PD_QUEUE_DEPTH_PER_EP` | 0 (off) | n>0 (clamped 64) | Admission: park queue depth (hold-don't-drop) |
| `LLB_PD_MAX_PARK_SEC` | 0 (→ prefill timeout) | 0<n<100000 | Admission: parked-request reap deadline |
| `LLB_PD_MAX_TOTAL_INFLIGHT` | 0 (off) | n>0 | Admission: global valve — refuse new connections beyond this |
| `LLB_PD_ORIGIN_ERR_THRESHOLD` | 3 | int ≥0; `0` disables | Consecutive origin 5xx responses that open an enabled endpoint breaker. A 4xx neither advances nor resets this streak. |
| `LLB_KV_MIN_MATCH_TOKENS` | `16` | `0`–`4096`; `0` disables | Skip Exact scoring for shorter prompts |

### Engine parity and effective identity

KV-specific field defaults and immutable binding are maintained in
[KV-Exact Configuration Reference](../ai-gateway/kv-caching.md#configuration-fields).
Use [Engine Contracts](../ai-gateway/engine-contracts.md) for seed, hash, geometry,
rank ports and image coherence. SGLang has no vLLM seed contract; do not apply the
vLLM parity triad to another engine. Check actual arguments, relevant environment,
image digest and rule readback before each comparison.

#### Tested-artifact rule

Do not derive a public support matrix from example host versions. Record the immutable Gateway
and engine image identities plus OS, kernel, GPU, and driver used by your own acceptance run.
Promote only that tested tuple and retest after any member changes. Keep `--max-model-len`
identical across a pool.

### Capacity contrast for heterogeneous fleets

The P/D capacity-aware selector-9 scorer is not currently a deployable tuning target because its
activation gate does not reliably follow the configured selector. The procedure below prepares a
heterogeneous test fleet for a future fixed release; it does **not** prove capacity-aware routing in
the current release.

On a uniform fleet every endpoint has the same `num_gpu_blocks`, so even a corrected capacity term
would be constant. To prepare a discriminating post-fix test, synthesize a spread.

#### Synthesize a KV-capacity spread with `gpu_mem_util`

The KV pool size a vLLM instance exposes scales with `--gpu-memory-utilization`. Launch
fleet members at deliberately different fractions to fan out `num_gpu_blocks`:

| `--gpu-memory-utilization` | Relative KV pool | Role in the contrast |
|---|---|---|
| `0.35` | small | low-capacity endpoint |
| `0.6` | medium | mid-capacity endpoint |
| `0.9` | large | high-capacity endpoint |

Across that 0.35 → 0.9 range you get roughly a **4–5× spread** in `num_gpu_blocks`. After the
activation blocker is fixed, use a spread of at least **≥ 4×** so capacity differences are large
enough to distinguish from normal placement noise.

!!! warning "Do not ship a synthesized spread"
    Under-utilizing GPU memory on purpose is a *test* posture to make capacity routing
    observable — it wastes KV capacity. Return every endpoint to its real
    `gpu_mem_util` (typically `0.9`) for production.

#### Verify the spread landed

Read the live block count each engine actually allocated — do not assume the fraction
mapped cleanly:

```bash
# Per endpoint: the number of GPU KV blocks vLLM allocated
curl -s "http://<endpoint-ip>:8100/metrics" | grep 'vllm:cache_config_info'
```

Read allocated capacity as an observation; verify placement separately.

### Per-layer enablement matrix

What turns each layer on, and the *fastest* check that it engaged (metrics on
`GET http://192.0.2.254:11111/netlox/v1/metrics` unless noted):

| Layer | Enable | Verify |
|---|---|---|
| P/D ladder | rule: `mode:4`, `pd_disagg_mode:true`, ≥1 `ep_role:1` + ≥1 `ep_role:2` | `loxilb_ai_pd_requests_total` advances |
| Tier 0 | on by default under P/D (`pd_session_ttl_sec`) | `loxilb_ai_pd_session_hits_total` advances on repeat `X-Conversation-Id` |
| Tier 1 | rule: `pd_cache_aware_mode:true` | repeat-prefix requests pin; imbalance bypass visible in logs |
| Tier 1.5 | rule: `kvExactMode:1` + triad + tokenizer | `loxilb_pd_kv_tier15_hits_total{ep_idx}` advances; `loxilb_pd_kv_blocks` > 0; `loxilb_kv_subscriber_connected` = 1 |
| Blend law | `LOXILB_KV_LB_MODE` (default `hard`) | `loxilb_pd_kv_tier15_spills_total` under hot-prefix load |
| Cold recovery | default on; tune with `LOXILB_KV_COLDSTART_SEED_N` and `_MIN_BLOCKS` | `loxilb_pd_kv_tier15_cold_seeds_total` advances only while an eligible endpoint is cold |
| Admission | `LLB_PD_MAX_INFLIGHT_PER_EP` > 0 | `loxilb_pd_admission_queued_total` / `loxilb_pd_admission_shed_total` |
| Single-pool affinity | rule: `sel:8` or `sel:10` | compare repeated-prefix placement and actual endpoint load |

### Tuning playbook

#### Choosing the Tier-1.5 mode

| Situation | Recommendation |
|---|---|
| Default / unknown workload | `hard` (the current default, ε = 0.75) — the blend that bounds affinity by load |
| Load varies widely across the day | `adaptive` — set `LOXILB_KV_CAP_SUM_MILLI` if your fleet's Σcapacity differs from the calibration fleet |
| Latency-tolerant batch, cache hit-rate is everything | `hard` with a **higher** `LOXILB_KV_MEAN_LOAD_FACTOR` (e.g. 300 ⇒ ε = 2.0) — affinity-preserving, spills late |
| Strict per-request SLA, spiky arrivals | `hard` with a **lower** factor (tighter cap, earlier spill), or `soft` with λ raised above 32 to price queueing more heavily |
| Debug / A-B baseline | `off` — pure overlap-argmax |

The best ε and λ **increase with load**. If you must run static, tune for your *peak*; if you
can, run `adaptive` and let the law move.

#### Tier-1 thresholds (when running without KV-exact)

- `pd_cache_threshold` 20 is conservative; RAG workloads with long shared preambles can drop to
  10–15 for more affinity. Raise it if affinity wins go to barely-matching prefixes.
- `pd_balance_abs_threshold` 3 is tuned for ~4-endpoint pools; scale roughly with pool size (it
  is an absolute connection-count delta, not a ratio).

#### Warmup, timeouts, session TTL

- `LLB_PD_PREFILL_TIMEOUT_SEC`: size to your p99.9 prefill duration. Use completed-request and timeout observations from the selected workload; no
  universal GPU-specific value is prescribed.
- `pd_session_ttl_sec`: match your conversational think-time. Too long pins conversations to
  workers whose cache has moved on; too short forfeits the multi-turn affinity win.

#### Admission (opt-in — protection, not throughput)

Enable only with a latency SLO to protect. Set `LLB_PD_MAX_INFLIGHT_PER_EP` near the per-endpoint
concurrency at which prefill queue-divergence begins, `LLB_PD_QUEUE_DEPTH_PER_EP` 8–16, and
`LLB_PD_MAX_PARK_SEC` below your client timeout. Watch `loxilb_pd_admission_shed_total` — a
steadily climbing shed count means the cap is below fleet capacity. FIFO admission trades
saturated-rate goodput for tail-latency control; keep it off unless you need the tail bound.

#### Inventory sizing

`LOXILB_KV_MAX_BLOCKS` = 1M blocks represents about 8 MB of raw 64-bit hashes alone. The Go
set, index, and ordering list add substantial overhead, so measure process memory with your
real inventory. Alert on `loxilb_kv_inv_cap_evictions_total` > 0 —
nonzero means an endpoint's publisher outran the cap and overlap scoring for it is degraded
(routing stays correct; only the optimization decays).

### Observability quick reference

Use [KV Routing Verification](../operations/kv-routing-verification.md) for the
single engagement gate, inventory/subscriber diagnostics, metric meanings and
independent receipt checks. [P/D lifecycle outcomes](../ai-gateway/pd-disaggregation.md#lifecycle-outcome-contract)
are separate from cache-hit decisions. Tuning values require effective-state
and completed-traffic evidence before performance interpretation.

#### Three silent-degradation patterns to alert on

1. **Silent fallback (hash-contract mismatch):** `tier15_hits` flat + `misses{reason="no_worker"}`
   climbing + `loxilb_pd_kv_blocks` **non-empty** ⇒ a broken parity leg (seed / block size / algo /
   tokenizer / vLLM version).
2. **Silent fallback (no inventory):** `loxilb_pd_kv_blocks` = 0 + `kv_subscriber_connected` = 1 ⇒ vLLM not
   publishing (missing `--kv-events-config`, wrong bind, or a decode endpoint mistagged `ep_role:1`).

### Operational cautions

- **Never hard-kill the LoxiLB container** on a `--net=host` deployment: orphaned XDP hooks can
  wedge the host's networking until reboot. Always `docker stop -t 30`.
- **A LoxiLB restart drops runtime-POSTed LB rules** — re-register rules after any recreate
  (keep your rule JSON in a script).
- The HTTPS cert is loaded **once per container lifetime**; rotate via the REST cert API or a
  container recreate, and remember HTTPS rules are host-keyed on delete.
- **All `LOXILB_*` / `LLB_*` env changes need a container recreate** — plan them together with
  rule re-registration.
- When results look wrong, **check the client/harness first** (an unset parity leg or a non-JSON
  request body is the most common "routing bug"), then the metrics above, then the config.

For the conceptual ladder and the selection-law math, see [Routing Hierarchy](routing-hierarchy.md);
for the KV block-hash contract, see [KV-Cache Routing](../ai-gateway/kv-caching.md).

## Check your result

Read back configured and effective values; a valid field does not prove serving or performance.

Select a supported model/engine tuple before interpreting results. Keep direct-worker success separate from Gateway delivery, routing evidence, engine cache reuse, performance and release qualification. Historical PASS, FAIL and BLOCKED results retain their original artifact identities.

## Next steps and cleanup

Use the canonical deployment sequence rather than combining fragments from different engine/version pages. Drain before switching or deleting owned resources; retained result pages are evidence, not another deployment recipe. Read the [lab starting point](model-engine-standard/select.md) if required values are missing. Use [cleanup and recovery](model-engine-standard/lifecycle.md) when ending the run.

<!-- Previous section IDs: kept so old deep links redirect to the current page. -->
<div class="legacy-anchors" markdown>

- <span id="configuration-tuning"></span>[configuration-tuning](../ai-gateway/engine-contracts.md)
- <span id="vllm-side-the-parity-triad"></span>[vllm-side-the-parity-triad](../ai-gateway/engine-contracts.md)
- <span id="environment-parity-preflight"></span>[environment-parity-preflight](../ai-gateway/engine-contracts.md)
- <span id="the-parity-triad"></span>[the-parity-triad](../ai-gateway/engine-contracts.md)
- <span id="read-only-preflight-inspect-the-running-container"></span>[read-only-preflight-inspect-the-running-container](../ai-gateway/engine-contracts.md)
- <span id="loxilb-runtime-environment-parity-and-admission-relevant"></span>[loxilb-runtime-environment-parity-and-admission-relevant](../ai-gateway/engine-contracts.md)

</div>
