# Metrics reference

This catalog is generated from the Gateway metric manifest and contains only
families marked `release`. It proves the name, type, label schema, activation
class, mapped writer, and upstream evidence classification at the frozen source
revision. It does **not** prove that every family is present in a particular
deployment: feature activation, traffic, build tags, hardware, and runtime
configuration still determine whether a series is emitted.

- Gateway source commit: `72de93cd2af8e62a956083795e6d8e33bb354ff0`
- Selected Gateway eBPF submodule commit: `201ee03d36b354a20f47603c0f9fb4a9b9f14be3`
- Comparison release: `v0.9.8.9-rc.1` at `f08b18beda587217265c9ba6419159119914795c`
- Comparison release eBPF submodule commit: `5536a2117ad2ad1128900a0d808ad7dec2eee2b5`
- Release manifest availability: **absent**
- Manifest path: `deploy/monitoring/manifest/metric-manifest.json`
- Manifest SHA-256: `121e8e828468f6c91569662afa94ead0bdab5f4d61a22f5b52ae2e96ad602273`
- Embedded manifest source revision: `0cc23566c888a77c090ce41d99317002a618686b`
- Embedded manifest generation time: `2026-11-06T02:15:18+00:00`
- Manifest schema version: `1`
- Release-scope families: **298**
- Raw writer paths and evidence prose are intentionally not copied into this public catalog.

The table below is therefore a selected-source catalog, not a claim
that `v0.9.8.9-rc.1` ships every listed family. The comparison
release does not contain the generated metric manifest used by this page.
Release packaging and runtime emission require separate qualification.

## How to read evidence

| Status | Meaning |
| --- | --- |
| `verified-runtime` (70) | writer plus recorded runtime evidence in the upstream manifest |
| `verified-static` (69) | writer verified by static or unit evidence; no runtime claim |
| `conditional-with-proven-writer` (77) | writer exists but the family appears only when its feature path is active |
| `writer-mapped` (80) | writer source is mapped; runtime emission was not verified |
| `definition-only` (2) | registered without a separate writer, for example a gauge computed when Prometheus scrapes it; no runtime claim |

A writer or registration point is source evidence, not deployment evidence.
`verified-runtime` records upstream runtime evidence for that family, but this
documentation build does not rerun Linux, GPU, HA, or release tests.
The [verification status](verification-status.md) page keeps those evidence
lanes separate.

## Activation codes

Combined codes such as `DP+V` require both conditions.

| Code | Activation condition |
| --- | --- |
| `E` | eager scalar |
| `V` | lazy vector children |
| `P` | pre-created children |
| `C` | custom collector; collector-defined samples |
| `H` | eager TTFB histogram |
| `Q` | quota-lazy collector |
| `DP` | datapath-gated scalar |
| `T` | TTFT-window-lazy |
| `S` | startup-created child |

## Release-scope families

