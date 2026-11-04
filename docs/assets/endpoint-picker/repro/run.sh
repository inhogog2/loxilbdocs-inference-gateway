#!/usr/bin/env bash
# ============================================================================
# Endpoint Picker verification + cache benchmark harness
# Usage:   bash run.sh <command>
# Config:  config.env in the same folder (the only file to edit per cluster)
# Pod IPs, the pod count and the EPP ClusterIP are discovered at run time.
# ============================================================================
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/config.env"
TS=$(date +%Y%m%dT%H%M%S)
OUT=${OUT:-$HOME/epp_repro_$TS}; mkdir -p "$OUT"
log(){ echo "[$(date +%H:%M:%S)] $*"; }
K(){ $KUBECTL "$@"; }

# ---------- discovery ----------
ready_pods(){ # IPs of the Ready (1/1 Running) model-server pods
  $KUBECTL -n "$NS" get pods -l "$POD_LABEL" -o json 2>/dev/null | python3 -c '
import sys,json
for p in json.load(sys.stdin)["items"]:
    cs=p["status"].get("containerStatuses",[])
    if p["status"]["phase"]=="Running" and cs and all(c.get("ready") for c in cs):
        print(p["status"]["podIP"])'; }
epp_clusterip(){ $KUBECTL -n "$NS" get svc "$EPP_SVC" -o jsonpath='{.spec.clusterIP}' 2>/dev/null; }
build_eps(){ local eps=""; for ip in "$@"; do eps="$eps${eps:+,}{\"endpointIP\":\"$ip\",\"targetPort\":$TARGET_PORT,\"weight\":1}"; done; echo "$eps"; }

# ---------- gateway rule ----------
del_rule(){ curl -s -X DELETE "$LOXILB_API/config/loadbalancer/externalipaddress/$VIP/port/$PORT/protocol/tcp" >/dev/null 2>&1; }
mkrule(){ # mkrule <epp|chwbl|rr>: the rule on VIP:PORT with the Ready pods as endpoints
  local mode=$1; local eps; eps=$(build_eps $(ready_pods)); local epp_ip; epp_ip=$(epp_clusterip)
  local sel name epp
  case $mode in
    epp)   sel=$SEL_EPP;   name=repro-epp;   epp=",\"eppEndpoint\":\"$epp_ip:$EPP_GRPC_PORT\",\"eppFailureMode\":\"$EPP_FAILMODE\",\"eppTimeoutMs\":$EPP_TIMEOUT_MS";;
    chwbl) sel=$SEL_CHWBL; name=repro-chwbl; epp="";;
    rr)    sel=$SEL_RR;    name=repro-rr;    epp="";;
    *) echo "unknown mode $mode"; return 1;;
  esac
  del_rule
  curl -s -X POST "$LOXILB_API/config/loadbalancer" -H 'Content-Type: application/json' \
    -d "{\"serviceArguments\":{\"externalIP\":\"$VIP\",\"port\":$PORT,\"protocol\":\"tcp\",\"mode\":$LB_MODE,\"sel\":$sel,\"name\":\"$name\"$epp},\"endpoints\":[$eps]}" >/dev/null
  sleep 2; }
mkrule_failmode(){ local fm=$1; local eps; eps=$(build_eps $(ready_pods)); local epp_ip; epp_ip=$(epp_clusterip)
  del_rule
  curl -s -X POST "$LOXILB_API/config/loadbalancer" -H 'Content-Type: application/json' \
    -d "{\"serviceArguments\":{\"externalIP\":\"$VIP\",\"port\":$PORT,\"protocol\":\"tcp\",\"mode\":$LB_MODE,\"sel\":$SEL_EPP,\"name\":\"repro-fm\",\"eppEndpoint\":\"$epp_ip:$EPP_GRPC_PORT\",\"eppFailureMode\":\"$fm\",\"eppTimeoutMs\":3000},\"endpoints\":[$eps]}" >/dev/null
  sleep 2; }

