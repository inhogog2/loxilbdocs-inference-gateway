# Existing profiles: prepare, launch, and verify

<!-- example-status-default: illustrative-only -->

Use this page to bring up **one model and one engine on two allocated workers**, first with round robin (RR), then optionally with KV Exact. Start with the [model results and permitted modes](existing-profiles.md). Run **either** the vLLM **or** the SGLang launch block, never both on the same ports.

## Before you start

Choose a profile with an available runtime recipe and a dedicated empty Gateway.

**Focus of this page:** Run the two-worker launch guide on the Gateway host and workers A/B.

## Topology and execution locations

--8<-- "snippets/use-cases/topology/existing-profiles.md"

This is the separate existing-profile campaign: two converged worker hosts, one pre-existing dedicated Gateway, and an independent receipt proxy on each worker. Native inference uses 18300; receipt forwarding uses 18301. These profile settings and recorded identities must not be replaced by the five-model guide's three-worker variables.

| Where | What happens here |
|---|---|
| Operator terminal | Select the version tuple, private run directory, model snapshot and profiles. |
| Gateway host / namespace | Start the dedicated Gateway; apply and read back only the selected service. |
| Each worker host | Launch the chosen engine and prove direct inference before Gateway traffic. |
| Client | Send the same request through the Gateway and retain its HTTP/SSE observations. |
| Independent evidence | Correlate worker requests/receipts with the selected rule and request identifiers. |

## Walkthrough

### Before you begin {#before-you-begin}

| Machine / terminal | Responsibility | Required tools |
|---|---|---|
| Gateway host | Approved isolated Gateway, rule management, optional Exact metadata | Bash 4+, Python 3, curl, jq, sha256sum, Docker; `hf` only for Exact artifacts |
| Worker A and worker B | Identical model snapshots, selected native engine, receipt collector | Linux x86_64, Bash 4+, Python 3, curl, jq, sha256sum, `hf`, Docker with NVIDIA GPU access |
| Separate terminal on each worker | Keep the receipt collector in the foreground | Same saved shell settings and receipt directory |

Allocate GPUs matching the [recorded hardware](existing-profiles.md#recorded-hardware). This is a short English text-chat check, not language-task accuracy, multimodal operation, maximum context, or production capacity qualification. The package excludes weights, tokenizer/template bytes, and the Gateway binary. The tested Gateway binary's source commit was not established: use an approved compatible deployment and record its identity; the package alone cannot recreate that binary.

[Install the Gateway](../../getting-started/installation.md) and configure its management authentication before this procedure. Use an **empty dedicated Gateway**, reachable from your management shell, with Prometheus collection enabled. Its data listener must be reachable from clients and its native/event ports from the relevant workers. No existing service rule should share this test VIP/port. Do not run these examples against a production rule set.

| Value to replace | Example only | Meaning |
|---|---|---|
| `PROFILE` |`olmo2-0425-1b-v1`|Identity selected from the results guide; not the request's model name|
| `ENGINE` |`vllm`|Choose `vllm` or `sglang`; each has different settings|
| `API` |`http://127.0.0.1:11111/netlox/v1`|Management URL from the Gateway host; use your approved HTTPS URL/CA where applicable|
| `VIP` |`192.0.2.10`|Assigned data-plane address reachable by the client; these documentation addresses are not real allocations|
| `WORKER_A`, `WORKER_B` |`192.0.2.21`, `192.0.2.22`|Allocated workers; native HTTP 18300, receipt HTTP 18301, Exact inventory TCP 5557|
| `GATEWAY_CONTAINER` |`existing-profile-gateway`|Your pre-existing dedicated Gateway's actual container name|
| `CURL_CONFIG` |A private local curl configuration file|Management authentication and CA options; keep credentials out of commands, source control, and the package|

The examples assume directly reachable Linux host networking on each worker. Prepare the assigned VIP/network through your approved deployment procedure; a JSON rule alone does not prove the client can reach it. Container GPU access, firewall/route reachability, and free ports are prerequisites.

### 1. Verify the package and save local shell settings {#select-and-save}

On **each participating machine**, use a new working directory outside any existing extraction. Save the [archive](../../assets/existing-profiles-evaluation.tgz) and [checksum](../../assets/existing-profiles-evaluation.tgz.sha256) there. The following uses a dedicated directory under your home; choose another path consistently if needed. Do not download models or write run outputs inside the immutable package. A Git clone or GitHub source ZIP omits raw results and token probes; use the evaluation archive for every launch and result-verification step. Before this documentation revision is deployed, use the archive/checksum links in the PR Files view instead of the not-yet-published Pages URLs.

**Step 1 — Download and verify the package, then select a profile**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
set -e
umask 077
export WORK="$HOME/igw-existing-profile-evaluation"
mkdir -p "$WORK"
cd "$WORK" || exit 1
# Use the same published documentation version for both files.
export ASSET_BASE='https://loxilb-io.github.io/loxilbdocs-inference-gateway/latest/assets'
curl --fail --location --connect-timeout 10 --max-time 180 --output existing-profiles-evaluation.tgz "$ASSET_BASE/existing-profiles-evaluation.tgz"
curl --fail --location --connect-timeout 10 --max-time 30 --output existing-profiles-evaluation.tgz.sha256 "$ASSET_BASE/existing-profiles-evaluation.tgz.sha256"
sha256sum -c existing-profiles-evaluation.tgz.sha256 || exit 1
test ! -e existing-profiles || exit 1
tar -xzf existing-profiles-evaluation.tgz
export PACKAGE="$WORK/existing-profiles"
(cd "$PACKAGE" && sha256sum -c SHA256SUMS) || exit 1
export PROFILE=olmo2-0425-1b-v1
export ENGINE=vllm
jq -e --arg p "$PROFILE" --arg e "$ENGINE"   'any(.[]; .profileId==$p and .engine==$e and .settings!=null)' "$PACKAGE/recipes.json" || exit 1
source "$PACKAGE/models/$PROFILE.env" || exit 1
source "$PACKAGE/settings/$PROFILE-$ENGINE.env" || exit 1
export API='http://127.0.0.1:11111/netlox/v1'
export VIP=192.0.2.10
export WORKER_A=192.0.2.21
export WORKER_B=192.0.2.22
export GATEWAY_CONTAINER=existing-profile-gateway
```

**Step 2 — Save the run settings to `operator.env`**

Use the namespace/container shown by the command. Keep the response file and HTTP status separate; the next check explains the expected result.

```bash
export CURL_CONFIG="$WORK/management.curl"
if test ! -e "$CURL_CONFIG"; then install -m 600 /dev/null "$CURL_CONFIG"; fi
case "$ENGINE" in
  vllm) export ENGINE_IMAGE='vllm/vllm-openai@sha256:a4a4c0437bf7240089da5f08aa370c4aee17ae5290f7a3b468825ee26c4c3a6b' ;;
  sglang) export ENGINE_IMAGE='lmsysorg/sglang@sha256:37bbbd3444732a464bbc68dee4fb0164e0ce9e18e2f027f3fc967f1152d3c262' ;;
  *) exit 1 ;;