| Family | Type | Labels | Activation | Runtime scope | Evidence status |
| --- | --- | --- | --- | --- | --- |
| `loxilb_active_conntrack_entries` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_active_flow_count_sctp` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_active_flow_count_tcp` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_active_flow_count_udp` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_ai_active_streams` | `gauge` | `model` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_admission_adapt_moves_total` | `counter` | `service`, `pool`, `direction` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_adapt_reason` | `gauge` | `service`, `pool`, `reason` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_adapt_state` | `gauge` | `service`, `pool`, `state` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_anomalies_total` | `counter` | `kind` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_decisions_total` | `counter` | `service`, `pool`, `reason` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_effective_limit` | `gauge` | `service`, `pool` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_inflight` | `gauge` | `service`, `pool`, `role` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_limit` | `gauge` | `service`, `pool`, `role` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_mode` | `gauge` | `service`, `pool` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_queue_wait_seconds` | `histogram` | `service`, `pool` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_queued` | `gauge` | `service`, `pool` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_tenants_active` | `gauge` | `service`, `pool` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_admission_warming_endpoints` | `gauge` | `service`, `pool` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_class_config_lkg_intervals_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_engine_info` | `gauge` | `service`, `engine` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_epp_candidates_rejected_total` | `counter` | `reason` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_epp_duration_seconds` | `histogram` | none | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_epp_inflight` | `gauge` | none | `E` | `gateway-default` | `definition-only` |
| `loxilb_ai_epp_pending` | `gauge` | none | `E` | `gateway-default` | `definition-only` |
| `loxilb_ai_epp_requests_total` | `counter` | `outcome` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_fc_band_total` | `counter` | `service`, `band`, `outcome` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_fc_tenant_slots` | `gauge` | `service`, `kind` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_jwks_keys` | `gauge` | `profile` | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_jwks_last_success_timestamp_seconds` | `gauge` | `profile` | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_jwks_refresh_total` | `counter` | `profile`, `outcome` | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_jwks_usable` | `gauge` | `profile` | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_jwt_validation_total` | `counter` | `tenant`, `reason` | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_key_store_circuit_open` | `gauge` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_key_store_lookup_inflight` | `gauge` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_key_store_lookup_seconds` | `histogram` | `result` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_key_token_quota_limit_tokens` | `gauge` | `key_id` | `Q` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_key_token_quota_utilization` | `gauge` | `key_id` | `Q` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_keyed_services` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_ai_kv_attest_echo_total` | `counter` | `result` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_kv_attest_probe_fail_total` | `counter` | `reason` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_kv_attest_state` | `gauge` | `rule`, `state` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_kv_enforcement_fault` | `gauge` | `rule` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_kv_trtllm_drain_ownership_fault_total` | `counter` | `reason` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_kv_trtllm_drain_ownership_heal_total` | `counter` | none | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_llamacpp_probe_warnings_total` | `counter` | `service`, `kind` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_model_not_allowed_total` | `counter` | `model`, `tenant` | `V` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_netid_requests_total` | `counter` | `binding`, `tenant`, `outcome` | `V` | `gateway-default` | `verified-static` |
| `loxilb_ai_netid_resolver_faults_total` | `counter` | `service` | `V` | `gateway-default` | `verified-static` |
| `loxilb_ai_normal_session_hits_total` | `counter` | `model` | `V` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_pd_decode_duration_seconds` | `histogram` | `model` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_pd_decode_kv_fill_total` | `counter` | `model` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_pd_decode_selected_total` | `counter` | `path`, `model` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_pd_decode_ttft_seconds` | `histogram` | `model` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_pd_kv_params_found_total` | `counter` | `model` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_pd_kv_params_missing_total` | `counter` | `model` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_pd_prefill_duration_seconds` | `histogram` | `model` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_pd_prefill_fallback_total` | `counter` | `model`, `reason` | `P` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_pd_requests_total` | `counter` | `model`, `phase`, `status` | `P` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_pd_session_hits_total` | `counter` | `model` | `V` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_pd_terminator_synthesized_total` | `counter` | none | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_pd_tier_selected_total` | `counter` | `tier`, `model` | `V` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_policy_store_unavailable_total` | `counter` | none | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_rate_limit_hits_total` | `counter` | `tenant`, `reason` | `V` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_reap_fallback_total` | `counter` | none | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_request_duration_seconds` | `histogram` | `model`, `tenant` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_requests_total` | `counter` | `model`, `tenant`, `status`, `outcome`, `cause` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_reservation_clamped_total` | `counter` | `service`, `reason` | `V` | `gateway-default` | `verified-static` |
| `loxilb_ai_route_host_missing_total` | `counter` | none | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_store_write_outcome_unknown_total` | `counter` | `plane` | `C` | `gateway-default` | `verified-static` |
| `loxilb_ai_stream_early_bytes_closed_total` | `counter` | `service` | `V` | `gateway-default` | `verified-static` |
| `loxilb_ai_token_quota_cold_open_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_token_quota_denied_total` | `counter` | `tenant` | `V` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_token_quota_limit_tokens` | `gauge` | `tenant` | `Q` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_token_quota_model_limit_tokens` | `gauge` | `tenant`, `model` | `Q` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_token_quota_model_utilization` | `gauge` | `tenant`, `model` | `Q` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_token_quota_utilization` | `gauge` | `tenant` | `Q` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_tokens_consumed_total` | `counter` | `model`, `tenant`, `kind` | `V` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_tokens_estimated_total` | `counter` | `model`, `tenant` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_tokens_missing_total` | `counter` | `model`, `tenant`, `reason` | `V` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_unmetered_requests_total` | `counter` | `vip` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ai_user_model_token_quota_limit_tokens` | `gauge` | `tenant`, `user`, `model` | `Q` | `gateway-default` | `verified-static` |
| `loxilb_ai_user_model_token_quota_utilization` | `gauge` | `tenant`, `user`, `model` | `Q` | `gateway-default` | `verified-static` |
| `loxilb_ai_user_token_quota_limit_tokens` | `gauge` | `tenant`, `user` | `Q` | `gateway-default` | `verified-static` |
| `loxilb_ai_user_token_quota_utilization` | `gauge` | `tenant`, `user` | `Q` | `gateway-default` | `verified-static` |
| `loxilb_ai_vip_token_quota_limit_tokens` | `gauge` | `service` | `Q` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_vip_token_quota_utilization` | `gauge` | `service` | `Q` | `gateway-default` | `verified-runtime` |
| `loxilb_ai_worker_scrape_total` | `counter` | `result` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_audit_delegation_lookups_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_last_heartbeat_timestamp_seconds` | `gauge` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_last_write_timestamp_seconds` | `gauge` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_mgmt_timeouts_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_originator_dropped_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_orphaned_intents_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_records_dropped_total` | `counter` | `stream`, `reason` | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_records_lost_to_retention_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_records_unattributed_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_records_written_total` | `counter` | `stream` | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_reserve_breached` | `gauge` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_result_write_failures_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_segment_seal_failures_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_segments_pruned_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_sink_connected` | `gauge` | `sink` | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_sink_cursor_lag_bytes` | `gauge` | `sink` | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_sink_cursor_lag_seconds` | `gauge` | `sink` | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_sink_export_failures_total` | `counter` | `sink` | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_sink_lag_drops_total` | `counter` | `sink` | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_sink_poison_total` | `counter` | `sink` | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_sink_records_exported_total` | `counter` | `sink` | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_sync_failures_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_write_failures_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_writer_panics_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_writer_restarts_total` | `counter` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_audit_writer_up` | `gauge` | none | `C` | `gateway-default` | `verified-static` |
| `loxilb_autopersist_consecutive_failures` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_backend_traffic_bytes_total` | `counter` | `service`, `endpoint` | `P` | `gateway-default` | `verified-static` |
| `loxilb_backend_traffic_connections_total` | `counter` | `service`, `endpoint` | `V` | `gateway-default` | `writer-mapped` |
| `loxilb_backend_traffic_packets_total` | `counter` | `service`, `endpoint` | `P` | `gateway-default` | `verified-static` |
| `loxilb_boot_config_conflict_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_boot_legacy_fallback_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_client_traffic_packets_total` | `counter` | `service`, `sip` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_closed_connections_processed_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_config_dirty` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_conntrack_max_entries` | `gauge` | none | `DP` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_conntrack_stat_resets_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_endpoint_traffic_bytes_total` | `counter` | `service`, `dip` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_errors_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_firewall_rules` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_fw_drop_packets_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_fw_rule_drop_packets_total` | `counter` | `fw_rule` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_healthy_endpoints` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_host_cpu_utilization_percent` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_ipfilter_blacklist_bytes_total` | `counter` | `cidr`, `priority`, `zone` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ipfilter_blacklist_packets_total` | `counter` | `cidr`, `priority`, `zone` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ipfilter_rules` | `gauge` | `type` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ipfilter_whitelist_bytes_total` | `counter` | `cidr`, `priority`, `zone` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_ipfilter_whitelist_packets_total` | `counter` | `cidr`, `priority`, `zone` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_kv_exact_overlap_blocks` | `histogram` | none | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_kv_exact_prompt_blocks` | `histogram` | none | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_kv_exact_stage_seconds` | `histogram` | `stage`, `outcome` | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_kv_inv_cap_evictions_total` | `counter` | `service`, `ep` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_kv_inventory_fresh` | `gauge` | `service`, `ep` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_kv_subscriber_connected` | `gauge` | `service`, `ep` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_kv_subscriber_last_event_timestamp_seconds` | `gauge` | `service`, `ep` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_kv_subscriber_reconnect_total` | `counter` | `service`, `ep` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_kv_subscriber_recv_error_total` | `counter` | `service`, `ep` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_kv_subscriber_wire_reject_total` | `counter` | `service`, `ep`, `reason` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_l4_error_events_total` | `counter` | `proto`, `reason` | `V` | `gateway-default` | `writer-mapped` |
| `loxilb_last_restore_timestamp_seconds` | `gauge` | none | `E` | `gateway-default` | `verified-static` |
| `loxilb_lb_rule_interaction_bytes_total` | `counter` | `service`, `sip`, `dip` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_lb_rule_interaction_packets_total` | `counter` | `service`, `sip`, `dip` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_lb_rules` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_lb_select_failure_shutdown_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_log_lines_dropped_total` | `counter` | `level` | `C` | `gateway-default` | `verified-static` |
| `loxilb_new_flows` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_opa_circuit_breaker_state` | `gauge` | none | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_opa_firewall_rules` | `gauge` | none | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_opa_sync_duration_seconds` | `histogram` | none | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_opa_watcher_syncs_total` | `counter` | `status` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_parser_attributes_extracted_total` | `counter` | `protocol` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_parser_body_size_bytes` | `histogram` | `protocol` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_parser_calls_total` | `counter` | `protocol`, `status` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_parser_duration_seconds` | `histogram` | `protocol` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_pd_admission_overflow_shed_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_admission_queued_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_admission_shed_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_cb_flips_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_cb_proactive_heal_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_connect_failover_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_connect_retry_same_ep_ok_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_connect_retry_same_ep_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_decode_ep_died_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_decode_inflight` | `gauge` | none | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_pd_decode_zero_byte_eof_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_ep_info` | `gauge` | `service`, `ep_idx`, `ep` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_pd_fallback_to_normal_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_pd_kv_blocks` | `gauge` | `service`, `ep_idx` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_pd_kv_tier15_cold_seeds_total` | `counter` | `ep_idx` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_pd_kv_tier15_fallthrough_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_kv_tier15_hits_total` | `counter` | `ep_idx` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_pd_kv_tier15_miss_reason_total` | `counter` | `reason` | `P` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_pd_kv_tier15_spills_total` | `counter` | `ep_idx` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_pd_kv_zero_hit_watchdog_total` | `counter` | `service_id` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_pd_parked_connections` | `gauge` | none | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_pd_prefill_ep_died_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_prefill_inflight` | `gauge` | none | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_pd_sessions_active` | `gauge` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_sg_decode_close_drain_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_sg_oversize_reject_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_sg_prefill_abort_decode_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_sg_prefill_reject_relay_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_sg_room_retry_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_trie_nodes` | `gauge` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_pd_trt_ctx_early_exit_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_persist_total` | `counter` | `result` | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_policer_attached` | `gauge` | `ident` | `C` | `gateway-default` | `verified-static` |
| `loxilb_processed_bytes_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_processed_packets_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_processed_sctp_bytes_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_processed_sctp_packets_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_processed_tcp_bytes_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_processed_tcp_packets_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_processed_udp_bytes_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_processed_udp_packets_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_accept_blocked_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_accept_bound` | `gauge` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_active_connections` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_active_ssl_connections` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_cache_backpressure_ratio` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_cache_bytes` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_cache_bytes_max_conn` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_cache_conns_queued` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_cache_drain_partial_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_cache_high_water_events_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_chunked_responses_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_client_reset_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_context_inflight` | `gauge` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_conversation_hits_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_conversation_misses_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_conversation_sessions` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_conversation_ttl_expired_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_graceful_close_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_halfclose_accel_early_fin_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_accel_skipped_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_fin_gap_seconds` | `histogram` | `entry`, `stream` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_fin_total` | `counter` | `entry`, `outcome` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_held` | `gauge` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_held_oldest_seconds` | `gauge` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_hold_allowed` | `gauge` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_hold_cap_seconds` | `gauge` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_hold_default_mode` | `gauge` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_hold_ended_total` | `counter` | `reason` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_hold_expired_total` | `counter` | `answer_started`, `stream` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_hold_refused_total` | `counter` | `reason` | `P` | `gateway-default` | `verified-static` |
| `loxilb_proxy_halfclose_hold_spurious_wakeups_total` | `counter` | `kind` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_hold_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_halfclose_tls_fin_total` | `counter` | `path`, `early_owed` | `P` | `gateway-default` | `verified-static` |
| `loxilb_proxy_halfclose_user_agent_total` | `counter` | `family` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_header_deadline_drops_total` | `counter` | none | `E` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_http2_sessions_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_http_responses_by_status_total` | `counter` | `status_class` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_proxy_http_responses_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_http_ttfb_seconds` | `histogram` | none | `H` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_proxy_listen_drops_total` | `counter` | none | `E` | `gateway-default` | `verified-static` |
| `loxilb_proxy_listen_overflows_total` | `counter` | none | `E` | `gateway-default` | `verified-static` |
| `loxilb_proxy_pd_kv_params_overflow_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_pools_freed_total` | `counter` | none | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_pools_live` | `gauge` | none | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_qos_bytes_delayed_total` | `counter` | `vip`, `port`, `proto`, `direction` | `C` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_qos_bytes_passed_total` | `counter` | `vip`, `port`, `proto`, `direction` | `C` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_qos_cbs_bytes` | `gauge` | `vip`, `port`, `proto`, `direction` | `C` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_qos_cir_bytes_per_second` | `gauge` | `vip`, `port`, `proto`, `direction` | `C` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_qos_park_seconds_total` | `counter` | `vip`, `port`, `proto`, `direction` | `C` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_qos_parked_connections` | `gauge` | `vip`, `port`, `proto`, `direction` | `C` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_qos_parks_total` | `counter` | `vip`, `port`, `proto`, `direction` | `C` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_qos_tokens_bytes` | `gauge` | `vip`, `port`, `proto`, `direction` | `C` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_response_first_write_gap_seconds` | `histogram` | `stream` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_response_max_write_gap_seconds` | `histogram` | `stream` | `P` | `gateway-default` | `verified-runtime` |
| `loxilb_proxy_sse_stall_abort_seconds` | `gauge` | none | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_stream_abandon_age_seconds` | `histogram` | `reason` | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_proxy_stream_abandoned_total` | `counter` | `reason` | `P` | `gateway-default` | `writer-mapped` |
| `loxilb_requests_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_restore_duration_seconds` | `histogram` | none | `E` | `gateway-default` | `verified-static` |
| `loxilb_restore_total` | `counter` | `mode`, `result` | `P` | `gateway-default` | `verified-static` |
| `loxilb_security_aggregate_conn_blocked_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_aggregate_syn_blocked_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_aggregate_udp_blocked_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_conn_blocked_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_conn_passed_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_syn_blocked_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_syn_cookies_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_syn_passed_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_tracking_failures_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_udp_blocked_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_udp_bytes_blocked_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_udp_bytes_passed_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_udp_passed_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_unique_ips` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_security_unsupported_packet_blocked_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_service_errors_total` | `counter` | `service` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_service_requests_total` | `counter` | `service` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_service_traffic_bytes_total` | `counter` | `service` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_service_traffic_packets_total` | `counter` | `service` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_snapshot_quarantine_total` | `counter` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_snapshot_total` | `counter` | `trigger` | `P` | `gateway-default` | `verified-static` |
| `loxilb_sockproxy_sync_apply_errors_total` | `counter` | none | `E` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_sockproxy_sync_conflict_total` | `counter` | `outcome` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_sockproxy_sync_drop_total` | `counter` | `reason` | `V` | `gateway-default` | `verified-static` |
| `loxilb_sockproxy_sync_health_reject_total` | `counter` | `reason` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_sockproxy_sync_inflight_rpc` | `gauge` | `peer` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_sockproxy_sync_overflow_total` | `counter` | `kind` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_sockproxy_sync_peer_lag_seconds` | `gauge` | `peer` | `V` | `gateway-default` | `verified-static` |
| `loxilb_sockproxy_sync_peer_scope_version` | `gauge` | `peer` | `V` | `gateway-default` | `verified-runtime` |
| `loxilb_sockproxy_sync_peer_up` | `gauge` | `peer` | `V` | `gateway-default` | `verified-static` |
| `loxilb_sockproxy_sync_push_latency_seconds` | `histogram` | `peer`, `rpc` | `V` | `gateway-default` | `conditional-with-proven-writer` |
| `loxilb_system_cpu_utilization_percent` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_system_disk_utilization_percent` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_system_memory_utilization_percent` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |
| `loxilb_unhealthy_endpoints` | `gauge` | none | `E` | `gateway-default` | `writer-mapped` |