# ---------- metrics / logs ----------
vmetric(){ curl -s -m5 "http://$1:$TARGET_PORT/metrics" 2>/dev/null | awk -v k="$2" '$0 ~ "^"k"[ {]"{s+=$NF}END{print s+0}'; }
snap(){ local tag=$1; local f="$OUT/snap_$tag.txt"; : > "$f"; for ip in $(ready_pods); do
    echo "$ip $(vmetric $ip vllm:prefix_cache_queries_total) $(vmetric $ip vllm:prefix_cache_hits_total) $(vmetric $ip vllm:request_success_total)" >> "$f"; done; }
reuse(){ python3 - "$1" "$2" <<'PY'
import sys
def L(f):
 q=h=0
 for l in open(f):
  p=l.split(); q+=int(float(p[1])); h+=int(float(p[2]))
 return q,h
q0,h0=L(sys.argv[1]); q1,h1=L(sys.argv[2]); dq=q1-q0
print("%.1f%%"%(100*(h1-h0)/dq) if dq else "n/a")
PY
}
loxilb_epp_metric(){ curl -s -m5 "$LOXILB_API/metrics" 2>/dev/null | awk -v k="$EPP_METRIC" '$0 ~ "^"k"[ {]"{s+=$NF}END{print s+0}'; }
served_pod(){ # served_pod <snapshot file>: the pod whose request_success counter rose (sequential sends)
  local bf=$1 t ip s0 s1
  for t in $(seq 1 30); do
    while read ip _ _ s0; do s1=$(vmetric "$ip" vllm:request_success_total); [ "$s1" -gt "$s0" ] && { echo "$ip"; return; }; done < "$bf"
    sleep 0.3
  done; echo "-"; }