esac
export MODEL_DIR="$WORK/model-snapshots/$PROFILE/$REV"
RUN="$WORK/runs/$PROFILE-$ENGINE-$(date -u +%Y%m%dT%H%M%S)-$RANDOM"
export RUN
RID_PREFIX="existing-$(date -u +%Y%m%dT%H%M%S)-$RANDOM"
export RID_PREFIX
MODEL_ESCAPED=$(jq -rn --arg value "$MODEL" '$value|@uri')
export MODEL_ESCAPED
mkdir -p "$RUN"
declare -p WORK PACKAGE PROFILE ENGINE MODEL REV TOKENIZER_SHA TEMPLATE_SHA TEMPLATE_SOURCE   API VIP WORKER_A WORKER_B GATEWAY_CONTAINER CURL_CONFIG ENGINE_IMAGE MODEL_DIR RUN RID_PREFIX MODEL_ESCAPED   > "$WORK/operator.env"
cd "$RUN" || exit 1
```

Expected: archive/files report `OK`; the recipe check prints `true`; `operator.env` contains your selected model/engine and host-local paths. Configure `management.curl` using your approved [management authentication](../../security/management-api-authentication.md) and CA settings. An empty file is usable only where the dedicated listener's approved policy permits it. Use `--config "$CURL_CONFIG"` on **every management request** below; inference requests have their own deployment authentication, if enabled.

For a **new terminal**, restore that machine's settings before continuing:

```bash
set -e
export WORK="$HOME/igw-existing-profile-evaluation"
source "$WORK/operator.env" || exit 1
source "$PACKAGE/settings/$PROFILE-$ENGINE.env" || exit 1
cd "$RUN" || exit 1
printf 'profile=%s engine=%s model=%s output=%s\n' "$PROFILE" "$ENGINE" "$MODEL" "$MAX_OUTPUT"
```

Keep Gateway-host and worker paths local to each machine. Repeat Step 1 there rather than copying an environment file containing another host's paths. To change model/engine later, finish cleanup first and start a new run. Gemma 3 and Llama 3.2 have no runtime recipe and fail the selection gate; do not retry their access during this campaign.

### 2. Prepare model files on both workers {#worker-artifacts}

**Workers only; skip on the Gateway host.** Verify free ports 18300/18301/5557, disk headroom, Docker GPU access, and the selected snapshot. Authenticate interactively with HF only if the selected, non-deferred model requires existing authorized access. Do not paste tokens into these commands or logs.

```bash
nvidia-smi
ss -lntp
docker ps --format '{{.Names}} {{.Status}}'
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR" "$(docker info --format '{{.DockerRootDir}}')"
test -f "$PACKAGE/weights/$PROFILE.sha256" || exit 1
mapfile -t MODEL_FILES < <(cut -d ' ' -f3- "$PACKAGE/weights/$PROFILE.source-index")
hf download "$MODEL" "${MODEL_FILES[@]}" --revision "$REV" --local-dir "$MODEL_DIR"
(cd "$MODEL_DIR" && sha256sum -c "$PACKAGE/weights/$PROFILE.sha256") || exit 1
docker pull "$ENGINE_IMAGE"
docker image inspect "$ENGINE_IMAGE" --format '{{.Id}} {{json .RepoDigests}}'
docker run --rm --gpus all --entrypoint nvidia-smi "$ENGINE_IMAGE"
```

All files must verify, and the diagnostic container must see the allocated GPU. Preserve the exact image reference; if it cannot be obtained, stop and resolve artifact access rather than silently substituting a tag. Allow extraction and runtime headroom beyond the indexed weight/image sizes. Preserve symlink targets if using an existing HF cache.

### 3. Launch the selected native engine {#native-launch}

Run **one** of the following blocks on **both** workers. `MODEL` is the served repository name; `PROFILE` is registry metadata. Do not start the second engine on the same ports. Each fixed container name must be absent before creation.

| Variable | Unit / recorded value | Meaning |
|---|---|---|
| `CONTEXT` |tokens; 4096|Input plus reasoning/final output; not the model's official maximum|
| `MAX_OUTPUT` |tokens; 512, 1024, or 1536|Request budget for the selected functional case; not a guaranteed final-answer length|
| `MAX_SEQS` |requests; 2 or 4|Engine scheduling cap; not client concurrency|
| `MEMORY_FRACTION` |fraction; recipe-specific|Engine memory budget, not weights-only or per-request allocation|
| `BATCHED_TOKENS` |tokens; 4096|vLLM per-iteration budget or SG chunked-prefill size, not a second context limit|
| `NATIVE_MEMORY_ARGS` |Docker host RAM array|Recorded `--memory 40g` or empty; distinct from GPU fraction|
| Model argument/environment arrays |literal per-model values|Preserve language-only, attention, reasoning parser, and state-layout options|

**vLLM only:**

```bash
source "$PACKAGE/settings/$PROFILE-vllm.env" || exit 1
test "$ENGINE" = vllm || exit 1
docker pull "$ENGINE_IMAGE"
docker image inspect "$ENGINE_IMAGE" --format '{{.Id}} {{json .RepoDigests}}'
docker run -d --name existing-profile-vllm --label igw.qa=existing-profile-evaluation \
  --gpus all "${NATIVE_MEMORY_ARGS[@]}" --network host --ipc host --shm-size 8g \
  -e HF_HUB_OFFLINE=1 -e HF_MODULES_CACHE=/tmp/hf_modules \
  -e PYTHONHASHSEED=0 -e VLLM_KV_EVENTS_USE_INT_BLOCK_HASHES=1 \
  "${VLLM_MODEL_ENVS[@]}" -v "$MODEL_DIR:/qa/model:ro" "$ENGINE_IMAGE" \
  --model /qa/model --revision "$REV" --tokenizer-revision "$REV" \
  --served-model-name "$MODEL" --host 0.0.0.0 --port 18300 \
  --dtype auto --max-model-len "$CONTEXT" --max-num-seqs "$MAX_SEQS" \
  --max-num-batched-tokens "$BATCHED_TOKENS" --gpu-memory-utilization "$MEMORY_FRACTION" \
  --enforce-eager --enable-prefix-caching --prefix-caching-hash-algo sha256_cbor \
  --block-size 16 --prefix-match-unit 16 \
  --kv-events-config '{"enable_kv_cache_events":true,"publisher":"zmq","endpoint":"tcp://*:5557","topic":""}' \
  "${VLLM_MODEL_ARGS[@]}"
