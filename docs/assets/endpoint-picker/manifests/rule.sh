#!/usr/bin/env bash
# rule.sh epp|chwbl|rr|delete|show
#   Creates the loxilb-igw rule on VIP:PORT in one routing mode, reading the vLLM pod IPs and the
#   EPP Service's ClusterIP from the cluster. A rule already on VIP:PORT is deleted first, because
#   eppEndpoint cannot be patched.
#
#   VIP=192.0.2.10 bash rule.sh epp
#   FAILMODE=FailOpen VIP=192.0.2.10 bash rule.sh epp
set -euo pipefail

VIP=${VIP:?set VIP to the gateway node IP}
PORT=${PORT:-8080}
LB=${LB:-http://$VIP:11111/netlox/v1}
NS=${NS:-llm-d-pd-disaggregation}
POD_LABEL=${POD_LABEL:-llm-d.ai/role=aggregated}
TARGET_PORT=${TARGET_PORT:-8000}
EPP_SVC=${EPP_SVC:-pd-disaggregation-epp}
EPP_GRPC_PORT=${EPP_GRPC_PORT:-9002}
FAILMODE=${FAILMODE:-FailClose}
TIMEOUT_MS=${TIMEOUT_MS:-3000}
KUBECTL=${KUBECTL:-kubectl}

endpoints() {
  $KUBECTL -n "$NS" get pod -l "$POD_LABEL" \
    -o jsonpath='{range .items[?(@.status.phase=="Running")]}{.status.podIP}{"\n"}{end}' |
  awk -v p="$TARGET_PORT" 'NF { printf "%s{\"endpointIP\":\"%s\",\"targetPort\":%s,\"weight\":1}", (n++ ? "," : ""), $1, p }'
}
epp_ip() { $KUBECTL -n "$NS" get svc "$EPP_SVC" -o jsonpath='{.spec.clusterIP}'; }

create() {  # $1 = sel, $2 = extra serviceArguments fields (JSON fragment starting with a comma, or empty)
  local eps; eps=$(endpoints)
  [ -n "$eps" ] || { echo "no Running pods with label $POD_LABEL in $NS" >&2; exit 1; }
  curl -s -X POST "$LB/config/loadbalancer" -H 'Content-Type: application/json' -d "{
    \"serviceArguments\": {\"externalIP\":\"$VIP\",\"port\":$PORT,\"protocol\":\"tcp\",\"mode\":4,
                           \"sel\":$1,\"name\":\"igw-$MODE\"$2},
    \"endpoints\": [$eps]}"
  echo
}
delete() { curl -s -X DELETE "$LB/config/loadbalancer/externalipaddress/$VIP/port/$PORT/protocol/tcp"; echo; }

MODE=${1:-}
case "$MODE" in
  epp)    delete >/dev/null
          create 0 ",\"eppEndpoint\":\"$(epp_ip):$EPP_GRPC_PORT\",\"eppFailureMode\":\"$FAILMODE\",\"eppTimeoutMs\":$TIMEOUT_MS" ;;
  chwbl)  delete >/dev/null; create 8 "" ;;
  rr)     delete >/dev/null; create 0 "" ;;
  delete) delete ;;
  show)   curl -s "$LB/config/loadbalancer/externalipaddress/$VIP/port/$PORT/protocol/tcp"; echo ;;
  *)      echo "usage: VIP=<gateway node IP> [PORT=8080] [FAILMODE=FailClose|FailOpen] $0 epp|chwbl|rr|delete|show" >&2; exit 1 ;;
esac