# ---------- EPP log level / pool / scale ----------
epp_cindex(){ $KUBECTL -n "$NS" get deploy "$EPP_DEPLOY" -o json | python3 -c '
import sys,json; d=json.load(sys.stdin); cs=d["spec"]["template"]["spec"]["containers"]
import os
want=os.environ.get("EPP_CONTAINER","epp")
print(next((i for i,c in enumerate(cs) if c["name"]==want), len(cs)-1))'; }
epp_set_v(){ local lvl=$1; local idx; idx=$(EPP_CONTAINER="$EPP_CONTAINER" epp_cindex)
  local cur new; cur=$($KUBECTL -n "$NS" get deploy "$EPP_DEPLOY" -o jsonpath="{.spec.template.spec.containers[$idx].args}")
  new=$(python3 -c "import json,sys;a=json.loads(sys.argv[1]);a=[('--v=%s'%sys.argv[2] if x.startswith('--v=') else x) for x in a];print(json.dumps(a))" "$cur" "$lvl")
  $KUBECTL -n "$NS" patch deploy "$EPP_DEPLOY" --type=json -p "[{\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/$idx/args\",\"value\":$new}]" >/dev/null
  $KUBECTL -n "$NS" rollout status deploy/"$EPP_DEPLOY" --timeout=180s >/dev/null 2>&1; sleep 5; }
pool_restore(){ $KUBECTL -n "$NS" patch "$POOL_KIND" "$POOL_NAME" --type=json -p "[{\"op\":\"replace\",\"path\":\"/spec/selector/matchLabels\",\"value\":$POOL_DEFAULT_SELECTOR}]" >/dev/null 2>&1; }
epp_replicas(){ $KUBECTL -n "$NS" get deploy "$EPP_DEPLOY" -o jsonpath='{.spec.replicas}'; }
epp_scale(){ $KUBECTL -n "$NS" scale deploy/"$EPP_DEPLOY" --replicas=$1 >/dev/null; }
epp_wait_down(){ local ip; ip=$(epp_clusterip); for i in $(seq 1 60); do
    local np ep; np=$($KUBECTL -n "$NS" get pods -o name 2>/dev/null | grep -c "$EPP_DEPLOY")
    ep=$($KUBECTL -n "$NS" get endpoints "$EPP_SVC" -o jsonpath='{.subsets}' 2>/dev/null)
    if timeout 2 bash -c "echo > /dev/tcp/$ip/$EPP_GRPC_PORT" 2>/dev/null; then r=no; else r=yes; fi
    [ "$np" = 0 ] && [ -z "$ep" ] && [ "$r" = yes ] && { log "EPP is down: no pod, no endpoint, port closed"; return 0; }; sleep 3
  done; log "warning: could not confirm that the EPP is fully down"; return 1; }
epp_wait_up(){ local ip; ip=$(epp_clusterip); $KUBECTL -n "$NS" rollout status deploy/"$EPP_DEPLOY" --timeout=180s >/dev/null 2>&1
  for i in $(seq 1 40); do timeout 2 bash -c "echo > /dev/tcp/$ip/$EPP_GRPC_PORT" 2>/dev/null && { log "EPP accepts on :$EPP_GRPC_PORT again"; return 0; }; sleep 3; done; }

# ---------- sending ----------
send_one(){ curl -s -o /dev/null -m 30 -w '%{http_code} %{time_total}' -X POST "http://$VIP:$PORT/v1/completions" \
  -H 'Content-Type: application/json' -H "x-request-id: $1" \
  -d "{\"model\":\"$MODEL\",\"prompt\":\"$2\",\"max_tokens\":${3:-4}}"; }

need_pods(){ local n; n=$(ready_pods | wc -l); [ "$n" -lt 2 ] && { log "only $n Ready pod(s); this harness needs at least 2. Retry when the pods are up."; exit 1; }; log "$n Ready pods: $(ready_pods | tr '\n' ' ')"; }

# ============================================================================
#  verify-path — does every request go through the EPP?
# ============================================================================
cmd_verify_path(){ need_pods
  log "[verify-path] N=$VERIFY_N requests; raising the EPP log level to $EPP_V_DEBUG"
  epp_set_v "$EPP_V_DEBUG"; mkrule epp
  local before after; before=$(loxilb_epp_metric)
  local T0; T0=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  : > "$OUT/q1_sent.txt"
  for i in $(seq 1 "$VERIFY_N"); do rid=$(printf "vrfy-%04d" "$i")
    echo "$rid $(send_one "$rid" "Q1 $rid uniq$RANDOM: name a color." 4)" >> "$OUT/q1_sent.txt"; done
  sleep 3; after=$(loxilb_epp_metric)
  $KUBECTL -n "$LOXILB_LOG_NS" logs "$LOXILB_LOG_SEL" --since-time="$T0" 2>/dev/null | grep -E '\[EPP\].* -> ' > "$OUT/q1_loxilb.log"
  $KUBECTL -n "$NS" logs deploy/"$EPP_DEPLOY" -c "$EPP_CONTAINER" --since-time="$T0" 2>/dev/null | grep '"Request handled"' > "$OUT/q1_epp.log"
  epp_set_v "$EPP_V_NORMAL"; del_rule
  { echo "== verify-path =="
    echo "requests sent:           $(wc -l < "$OUT/q1_sent.txt")"
    echo "HTTP 200:                $(grep -c ' 200 ' "$OUT/q1_sent.txt")"
    echo "gateway EPP metric:      $before -> $after (+$((after-before)))  [must equal N]"
    echo "gateway '-> ip' lines:   $(grep -c ' -> ' "$OUT/q1_loxilb.log")"
    echo "EPP 'Request handled':   $(grep -c 'Request handled' "$OUT/q1_epp.log")"
    echo "per-pod, EPP decisions:  $(grep -oE '\"endpoint\":\"[0-9.]+' "$OUT/q1_epp.log" | sed 's/.*\"//' | sort | uniq -c | tr '\n' ' ')"
    echo "per-pod, gateway:        $(grep -oE '\-> [0-9.]+' "$OUT/q1_loxilb.log" | awk '{print $2}' | sort | uniq -c | tr '\n' ' ')"
  } | tee "$OUT/q1_result.txt"
  log "[verify-path] files: $OUT/q1_*  PASS when sent == metric delta == gateway lines == EPP lines"; }

# ============================================================================
#  verify-decides — is the EPP the one deciding? (RR alone scatters a conversation, the EPP pins it)
# ============================================================================
cmd_verify_decides(){ need_pods
  # Pool-independent form: works on clusters where kube-loxilb owns the InferencePool.
  local S=${VERIFY_SESS:-6} T=${VERIFY_TURNS:-8}
  local RES="$OUT/q2_rows.txt"; : > "$RES"
  local W="gateway router cache prefix block hash tensor kernel latency cluster endpoint session context window attention decode prefill schedule batch token memory replica scorer affinity queue stream header socket proxy metric event worker policy threshold warmup shard rank device module vector matrix layer embedding sampler prompt answer system assistant dialogue history summary document"
  _m(){ local mode=$1 nonce=$RANDOM s t; log "[verify-decides] $mode: $S conversations x $T sequential turns"; mkrule "$mode"
    for s in $(seq 1 $S); do local pre="Session $mode-$nonce-$s: $W $W ($mode-$nonce-$s)." hist=""
      for t in $(seq 1 $T); do snap q2tmp >/dev/null; mv "$OUT/snap_q2tmp.txt" "$OUT/.s2"
        local prompt="$pre$hist Q$t color $t? A:"
        curl -s -o /dev/null -m 30 -X POST "http://$VIP:$PORT/v1/completions" -H 'Content-Type: application/json' -H "x-request-id: q2-$mode-$s-$t" \
          -d "$(python3 -c "import json,sys;print(json.dumps({'model':'$MODEL','prompt':sys.stdin.read(),'max_tokens':6}))" <<<"$prompt")"
        echo "$mode $s $t $(served_pod "$OUT/.s2")" >> "$RES"; hist="$hist Q$t A$t."; done; done; }
  _m rr; _m epp; del_rule
  python3 - "$RES" <<'PYEOF' | tee "$OUT/q2_result.txt"
import sys,collections
rows=[l.split() for l in open(sys.argv[1]) if l.strip()]
for mode in ("rr","epp"):
    bys=collections.defaultdict(set); dist=collections.Counter()
    for m,s,t,pod in rows:
        if m!=mode or pod=="-": continue
        bys[s].add(pod); dist[pod]+=1
    per=sorted((int(s),len(p)) for s,p in bys.items()); one=sum(1 for _,n in per if n==1)
    print(f"[{mode}] pods per conversation {[n for _,n in per]} -> single-pod conversations {one}/{len(per)} (distribution {dict(dist)})")
print("PASS when RR alone spreads conversations over several pods and the EPP keeps each on one pod: the EPP overrides the rule's own selector.")
PYEOF
  log "[verify-decides] rows: $RES"; }

# ============================================================================
#  verify-affinity — prefix-cache affinity (same measurement as bench-cache)
# ============================================================================
cmd_verify_affinity(){ need_pods; require_guidellm
  log "[verify-affinity] multi-turn reuse and throughput for EPP / CHWBL / RR"
  cmd_bench_cache
  log "[verify-affinity] PASS when EPP and CHWBL reuse is well above RR"; }

# ============================================================================
#  verify-vllm — a model-server pod is force-deleted under load
# ============================================================================
cmd_verify_vllm(){ need_pods
  log "[verify-vllm] force-deleting one serving pod under load (FailOpen rule)"
  mkrule_failmode FailOpen 2>/dev/null || mkrule epp
  local victim; victim=$($KUBECTL -n "$NS" get pods -l "$POD_LABEL" --field-selector status.phase=Running -o jsonpath='{.items[0].metadata.name}')
  : > "$OUT/q5.log"; rm -f "$OUT/.q5stop"
  ( while [ ! -f "$OUT/.q5stop" ]; do echo "$(send_one q5-$RANDOM "Q5 $RANDOM: a color." 4)" >> "$OUT/q5.log"; done ) & local LP=$!
  sleep 3; log "deleting $victim"; $KUBECTL -n "$NS" delete pod "$victim" --grace-period=0 --force >/dev/null 2>&1
  sleep 25; touch "$OUT/.q5stop"; wait $LP 2>/dev/null; rm -f "$OUT/.q5stop"; del_rule
  { echo "== verify-vllm =="; echo "requests:     $(wc -l < "$OUT/q5.log")"; echo "non-200:      $(grep -vc ' 200 ' "$OUT/q5.log")"
    echo "max latency:  $(awk '{print $2}' "$OUT/q5.log" | sort -n | tail -1)s"
    echo "PASS when non-200 stays 0 while the pod is deleted."
  } | tee "$OUT/q5_result.txt"; }

# ============================================================================
#  verify-failmode — EPP down: FailClose 503, FailOpen 200, recovery
# ============================================================================
cmd_verify_failmode(){ need_pods
  local REPL; REPL=$(epp_replicas); local N=15
  log "[verify-failmode] step 1: scale the EPP to 0 and confirm it is down"
  epp_scale 0; epp_wait_down
  log "[verify-failmode] step 2: FailClose, expecting 503"; mkrule_failmode FailClose; local T2; T2=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  : > "$OUT/q6_fc.txt"; for i in $(seq 1 $N); do echo "$(send_one fc-$i "x" 4)" >> "$OUT/q6_fc.txt"; done
  log "[verify-failmode] step 3: FailOpen, expecting 200 spread by the rule's own selector"; mkrule_failmode FailOpen
  : > "$OUT/q6_fo.txt"; for i in $(seq 1 $N); do snap q6tmp >/dev/null; mv "$OUT/snap_q6tmp.txt" "$OUT/.s6"
    echo "$(send_one fo-$i "Q6 $i uniq$RANDOM: a color" 4) $(served_pod "$OUT/.s6")" >> "$OUT/q6_fo.txt"; done
  log "[verify-failmode] step 4: recovery (replicas=$REPL)"; epp_scale "$REPL"; epp_wait_up; del_rule
  { echo "== verify-failmode =="
    echo "FailClose codes:        $(awk '{print $1}' "$OUT/q6_fc.txt" | sort | uniq -c | tr '\n' ' ')  [expect 503]"
    echo "FailClose latency:      min/max $(awk '{print $2}' "$OUT/q6_fc.txt" | sort -n | sed -n '1p;$p' | tr '\n' ' ')"
    echo "FailOpen codes:         $(awk '{print $1}' "$OUT/q6_fo.txt" | sort | uniq -c | tr '\n' ' ')  [expect 200]"
    echo "FailOpen pods:          $(awk '{print $3}' "$OUT/q6_fo.txt" | sort | uniq -c | tr '\n' ' ')  [several pods = the rule's selector]"
  } | tee "$OUT/q6_result.txt"; }

# ============================================================================
#  guidellm
# ============================================================================
require_guidellm(){ [ -x "$GUIDELLM_BIN" ] && return 0
  log "guidellm not found; installing with pip --user"
  python3 -m pip install --user guidellm >/dev/null 2>&1 || { log "install failed: check python3 -m pip"; return 1; }
  [ -x "$GUIDELLM_BIN" ] || GUIDELLM_BIN=$(command -v guidellm); }
gdl(){ "$GUIDELLM_BIN" "$@"; }
parse_bench(){ python3 - "$1" "$2" "$3" <<'PY'
import sys,json
js,scn,mode=sys.argv[1:4]
def g(d,*ks):
 for k in ks:
  if isinstance(d,dict) and k in d: d=d[k]
  else: return None
 return d
def f(x,s=1): return ("%.1f"%(x*s)) if isinstance(x,(int,float)) else "?"
try:
 d=json.load(open(js)); m=d["benchmarks"][0]["metrics"]
 print("\t".join([scn,mode,
   f(g(m,"requests_per_second","successful","mean")),
   f(g(m,"output_tokens_per_second","successful","mean")),
   f(g(m,"time_to_first_token_ms","successful","percentiles","p50")),
   f(g(m,"time_to_first_token_ms","successful","percentiles","p95")),
   f(g(m,"request_latency","successful","percentiles","p50"),1000),
   str(g(m,"request_totals","successful")),str(g(m,"request_totals","errored"))]))
except Exception as e: print("\t".join([scn,mode,"ERR","","","","",str(e)[:30],""]))
PY
}

# ============================================================================
#  bench-cache — multi-turn cache reuse, EPP vs CHWBL vs RR, long and short conversations
# ============================================================================
cmd_bench_cache(){ need_pods; require_guidellm
  local S="$OUT/bench_cache.tsv"; echo -e "scenario\tmode\tcache_reuse\treq_s\ttok_s\tttft_p50\tttft_p95\tlat_p50\tok\terr" > "$S"
  _run(){ local scn=$1 ptok=$2 otok=$3 turns=$4 xtok=$5
    for mode in $MODES; do log "[bench-cache] $scn/$mode"; mkrule "$mode"; snap "c_${scn}_${mode}_b" >/dev/null
      gdl run --backend kind=openai_http,target=http://$VIP:$PORT,model=$MODEL,request_format=/v1/chat/completions \
        --data kind=synthetic_text,prompt_tokens=$ptok,output_tokens=$otok,turns=$turns,prefix_tokens=$xtok,prefix_count=$PREFIX_COUNT \
        --profile kind=concurrent --override profile.streams $STREAMS \
        --constraint kind=max_duration,seconds=$BENCH_DUR --tokenizer kind=hf_auto,model=$TOKENIZER \
        --output kind=json,path="$OUT/c_${mode}_${scn}.json" --disable-progress > "$OUT/c_${mode}_${scn}.out" 2>&1
      snap "c_${scn}_${mode}_a" >/dev/null
      # cache_reuse goes into the third column
      R=$(reuse "$OUT/snap_c_${scn}_${mode}_b.txt" "$OUT/snap_c_${scn}_${mode}_a.txt")
      P=$(parse_bench "$OUT/c_${mode}_${scn}.json" "$scn" "$mode")
      echo "$P" | awk -F'\t' -v r="$R" '{print $1"\t"$2"\t"r"\t"$3"\t"$4"\t"$5"\t"$6"\t"$7"\t"$8"\t"$9}' >> "$S"
    done; }
  _run long  "$PROMPT_LONG"  "$OUT_LONG"  "$TURNS_LONG"  "$PREFIX_LONG"
  _run short "$PROMPT_SHORT" "$OUT_SHORT" "$TURNS_SHORT" "$PREFIX_SHORT"
  del_rule; echo; echo "== bench-cache summary =="; column -t -s$'\t' "$S"; log "summary: $S"; }

# ============================================================================
#  bench-singleshot — concurrent single-shot requests (no turns), as a contrast to bench-cache
# ============================================================================
cmd_bench_singleshot(){ need_pods; require_guidellm
  local S="$OUT/bench_singleshot.tsv"; echo -e "mode\tcache_reuse\treq_s\tttft_p50\tttft_p95\tok\terr" > "$S"
  for mode in $MODES; do log "[bench-singleshot] $mode"; mkrule "$mode"; snap "s_${mode}_b" >/dev/null
    gdl run --backend kind=openai_http,target=http://$VIP:$PORT,model=$MODEL \
      --data kind=synthetic_text,prompt_tokens=$((PREFIX_LONG+100)),output_tokens=$OUT_LONG,prefix_tokens=$PREFIX_LONG,prefix_count=$PREFIX_COUNT \
      --profile kind=concurrent --override profile.streams $STREAMS \
      --constraint kind=max_requests,count=300 --tokenizer kind=hf_auto,model=$TOKENIZER \
      --output kind=json,path="$OUT/s_${mode}.json" --disable-progress > "$OUT/s_${mode}.out" 2>&1
    snap "s_${mode}_a" >/dev/null; R=$(reuse "$OUT/snap_s_${mode}_b.txt" "$OUT/snap_s_${mode}_a.txt")
    P=$(parse_bench "$OUT/s_${mode}.json" x "$mode")
    echo "$P" | awk -F'\t' -v r="$R" '{print $2"\t"r"\t"$3"\t"$5"\t"$6"\t"$8"\t"$9}' >> "$S"
  done; del_rule; echo; echo "== bench-singleshot summary =="; column -t -s$'\t' "$S"; log "summary: $S"; }

# ============================================================================
#  bench-sweep — throughput over concurrency
# ============================================================================
cmd_bench_sweep(){ need_pods; require_guidellm
  local S="$OUT/sweep_curve.tsv"; echo -e "mode\tstreams\treq_s\ttok_s\tttft_p50\tttft_p95\tlat_p50\tok\terr" > "$S"
  IFS=',' read -ra LV <<< "$SWEEP_STREAMS"
  for mode in $MODES; do log "[bench-sweep] $mode  streams=$SWEEP_STREAMS"; mkrule "$mode"
    gdl run --backend kind=openai_http,target=http://$VIP:$PORT,model=$MODEL,request_format=/v1/chat/completions \
      --data kind=synthetic_text,prompt_tokens=$PROMPT_LONG,output_tokens=$OUT_LONG,turns=$TURNS_LONG,prefix_tokens=$PREFIX_LONG,prefix_count=$PREFIX_COUNT \
      --profile kind=concurrent --override profile.streams $SWEEP_STREAMS \
      --constraint kind=max_duration,seconds=$SWEEP_DUR --tokenizer kind=hf_auto,model=$TOKENIZER \
      --output kind=json,path="$OUT/sweep_${mode}.json" --disable-progress > "$OUT/sweep_${mode}.out" 2>&1
    python3 - "$OUT/sweep_${mode}.json" "$mode" "$SWEEP_STREAMS" <<'PY' >> "$S"
import sys,json
js,mode,lv=sys.argv[1:4]; lv=lv.split(",")
def g(d,*ks):
 for k in ks:
  if isinstance(d,dict) and k in d: d=d[k]
  else: return None
 return d
def f(x,s=1): return ("%.1f"%(x*s)) if isinstance(x,(int,float)) else "?"
d=json.load(open(js))
for i,b in enumerate(d.get("benchmarks",[])):
 m=b.get("metrics",{}); st=lv[i] if i<len(lv) else "?"
 print("\t".join([mode,str(st),
   f(g(m,"requests_per_second","successful","mean")),
   f(g(m,"output_tokens_per_second","successful","mean")),
   f(g(m,"time_to_first_token_ms","successful","percentiles","p50")),
   f(g(m,"time_to_first_token_ms","successful","percentiles","p95")),
   f(g(m,"request_latency","successful","percentiles","p50"),1000),
   str(g(m,"request_totals","successful")),str(g(m,"request_totals","errored"))]))
PY
  done; del_rule; echo; echo "== bench-sweep summary =="; column -t -s$'\t' "$S"; log "summary: $S (the streams column follows the sweep order)"; }

# ============================================================================
usage(){ cat <<U
usage: bash run.sh <command>   (settings in config.env)
  prereq           pods Ready, gateway REST reachable, guidellm installed, tokenizer loads
  verify-path      every request goes through the EPP (sent == metric == gateway log == EPP log)
  verify-decides   the EPP decides: RR alone scatters a conversation, the EPP pins it
  verify-affinity  prefix-cache affinity (same measurement as bench-cache)
  verify-vllm      a model-server pod is force-deleted under load
  verify-failmode  EPP scaled to 0: FailClose 503, FailOpen 200, recovery
  verify-all       verify-path, verify-decides, verify-vllm, verify-failmode
  bench-cache      multi-turn cache reuse, EPP / CHWBL / RR, long and short conversations
  bench-singleshot concurrent single-shot requests, as a contrast
  bench-sweep      throughput over concurrency
  bench-all        bench-cache + bench-singleshot + bench-sweep
  all              verify-all + bench-all
Results are written to $OUT.
U
}
cmd_prereq(){ need_pods
  echo -n "gateway REST: "; curl -s -m5 -o /dev/null -w '%{http_code}\n' "$LOXILB_API/config/loadbalancer" || echo unreachable
  echo -n "EPP ClusterIP: "; epp_clusterip; echo
  require_guidellm && echo "guidellm: $($GUIDELLM_BIN --version 2>&1 | head -1)"
  echo -n "tokenizer ($TOKENIZER): "; ( cd /tmp && python3 -c "from transformers import AutoTokenizer;print('OK',len(AutoTokenizer.from_pretrained('$TOKENIZER')))" 2>&1 | tail -1 ); }
cmd_verify_all(){ cmd_verify_path; cmd_verify_decides; cmd_verify_vllm; cmd_verify_failmode; }
cmd_bench_all(){ cmd_bench_cache; cmd_bench_singleshot; cmd_bench_sweep; }
cmd_all(){ cmd_verify_all; cmd_bench_all; }

case "${1:-}" in
  prereq) cmd_prereq;;
  verify-path) cmd_verify_path;;
  verify-decides) cmd_verify_decides;;
  verify-affinity) cmd_verify_affinity;;
  verify-vllm) cmd_verify_vllm;;
  verify-failmode) cmd_verify_failmode;;
  verify-all) cmd_verify_all;;
  bench-cache) cmd_bench_cache;;
  bench-singleshot) cmd_bench_singleshot;;
  bench-sweep) cmd_bench_sweep;;
  bench-all) cmd_bench_all;;
  all) cmd_all;;
  *) usage;;
esac