```

**SGLang only:**

```bash
source "$PACKAGE/settings/$PROFILE-sglang.env" || exit 1
test "$ENGINE" = sglang || exit 1
docker pull "$ENGINE_IMAGE"
docker image inspect "$ENGINE_IMAGE" --format '{{.Id}} {{json .RepoDigests}}'
docker run -d --name existing-profile-sglang --label igw.qa=existing-profile-evaluation \
  --gpus all "${NATIVE_MEMORY_ARGS[@]}" --network host --ipc host --shm-size 8g \
  -e HF_HUB_OFFLINE=1 -e HF_MODULES_CACHE=/tmp/hf_modules -e PYTHONHASHSEED=0 \
  -v "$MODEL_DIR:/qa/model:ro" --entrypoint python3 "$ENGINE_IMAGE" -m sglang.launch_server \
  --model-path /qa/model --revision "$REV" --served-model-name "$MODEL" \
  --host 0.0.0.0 --port 18300 --dtype auto --context-length "$CONTEXT" \
  --mem-fraction-static "$MEMORY_FRACTION" --max-running-requests "$MAX_SEQS" \
  --chunked-prefill-size "$BATCHED_TOKENS" --page-size 16 --disable-cuda-graph \
  --enable-metrics --kv-events-config '{"publisher":"zmq","endpoint":"tcp://*:5557"}' \
  "${SGLANG_MODEL_ARGS[@]}"