## Label enums used by examples

The example validator rejects unknown metric names and selector labels. For
the closed values below it also rejects exact (`=` or `!=`) selectors that
use values outside the frozen source contract.

| Family | Label | Allowed values |
| --- | --- | --- |
| `loxilb_ai_jwks_refresh_total` | `outcome` | `success`, `failure` |
| `loxilb_ai_pd_prefill_fallback_total` | `reason` | `no_status`, `origin_408`, `origin_429`, `origin_5xx`, `other`, `truncated` |
| `loxilb_ai_pd_requests_total` | `phase` | `aborted`, `complete`, `decode`, `prefill`, `unknown` |
| `loxilb_ai_pd_requests_total` | `status` | `client`, `error`, `rejected`, `success`, `timeout`, `truncated`, `unknown` |
| `loxilb_ai_pd_tier_selected_total` | `tier` | `tier0`, `tier1`, `tier15`, `tier2` |
| `loxilb_ai_requests_total` | `cause` | `(empty)`, `client`, `engine`, `gateway` |
| `loxilb_ai_requests_total` | `outcome` | `completed`, `denied`, `aborted` |
| `loxilb_ai_tokens_consumed_total` | `kind` | `prompt`, `completion` |
| `loxilb_ai_worker_scrape_total` | `result` | `ok`, `unreachable`, `http_error`, `body_error`, `unparseable`, `bad_request`, `unknown` |

## Source-declared label combinations

Request outcomes, causes, P/D phases and fallback reasons are extracted from `api/prometheus/ai_metrics.go`
at the Gateway commit above (source SHA-256: `ffb660a1c45b4034e5b8cc12bfb2faa835004e7afe3ed3e4a96a7a58b74b9017`).
The validator also rejects selectors that match none of these combinations.
Other enums above are reviewed documentation constants. Empty cause is written as `(empty)`.

| Family | Labels | Allowed combinations |
| --- | --- | --- |
| `loxilb_ai_pd_requests_total` | `phase` / `status` | `aborted` / `client`; `complete` / `success`; `decode` / `error`; `decode` / `rejected`; `decode` / `timeout`; `decode` / `truncated`; `decode` / `unknown`; `prefill` / `error`; `prefill` / `rejected`; `prefill` / `timeout`; `unknown` / `error` |
| `loxilb_ai_requests_total` | `outcome` / `cause` | `completed` / `(empty)`; `denied` / `(empty)`; `aborted` / `client`; `aborted` / `engine`; `aborted` / `gateway` |