```

Gemma 4, Ministral, and Qwen text-only recipes retain `--language-model-only`. EXAONE retains its SG attention backend; GPT-OSS SG retains `--reasoning-parser gpt-oss`. Preserve local model paths and the pinned revision. Do not edit tokenizer/template bytes or substitute another quantization. Initial OLMo launches had no host RAM limit; adding one is a changed condition requiring requalification.

**Each worker:** check its selected container, readiness, and served name:

```bash
export ENGINE_CONTAINER="existing-profile-$ENGINE"
docker logs --tail 100 "$ENGINE_CONTAINER"
test "$(docker inspect "$ENGINE_CONTAINER" --format '{{.State.Running}}')" = true || exit 1
curl --fail-with-body --connect-timeout 5 --max-time 30 http://127.0.0.1:18300/health
curl --fail-with-body --connect-timeout 5 --max-time 30 http://127.0.0.1:18300/v1/models > native-models.json
jq -e --arg m "$MODEL" 'any(.data[]; .id==$m)' native-models.json || exit 1
```

Wait for native startup completion before testing. Running is not readiness. A missing model, failed health request, or startup exception stops this procedure; preserve the logs and use the [model-specific failure notes](existing-profiles.md#model-specific-settings-failures-and-limitations).

### 4. Start receipt collectors and check direct answers {#receipt-collectors}

Open a **second terminal on each worker**, restore its `operator.env` and selected settings, and choose that worker's address. Use `WORKER_A` on A and `WORKER_B` on B. This foreground process must remain running while traffic is tested.

```bash
export WORKER_IP="${WORKER_A:?Restore operator.env first}"
export RECEIPTS="$RUN/receipts"
test ! -e "$RECEIPTS" || exit 1
printf '%s\n' "$RECEIPTS" > "$RUN/receipt-directory.txt"
python3 "$PACKAGE/receipt-proxy.py" --bind "$WORKER_IP" --port 18301   --upstream-port 18300 --directory "$RECEIPTS" || { rc=$?; test "$rc" = 130 || exit "$rc"; }
```

The collector forwards to native HTTP 18300 and records body bytes/hashes independently. It does not hash all HTTP headers/TCP framing and is not a production component. Its upstream timeout is 180 seconds; long-context/time-to-first-token tests need separate qualification.

**Gateway/management shell:** restore its selected settings, create the request, and save both direct JSON and SSE responses. Test A, then repeat with `WORKER_B` and different request IDs/output filenames.

```bash
jq -n --arg model "$MODEL" --argjson maximum "$MAX_OUTPUT"   '{model:$model,messages:[{role:"user",content:"Explain in one short English sentence why clean drinking water protects human health."}],temperature:0,max_tokens:$maximum}' > request.json
curl --fail-with-body --connect-timeout 5 --max-time 180 -o native-json.body   -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-native-json"   --data-binary @request.json "http://$WORKER_A:18301/v1/chat/completions"
jq -e '.usage.prompt_tokens>0 and .usage.completion_tokens>0 and .choices[0].finish_reason=="stop"' native-json.body || exit 1
jq -r '.choices[0].message.content' native-json.body
jq '. + {stream:true,stream_options:{include_usage:true}}' request.json > request-sse.json
curl --fail-with-body --connect-timeout 5 --max-time 180 -N -o native-sse.body   -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-native-sse"   --data-binary @request-sse.json "http://$WORKER_A:18301/v1/chat/completions"
awk '/^data: \[DONE\]\r?$/{n++} END{print n+0; exit(n!=1)}' native-sse.body
sed -n 's/^data: *//p' native-sse.body | sed '/^\[DONE\]\r*$/d' | jq -s   'map(.choices[]?.delta.content // "") | join("")'
```

Require readable final content, positive prompt/completion usage, normal `stop`, exactly one SSE `[DONE]`, and matching native/client response hashes. The jq/awk checks alone do not prove readable final content or close reasoning. Inspect the printed final answer. R1 requires `</think>` plus a final answer; Qwen/Granite require closure of prefilled reasoning or separated reasoning plus final content. `length`, empty finals, exposed controls, or unclosed reasoning fail even with HTTP200. Preserve failures rather than stripping markers or increasing budgets without a separate controlled test.

### 5. Prepare the Gateway for your routing mode {#gateway-preparation}

**RR:** skip the entire Exact-artifact subsection and continue to the Gateway readiness checks below. `ENGINE` and `API` were already defined in Step 1. No model-profile discovery or Exact status call is needed for RR.

**Exact only:** confirm an Exact rule exists for your selected profile/engine before downloading metadata. On the Gateway host, prepare a new engine-specific registry. This host needs no GPU weights.

```bash
test -f "$PACKAGE/rules/$PROFILE-$ENGINE-exact.json" || exit 1
export GATEWAY_METADATA="$WORK/gateway-metadata/$PROFILE/$REV"
export QA_REGISTRY="$WORK/registry-$PROFILE-$ENGINE"
export QA_TOKENIZERS="$WORK/tokenizers-$PROFILE-$ENGINE"
test ! -e "$QA_REGISTRY" || exit 1
test ! -e "$QA_TOKENIZERS" || exit 1
mkdir -p "$GATEWAY_METADATA"
hf download "$MODEL" tokenizer.json tokenizer_config.json --revision "$REV" --local-dir "$GATEWAY_METADATA"
install -d -m 700 "$QA_REGISTRY/artifacts/sha256" "$QA_REGISTRY/manifests" "$QA_REGISTRY/probefixtures"
cp "$PACKAGE/registry-$ENGINE/$PROFILE.yaml" "$QA_REGISTRY/$PROFILE.yaml"
cp "$PACKAGE/registry-$ENGINE/manifests/$PROFILE.yaml" "$QA_REGISTRY/manifests/$PROFILE.yaml"
cp -R "$PACKAGE/registry-$ENGINE/probefixtures/$PROFILE" "$QA_REGISTRY/probefixtures/$PROFILE"
cp "$GATEWAY_METADATA/tokenizer.json" "$QA_REGISTRY/artifacts/sha256/$TOKENIZER_SHA"
if test "$TEMPLATE_SOURCE" = chat_template.jinja; then
  hf download "$MODEL" chat_template.jinja --revision "$REV" --local-dir "$GATEWAY_METADATA"
  cp "$GATEWAY_METADATA/chat_template.jinja" "$QA_REGISTRY/artifacts/sha256/$TEMPLATE_SHA"
elif test "$TEMPLATE_SOURCE" = tokenizer_config.json:chat_template; then
  jq -j '.chat_template' "$GATEWAY_METADATA/tokenizer_config.json" > "$QA_REGISTRY/artifacts/sha256/$TEMPLATE_SHA"
else
  echo 'No verified template preparation path for this profile'; exit 1
fi
printf '%s  %s\n' "$TOKENIZER_SHA" "$QA_REGISTRY/artifacts/sha256/$TOKENIZER_SHA"   "$TEMPLATE_SHA" "$QA_REGISTRY/artifacts/sha256/$TEMPLATE_SHA" | sha256sum -c - || exit 1
MODEL_DIRECTORY="${MODEL/\//__}"
install -d -m 700 "$QA_TOKENIZERS/$MODEL_DIRECTORY"
install -m 644 "$GATEWAY_METADATA/tokenizer.json" "$QA_TOKENIZERS/$MODEL_DIRECTORY/tokenizer.json"
sudo chown -R root:root "$QA_REGISTRY" "$QA_TOKENIZERS"
```

Expected: both artifact hashes report `OK`. The template-source branch chooses exactly one path; do not execute both and overwrite the artifact. Original multilingual probe strings/expected IDs must remain unchanged.

Before starting or recreating **your dedicated approved Gateway**, add the following bindings/environment to its deployment definition, retaining its approved authentication, network, config, and audit settings. Docker mounts cannot be added by `docker restart`. If it already has the correct binds, do not recreate it.

| Host value | Container target / setting | Expected |
|---|---|---|
| `QA_REGISTRY` |`/etc/loxilb/kvprofiles`, read-only|Contains selected profile, manifest, probes, and artifact tree|
| `QA_TOKENIZERS` |`/etc/loxilb/tokenizers`, read-only|Contains `MODEL_DIRECTORY/tokenizer.json`|
| vLLM Gateway environment |`LLB_KV_NONE_HASH_SEED=0`|Recorded vLLM hash-seed prerequisite; no need to dump other environment values|
| Owned writable audit directory |Your configured audit target|Root-owned mode 0700; existing audit files preserved|

Use the [Gateway installation procedure](../../getting-started/installation.md#run-the-gateway-container) with these additions; record the chosen Gateway image/binary identity. The original campaign used a separately mounted binary, so a generic release image is not an asserted byte-identical replay. There is no documented registry-reload REST command in this procedure. Prepare the registry before startup and use the discovery/readback gates; an engine switch needs a separate correctly prepared Gateway or a drained deployment replacement, not merely a different worker image.

**Gateway readiness, both modes:**

```bash
curl --config "$CURL_CONFIG" --fail-with-body "$API/config/loadbalancer/all" > before-evaluation.json
jq -e '.lbAttr == []' before-evaluation.json || exit 1
curl --config "$CURL_CONFIG" --fail-with-body "$API/metrics" > gateway-metrics-ready.txt
```

An existing rule, unavailable API, or unavailable metrics stops the test. Preserve that state rather than deleting unrelated rules. Resolve network/authentication or enable metrics in the approved deployment first.

**Exact only:** verify the expected published profile. A successful empty selection is not sufficient; `jq -e` must succeed.

```bash
curl --config "$CURL_CONFIG" --fail-with-body "$API/config/ai/model-profiles" > published-profiles.json
jq -e --arg p "$PROFILE" --arg m "$MODEL" --arg t "$TOKENIZER_SHA" --arg h "$TEMPLATE_SHA"   'any(.profiles[]; .profileId==$p and .baseModel==$m and .tokenizerSha256==$t and .templateSha256==$h)'   published-profiles.json || exit 1
```

### 6. Create one rule and check its effective state {#apply-routing}

**Gateway shell:** start with `ROUTING=rr`. Exact is a separate run after the RR rule has been deleted and its absence checked. `rules/` contains only permitted modes; a missing file is a stop condition, not a reason to copy another model's rule.

```bash
export ROUTING=rr
test -f "$PACKAGE/rules/$PROFILE-$ENGINE-$ROUTING.json" || exit 1
jq -e '.endpoints|length==2' "$PACKAGE/rules/$PROFILE-$ENGINE-$ROUTING.json" || exit 1
jq --arg vip "$VIP" --arg a "$WORKER_A" --arg b "$WORKER_B"   '.serviceArguments.externalIP=$vip | .serviceArguments.host=$vip |
   .endpoints[0].endpointIP=$a | .endpoints[1].endpointIP=$b'   "$PACKAGE/rules/$PROFILE-$ENGINE-$ROUTING.json" > rule.json
jq . rule.json
curl --config "$CURL_CONFIG" --fail-with-body -H 'Content-Type: application/json'   --data-binary @rule.json "$API/config/loadbalancer"
curl --config "$CURL_CONFIG" --fail-with-body "$API/config/loadbalancer/all" > effective-rules.json
jq -e --arg m "$MODEL" --arg vip "$VIP"   '[.lbAttr[]|select(.serviceArguments.model_name==$m and .serviceArguments.externalIP==$vip and .serviceArguments.port==28300)]|length==1'   effective-rules.json || exit 1
```

Check the selected model, mode, both endpoint addresses/ports, and weights against `rule.json`. RR uses fullproxy `mode:4`, `sel:0`, `pd_disagg_mode:false`, `kvExactMode:0`. Converged Exact uses `kvExactMode:3`, selected `kvModelProfile`, `kvExactApiMode:chat`, `kvBlockSize:16`, and inventory `kvZmqPort:5557`. These geometry settings must match the actual engine; endpoint listener readiness is not model readiness.

#### Exact readiness {#exact-ready}

**Exact only; skip for RR:** wait for the correct binding to become READY with no reasons. Retry this read-only check after startup if needed; do not send Exact traffic before it succeeds.

```bash
curl --config "$CURL_CONFIG" --fail-with-body   "$API/config/loadbalancer/externalipaddress/$VIP/port/28300/protocol/tcp/kvexactstatus?model_name=$MODEL_ESCAPED" > exact-status.json
jq -e 'any(.kvExactStatusAttr[]; .enforcedState=="READY" and ((.reasonCodes // [])|length)==0)' exact-status.json || exit 1
```

### 7. Send traffic and verify worker selection {#verify-routing}

Use fresh engines for the packaged repeated-prefix inputs. Warm worker B, then save all six main client responses and each worker's receipt ledger. For Exact, wait for inventory propagation before sending the six requests. Three seconds was used in this campaign; READY plus actual hit/distribution evidence is the success gate, not the sleep alone.

```bash
export FUNCTIONAL_INPUTS="$PACKAGE/results/converged/$RECIPE_CASE"
cp "$FUNCTIONAL_INPUTS/$ROUTING-warm.request.json" routing-json.json
jq '. + {stream:true,stream_options:{include_usage:true}}' routing-json.json > routing-sse.json
curl --fail-with-body --max-time 180 -o warm.body -H 'Content-Type: application/json'   -H "X-ModeQA-Request-ID: $RID_PREFIX-route-warm" --data-binary @routing-json.json   "http://$WORKER_B:18301/v1/chat/completions"
sleep 3
if test "$ROUTING" = exact; then
  curl --fail-with-body --max-time 180 -o exact-metric-prime.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-metric-prime" --data-binary @routing-json.json "http://$VIP:28300/v1/chat/completions"
fi
curl --config "$CURL_CONFIG" --fail-with-body "$API/metrics" > metrics-before.txt
if test "$ROUTING" = exact; then
  awk '/^loxilb_pd_kv_tier15_hits_total/ {n++; total+=$NF} END {if (!n) exit 1; print total}' metrics-before.txt > exact-hits-before.txt
fi
curl --fail-with-body --max-time 180 -o main-1.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-main-1" --data-binary @routing-json.json "http://$VIP:28300/v1/chat/completions"
curl --fail-with-body --max-time 180 -N -o main-2.sse -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-main-2" --data-binary @routing-sse.json "http://$VIP:28300/v1/chat/completions"
curl --fail-with-body --max-time 180 -o main-3.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-main-3" --data-binary @routing-json.json "http://$VIP:28300/v1/chat/completions"
curl --fail-with-body --max-time 180 -N -o main-4.sse -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-main-4" --data-binary @routing-sse.json "http://$VIP:28300/v1/chat/completions"
curl --fail-with-body --max-time 180 -o main-5.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-main-5" --data-binary @routing-json.json "http://$VIP:28300/v1/chat/completions"
curl --fail-with-body --max-time 180 -N -o main-6.sse -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-main-6" --data-binary @routing-sse.json "http://$VIP:28300/v1/chat/completions"
curl --config "$CURL_CONFIG" --fail-with-body "$API/metrics" > metrics-after.txt
if test "$ROUTING" = exact; then
  awk '/^loxilb_pd_kv_tier15_hits_total/ {n++; total+=$NF} END {if (!n) exit 1; print total}' metrics-after.txt > exact-hits-after.txt
  awk -v before="$(cat exact-hits-before.txt)" -v after="$(cat exact-hits-after.txt)" 'BEGIN {delta=after-before; print "Exact hit delta:",delta; exit(delta<6)}'
fi
sha256sum main-1.body main-2.sse main-3.body main-4.sse main-5.body main-6.sse
```

The Exact-only `metric-prime` request must complete normally and has its own receipt. Exclude it from main6. Some zero-valued metric series are omitted until first use; require a numeric `loxilb_pd_kv_tier15_hits_total` baseline and after value rather than silently treating an absent series as zero. If either is missing, stop the metric check.

Expected in this isolated two-worker test: RR six main receipts split **3:3**; Exact **0:6** to warmed worker B, with at least six additional Exact-hit counter events. All six answers must pass the normal-answer gate. No unrelated inference may overlap this measurement.

On each worker, count only this run's main IDs in `receipts.jsonl`:

```bash
RECEIPTS="$(cat "$RUN/receipt-directory.txt")"
export RECEIPTS
jq -s --arg p "$RID_PREFIX-main-"   '[.[]|select(.requestId|startswith($p))]|{requests:length,complete:all(.[];.upstreamComplete and .httpStatus==200)}'   "$RECEIPTS/receipts.jsonl"
```

Use the **same Gateway-generated `RID_PREFIX`** for this read-only query on both workers; print it in the Gateway terminal and set that value in the worker verification terminal. The worker's locally generated prefix may differ. Keep collector processes running in their own terminals. Collector commands permit the expected Ctrl-C exit130 so the shell remains usable for restart; other failures stop the command path. `complete:true` with zero rows is not a pass: verify the required counts above.

For a response received by one worker, compare its recorded hash with the client hash. Example for main 1, on the worker that received it:

```bash
export RID='COPY_THE_GATEWAY_MAIN_1_REQUEST_ID_HERE'
jq -e --arg r "$RID" 'select(.requestId==$r) | .upstreamComplete and .httpStatus==200' "$RECEIPTS/receipts.jsonl" || exit 1
jq -r --arg r "$RID" 'select(.requestId==$r)|.requestSha256+"  "+.requestFile' "$RECEIPTS/receipts.jsonl"   | (cd "$RECEIPTS" && sha256sum -c -) || exit 1
RESPONSE_FILES=("$RECEIPTS/$RID"-*.response)
test "${#RESPONSE_FILES[@]}" = 1 && test -f "${RESPONSE_FILES[0]}" || exit 1
sha256sum "${RESPONSE_FILES[0]}"
jq -r --arg r "$RID" 'select(.requestId==$r)|.responseSha256' "$RECEIPTS/receipts.jsonl"
```

The last two digests must match each other and the Gateway host's `main-1.body` digest. Repeat for all six; retain complete receipt folders through your approved private evidence-transfer process. These commands verify your new run, whereas the package's three verifiers validate the **recorded campaign**. They are not interchangeable.

### 8. Verify rejection and new-request path recovery {#reject-recover-cleanup}

**Gateway shell:** an unknown model must return 503 `model_unavailable` with `no backend pool for this model`. Both workers must have zero receipts for its request ID. Invalid converged mode 7 must return 422 without changing effective state.

```bash
jq '.model="qa-unknown-existing-profile"' request.json > unknown.json
curl -sS --max-time 30 -o unknown.body -w '%{http_code}\n' -H 'Content-Type: application/json'   -H "X-ModeQA-Request-ID: $RID_PREFIX-unknown" --data-binary @unknown.json "http://$VIP:28300/v1/chat/completions"
curl --config "$CURL_CONFIG" --fail-with-body "$API/config/loadbalancer/all" > before-invalid.json
jq '.serviceArguments.kvExactMode=7' rule.json > invalid-mode.json
curl --config "$CURL_CONFIG" -sS -o invalid-mode.body -w '%{http_code}\n' -H 'Content-Type: application/json'   --data-binary @invalid-mode.json "$API/config/loadbalancer"
curl --config "$CURL_CONFIG" --fail-with-body "$API/config/loadbalancer/all" > after-invalid.json
jq -S '.lbAttr |= map((.endpoints |= map(del(.counter))) | del(.serviceArguments.fc_effective.reservation_epoch))' before-invalid.json > before-invalid-canonical.json
jq -S '.lbAttr |= map((.endpoints |= map(del(.counter))) | del(.serviceArguments.fc_effective.reservation_epoch))' after-invalid.json > after-invalid-canonical.json
cmp before-invalid-canonical.json after-invalid-canonical.json || exit 1
jq -S '.lbAttr[0].serviceArguments.kvExactMode=99' after-invalid-canonical.json > changed-mode-control.json
if cmp -s before-invalid-canonical.json changed-mode-control.json; then echo 'Invalid comparison: actual mode change was missed'; exit 1; fi
```

Do not exclude other configuration differences. Preserve both originals. A negative-status test intentionally omits curl's `--fail-with-body` so its expected error body/status can be inspected; it is not a normal-answer pass.

For optional transport-path recovery, keep native engines running and stop only the selected collector with Ctrl-C: A for RR, warmed B for Exact. Wait for health monitoring to mark that listener unavailable (the campaign waited seven seconds), then send two fresh-ID requests using the same main payload. Both must complete normally through the surviving worker; the stopped worker must receive none. This is not an engine-crash or active-stream-continuity test.

**Gateway shell, after the selected listener is confirmed unavailable:** send the two survivor offers below. Then restart the collector as shown below and confirm native/receipt readiness before the recovery warmups.

```bash
curl --fail-with-body --max-time 180 -o survivor-1.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-survivor-1" --data-binary @routing-json.json "http://$VIP:28300/v1/chat/completions"
curl --fail-with-body --max-time 180 -o survivor-2.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-survivor-2" --data-binary @routing-json.json "http://$VIP:28300/v1/chat/completions"
```

Restart the collector **in its original terminal** with its preserved directory; do not repeat the initial `test ! -e` guard:

```bash
RECEIPTS="$(cat "$RUN/receipt-directory.txt")"
export RECEIPTS
python3 "$PACKAGE/receipt-proxy.py" --bind "$WORKER_IP" --port 18301   --upstream-port 18300 --directory "$RECEIPTS" || { rc=$?; test "$rc" = 130 || exit "$rc"; }
```

**Gateway shell, after collector readiness:**

```bash
cp "$FUNCTIONAL_INPUTS/$ROUTING-recovery-warm-0.request.json" recovery-a.json
cp "$FUNCTIONAL_INPUTS/$ROUTING-recovery-warm-1.request.json" recovery-b.json
curl --fail-with-body --max-time 180 -o recovery-warm-a.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-recovery-warm-a" --data-binary @recovery-a.json "http://$WORKER_A:18301/v1/chat/completions"
curl --fail-with-body --max-time 180 -o recovery-warm-b.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-recovery-warm-b" --data-binary @recovery-b.json "http://$WORKER_B:18301/v1/chat/completions"
sleep 3
curl --fail-with-body --max-time 180 -o recovery-1.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-recovery-1" --data-binary @recovery-a.json "http://$VIP:28300/v1/chat/completions"
curl --fail-with-body --max-time 180 -o recovery-2.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-recovery-2" --data-binary @recovery-b.json "http://$VIP:28300/v1/chat/completions"
curl --fail-with-body --max-time 180 -o recovery-3.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-recovery-3" --data-binary @recovery-a.json "http://$VIP:28300/v1/chat/completions"
curl --fail-with-body --max-time 180 -o recovery-4.body -H 'Content-Type: application/json' -H "X-ModeQA-Request-ID: $RID_PREFIX-recovery-4" --data-binary @recovery-b.json "http://$VIP:28300/v1/chat/completions"
```

The recovery inputs use two fresh prefixes warmed separately on the two workers. The recorded gate is **2:2**, with all answers normal and receipts complete. Count only `-survivor-` or `-recovery-1` through `-recovery-4` IDs for the corresponding phase; exclude recovery warmups. Do not reuse an old main denominator. Exact recovery must additionally demonstrate the expected affinity/hit behavior. Preserve failures such as Qwen3.8's observed 3:1/1:3 distributions rather than declaring recovery from HTTP200 alone.

### 9. Delete the rule and return owned resources {#cleanup}

**Gateway shell:** delete only the selected model/VIP/port rule and verify the dedicated Gateway has returned to its original empty rule list.

```bash
curl --config "$CURL_CONFIG" --fail-with-body -X DELETE   "$API/config/loadbalancer/hosturl/$VIP/externalipaddress/$VIP/port/28300/protocol/tcp?model_name=$MODEL_ESCAPED"
curl --config "$CURL_CONFIG" --fail-with-body "$API/config/loadbalancer/all" > after-delete.json
jq -e '.lbAttr == []' after-delete.json || exit 1
```

If creation was rejected, preserve that response; a subsequent404 plus empty readback means no created rule remains. Do not treat404 as successful deletion of an existing rule.

Stop each collector with Ctrl-C in its own terminal. On **each worker**, preserve its exact native container's logs and remove only that owned test container:

```bash
export ENGINE_CONTAINER="existing-profile-$ENGINE"
test "$(docker inspect "$ENGINE_CONTAINER" --format '{{index .Config.Labels "igw.qa"}}')" = existing-profile-evaluation || exit 1
docker logs "$ENGINE_CONTAINER" > "$RUN/$ENGINE_CONTAINER.log" 2>&1
docker stop --time 20 "$ENGINE_CONTAINER"
docker inspect "$ENGINE_CONTAINER" --format '{{json .State}}'
nvidia-smi
docker rm "$ENGINE_CONTAINER"
```

Expected: no test rule, no test receipt listener, no owned engine container, and GPU allocation returned to the pre-run baseline. If memory remains allocated, inspect exact consumers; do not prune other containers/images or delete model caches. Preserve raw evidence and registry artifacts. The dedicated Gateway itself remains owned by your deployment procedure.

For **RR to Exact**, delete/verify the RR rule first, prepare Exact Gateway bindings, restart fresh native engines if reproducing cold behavior, and repeat Steps 6–9 with `ROUTING=exact` instead of the default `rr`. Use a new run/request-ID prefix. For **P/D**, complete cleanup and follow the [separate topology procedure](existing-profiles-pd.md).

### Troubleshooting and restore {#troubleshooting}

| Symptom | Check / next action |
|---|---|
| No settings/rule file | Selected scope is deferred or unqualified; return to the results table, not another model's settings |
| Image/model download denied | Resolve authorized artifact access; do not substitute revision, digest, tokenizer, or quantization |
| Native health/model check fails | Preserve startup logs; confirm files, GPU access, exact args, RAM/VRAM, and served name |
| Profile missing or Exact not READY | Confirm startup mounts/ownership, pinned artifact hashes, correct engine manifest, native events, and selected binding; do not bypass refusal |
| Ministral Exact400 / GPT-OSS vLLM Exact400 | Native-renderer contract rejection; use only the independently qualified modes |
| HTTP200 with length, empty final, or open reasoning | Preserve input/response; this is not normal completion. Changed output budgets need separate tests |
| Answer succeeds but expected worker split/hits fail | Routing scope failed; inspect receipts and effective state rather than pooling successes |
| Metrics unavailable | Resolve collection/authentication before claiming hit/counter evidence |
| Audit-directory permission503 | Verify only your owned writable audit directory has the expected owner/mode 0700; preserve files |

This isolated procedure rolls back to **empty rules**, not to a prior production service. For an engine-setting rollback, stop the owned container, reload the verified environment, launch a fresh engine, and recheck answers/routing/recovery. Previous process KV state is not restored. Zero-downtime production rollback, long-context/1M inference, and arbitrary concurrency are outside the recorded qualification.

[Back to results](existing-profiles.md) · [Next: optional native P/D](existing-profiles-pd.md) · [Optional: inspect recorded tuning](existing-profiles-tuning.md)

## Check your result

Prove native inference, receipt forwarding and Gateway delivery separately; keep each host's paths and saved operator.env local.

Select a supported model/engine tuple before interpreting results. Keep direct-worker success separate from Gateway delivery, routing evidence, engine cache reuse, performance and release qualification. Historical PASS, FAIL and BLOCKED results retain their original artifact identities.

## Next steps and cleanup

Use the canonical deployment sequence rather than combining fragments from different engine/version pages. Drain before switching or deleting owned resources; retained result pages are evidence, not another deployment recipe. Read the [lab starting point](../model-engine-standard/select.md) if required values are missing. Use [cleanup and recovery](../model-engine-standard/lifecycle.md) when ending the run.
