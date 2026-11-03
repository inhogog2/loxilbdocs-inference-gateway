# Selected-source API schema models

This page classifies every Swagger definition added since the public API
documentation baseline. It is generated from the union of `api/swagger.yml`
and `api/swagger-extras.yml`; a new or removed definition fails the docs gate
until its public relevance is reviewed here.

- Public schema baseline: `47803fb660ed54cd1f180b616db628461ad85d1a`
- Reviewed Gateway source: `c7b4af87f1eda7db1a6667aa797e1d3b389d21cc`
- Added definitions: **47**
- Removed definitions: **0**
- Evidence class: **source/static contract only**

These models describe the current development-source wire contract. Their
presence does not establish Linux runtime, GPU, HA, release packaging, or
production qualification. Confirm the Swagger served by the exact image you
deploy.

## Relevance classes

| Class | Count | Meaning |
| --- | ---: | --- |
| `direct-operation` | 26 | Direct request, response, or operation envelope |
| `nested-component` | 18 | Public component nested in another operation model |
| `shared-envelope` | 1 | Shared public wire envelope used by multiple operations |
| `companion-error` | 2 | Public error contract in the companion raw-handler specification |

Field notation is `name:type`; `array<Model>` identifies an array of
referenced objects, and braces identify a closed enum from Swagger.

## `api/swagger.yml`

[Open the exact source](https://github.com/loxilb-io/loxilb-inference-gateway/blob/c7b4af87f1eda7db1a6667aa797e1d3b389d21cc/api/swagger.yml). Definition count changed from **147** to **192**; **45** definitions were added and **0** removed.

| Model | Relevance | Public wire role | Required fields | Other fields | Guide |
| --- | --- | --- | --- | --- | --- |
| `AIObjectiveEntry` | `direct-operation` | A named objective that maps requests to critical, standard, or sheddable class; same-class numeric order is not retained. | `name:string` | `priority:integer(int32)`, `services:array<string>`, `updated_at:string(date-time)` | [Details](../ai-gateway/ai-traffic-governance.md#network-identity-and-objective-api-contracts) |
| `AiModelProfileEntry` | `direct-operation` | One published model profile returned by detail lookup and nested in the registry list. | `profileId:string`, `gen:integer(uint64)`, `baseModel:string`, `aliasPolicy:string{base_model_only/list}`, `supportedApis:array<string>`, `tokenizerSha256:string` | `allowedAliases:array<string>`, `excludedFeatures:array<string>`, `oracleEngine:string`, `oracleVersion:string`, `rendererEngine:string`, `rendererVersion:string`, `supportedFeatures:array<string>`, `templateContentFormat:string`, `templateSha256:string`, `tokenizerRevision:string` | [Details](../ai-gateway/model-profiles-kv-readiness.md) |
| `AiModelProfileRegistry` | `direct-operation` | Read-only registry generation, set digest, and published profile list. | `registryGeneration:integer(uint64)`, `profiles:array<AiModelProfileEntry>` | `setDigest:string` | [Details](../ai-gateway/model-profiles-kv-readiness.md) |
| `AuditDropCount` | `nested-component` | One dropped-record counter, by stream and reason, nested in the audit status. | none | `count:integer(int64)`, `reason:string`, `stream:string` | [Details](../operations/audit-log.md) |
| `AuditNamedSink` | `direct-operation` | A secondary audit sink's configuration, selection filter and export state; certificate material is named by path only. | none | `address:string`, `ca_bundle_path:string`, `client_cert_path:string`, `client_key_path:string`, `cursor:AuditSinkCursor`, `enterprise_number:integer(int64)`, `facility:integer(int64)`, `filter:AuditSinkFilter`, `filtered:integer(int64)`, `lag_drops:integer(int64)`, `last_error:string`, `max_frame_bytes:integer(int64)`, `name:string`, `poison:integer(int64)`, `resent:integer(int64)`, `server_name:string`, `state:string`, `submitted:integer(int64)`, `truncated:integer(int64)`, `write_errors:integer(int64)`, `xseq_epoch:integer(int64)`, `xseq_high:integer(int64)` | [Details](../operations/audit-log.md) |
| `AuditPolicy` | `direct-operation` | The runtime-changeable audit policy: segment sealing limits and the local retention target. | none | `max_segment_age_seconds:integer(int64)`, `max_segment_bytes:integer(int64)`, `retention_max_age_seconds:integer(int64)`, `retention_max_bytes:integer(int64)`, `retention_max_prune_per_pass:integer(int64)`, `retention_reserve_bytes:integer(int64)` | [Details](../operations/audit-log.md) |
| `AuditProducerStatus` | `nested-component` | Per-producer record accounting nested in the audit status. | none | `accepted:integer(int64)`, `drop_ring_overflows:integer(int64)`, `dropped:object`, `id:string`, `pseq_high:integer(int64)`, `stream:string` | [Details](../operations/audit-log.md) |
| `AuditRetentionPolicy` | `nested-component` | The retention policy in force, nested in the audit status. | none | `max_age_seconds:integer(int64)`, `max_bytes:integer(int64)`, `reserve_bytes:integer(int64)` | [Details](../operations/audit-log.md) |
| `AuditRotateResult` | `direct-operation` | The segments either side of an operator-requested rotation. | none | `new_segment_uuid:string`, `sealed_segment_uuid:string` | [Details](../operations/audit-log.md) |
| `AuditSegmentStatus` | `nested-component` | The active segment the audit writer is appending to, nested in the audit status. | none | `bytes:integer(int64)`, `opened:string`, `records:integer(int64)`, `uuid:string` | [Details](../operations/audit-log.md) |
| `AuditSink` | `direct-operation` | The remote syslog sink's configuration and session state; certificate material is named by path only. | none | `address:string`, `ca_bundle_path:string`, `client_cert_path:string`, `client_key_path:string`, `connected:boolean`, `enabled:boolean`, `facility:integer(int64)`, `last_error:string`, `max_frame_bytes:integer(int64)`, `server_name:string`, `submitted:integer(int64)`, `truncated:integer(int64)`, `write_errors:integer(int64)` | [Details](../operations/audit-log.md) |
| `AuditSinkCursor` | `nested-component` | A place in the audit trail, the last record a sink is past, nested in sink state. | none | `segment_uuid:string`, `seq:integer(int64)` | [Details](../operations/audit-log.md) |
| `AuditSinkFilter` | `nested-component` | What a secondary sink selects from the trail: streams, services, outcome and a data sample rate. | none | `data_sample:integer(int64)`, `outcome:string`, `services:array<string>`, `streams:array<string>` | [Details](../operations/audit-log.md) |
| `AuditSinkStatus` | `nested-component` | One sink's progress through the trail, listed in the audit status. | none | `compliance:boolean`, `cursor:AuditSinkCursor`, `in_active_segment:boolean`, `lag_drops:integer(int64)`, `lag_records:integer(int64)`, `name:string`, `state:string` | [Details](../operations/audit-log.md) |
| `AuditStatus` | `direct-operation` | State of the management audit trail: writer liveness, counters, active segment, retention, and orphaned intents. | none | `accepted:object`, `available:boolean`, `boot_id:string`, `compliance_sink:boolean`, `compress_failed:integer(int64)`, `compress_skipped:integer(int64)`, `delegation_lookups:integer(int64)`, `dropped:array<AuditDropCount>`, `heartbeats:integer(int64)`, `last_orphan_event_id:string`, `last_write:string`, `mgmt_timeouts:integer(int64)`, `originator_dropped:integer(int64)`, `orphaned_intents:integer(int64)`, `panics:integer(int64)`, `path_sanitized:integer(int64)`, `perm_repaired:integer(int64)`, `producers:array<AuditProducerStatus>`, `projected_retention_days:number(double)`, `pruned:integer(int64)`, `queue_depth:object`, `queue_hwm:object`, `reserve_breached:boolean`, `reserve_breaches:integer(int64)`, `restarts:integer(int64)`, `result_drops:integer(int64)`, `retention:AuditRetentionPolicy`, `rotation_failed:integer(int64)`, `rotations:integer(int64)`, `running:boolean`, `sealed_bytes:integer(int64)`, `segment:AuditSegmentStatus`, `seq_high:integer(int64)`, `sinks:array<AuditSinkStatus>`, `sync_failures:integer(int64)`, `unattributed:integer(int64)`, `write_failures:integer(int64)` | [Details](../operations/audit-log.md) |
| `AutoPersistStatus` | `nested-component` | Auto-persist failure streak nested in readiness and diagnostics responses. | none | `consecutive_failures:integer`, `last_attempt:string(date-time)`, `last_error:string` | [Details](../operations/backup-restore.md) |
| `BootStatus` | `nested-component` | Boot replay, quarantine, legacy fallback, and degraded-state evidence. | `snapshot_found:boolean`, `succeeded:boolean`, `legacy_fallback:boolean`, `degraded:boolean` | `generation:integer(uint64)`, `profile:string`, `quarantine_path:string`, `reasons:array<string>` | [Details](../operations/backup-restore.md) |
| `CapabilityStatus` | `nested-component` | One optional capability verdict with a stable reason code and operator-facing reason. | `name:string`, `ready:boolean` | `in_use:integer(int64)`, `limit:integer(int64)`, `reason:string`, `reason_code:string` | [Details](../operations/readiness-diagnostics-maintenance.md) |
| `CapabilityStatusList` | `direct-operation` | Envelope returned by the optional capability readiness endpoint. | `capabilities:array<CapabilityStatus>` | none | [Details](../operations/readiness-diagnostics-maintenance.md) |
| `CertCreated` | `direct-operation` | Answer to a certificate create: the certId the entry is stored under, named by the request or minted by the gateway. | `certId:string` | none | [Details](../security/backend-tls.md) |
| `ConfigOpRecord` | `nested-component` | Generation, checksum, mode, and time identity for the last successful persist or restore. | none | `at:string(date-time)`, `checksum:string`, `generation:integer(uint64)`, `mode:string` | [Details](../operations/backup-restore.md) |
| `DependencyDiagnostic` | `nested-component` | Sanitized dependency type, requirement, status, and latency class in diagnostics. | `type:string`, `required:boolean`, `status:string{ready/failed}`, `latency_class:string{fast/slow/failed}` | none | [Details](../operations/readiness-diagnostics-maintenance.md) |
| `DiagnosticsStatus` | `direct-operation` | Bounded diagnostic response covering build, readiness, maintenance, datapath, and dependencies. | `version:string`, `uptime_seconds:integer(int64)`, `ready:boolean`, `maintenance_state:string{active/maintenance}` | `api_version:string`, `auto_persist:AutoPersistStatus`, `boot:BootStatus`, `build_info:string`, `ebpf_attachments:array<EbpfAttachmentStatus>`, `external_dependencies:array<DependencyDiagnostic>`, `last_persist:ConfigOpRecord`, `last_restore:ConfigOpRecord`, `maps:array<MapUtilization>`, `product:string`, `ready_reasons:array<string>` | [Details](../operations/readiness-diagnostics-maintenance.md) |
| `EbpfAttachmentStatus` | `nested-component` | One observable eBPF hook attachment fact nested in readiness or diagnostics. | `name:string`, `mode:string{tc/xdp}`, `attached:boolean` | none | [Details](../operations/readiness-diagnostics-maintenance.md) |
| `ExternalDependencyStatus` | `nested-component` | Credential-free identity and disposition of one external recovery dependency. | none | `digest:string`, `generation:string`, `id:string`, `required:boolean`, `status:string{ready/configured/verified/warning/failed/declared}`, `type:string` | [Details](../operations/backup-restore.md) |
| `FcBandEffective` | `nested-component` | Read-only per-band inflight, queued, wait, queue-share, floor, and weighted-wake observations nested in fc_effective.bands; not a configuration payload. | none | `floor_units:integer(int32)`, `inflight:integer(int32)`, `min_share_pct:integer(int32)`, `queue_pct:integer(int32)`, `queued:integer(int32)`, `wait_ms:integer(int32)`, `weight:integer(int32)`, `weight_pct:integer(int32)` | [Details](../ai-gateway/configuration-reference.md) |
| `FilesystemStatus` | `direct-operation` | Formal schema for the existing filesystem-status response. | none | `filesystemAttr:array<FileSystemInfoEntry>` | [Details](api.md) |
| `HalfCloseConfig` | `direct-operation` | The process-wide half-close hold settings: whether new holds may be taken and the idle bound on a hold. | none | `allow:boolean`, `capSeconds:integer(int32)`, `defaultMode:string` | [Details](../ai-gateway/configuration-reference.md#half-close-hold-half_close_mode) |
| `JWTAuthProfileEntry` | `direct-operation` | Named data-plane JWT issuer, JWKS, claim mapping, algorithm, and forwarding policy. | `name:string`, `issuer:string` | `algs:array<string>`, `audiences:array<string>`, `authorization_passthrough:boolean`, `default_tenant:string`, `forward_identity:boolean`, `jwks_url:string`, `leeway_sec:integer(int64)`, `model_authz:string{claims-required/allow-all}`, `model_role_prefix:string`, `models_claim:string`, `priority_class:string{standard/critical/sheddable}`, `refresh_sec:integer(int64)`, `roles_claim:string`, `tenant_claim:string`, `user_claim:string`, `username_claim:string` | [Details](../security/data-plane-jwt-auth.md) |
| `KvExactEnforcement` | `nested-component` | Desired versus acknowledged KV-exact enforcement and migration-fence state. | `desired:string`, `enforced:string` | `fault:string`, `goFenced:boolean`, `lastAckAt:string` | [Details](../ai-gateway/model-profiles-kv-readiness.md) |
| `KvExactStatusEntry` | `direct-operation` | Resolved rule, profile, engine-contract, binding, and enforcement readiness status. | `ruleIdentity:string`, `modelName:string`, `engineFamily:string`, `apiMode:string`, `desiredState:string`, `enforcedState:string`, `reasonCodes:array<string>` | `bindingDigest:string`, `bindingGen:integer(uint32)`, `enforcement:KvExactEnforcement`, `engineContractGen:integer(uint64)`, `engineContractId:string`, `hashContractId:string`, `modelProfileGen:integer(uint64)`, `modelProfileId:string`, `pdDialectId:string`, `requiredEvidenceLevel:string`, `wireSchemaId:string` | [Details](../ai-gateway/model-profiles-kv-readiness.md) |
| `MaintenanceRequest` | `direct-operation` | Requested maintenance state and optional drain timeout. | `enabled:boolean` | `drain_timeout_seconds:integer(uint32)` | [Details](../operations/readiness-diagnostics-maintenance.md) |
| `MaintenanceStatus` | `direct-operation` | Observed maintenance, refusal, in-flight stream, deadline, and cancellation state. | `state:string{active/maintenance}`, `refusing_new_config:boolean`, `refusing_new_inference:boolean`, `cancellable:boolean`, `in_flight_streams:integer(int64)`, `elapsed_seconds:integer(int64)`, `drain_deadline_exceeded:boolean` | `drain_timeout_seconds:integer(uint32)`, `entered_at:string(date-time)`, `in_flight_requests:integer(int64)`, `operation_id:string` | [Details](../operations/readiness-diagnostics-maintenance.md) |
| `MapUtilization` | `nested-component` | Bounded datapath-map count and capacity without exposing entry contents. | `name:string`, `count:integer(int64)`, `capacity:integer(int64)` | none | [Details](../operations/readiness-diagnostics-maintenance.md) |
| `NetIdentityEntry` | `direct-operation` | A node-local network-to-tenant attribution binding, with service/model scope and credential handling; network attribution is not authentication. | `name:string`, `match:object`, `tenant:string` | `allowed_models:array<string>`, `credential:string{none/network}`, `enforce:string{advisory/strict}`, `fail_mode:string{neutral/closed}`, `forward_identity:boolean`, `priority_class:string{standard/critical/sheddable}`, `services:array<string>` | [Details](../ai-gateway/ai-traffic-governance.md#network-identity-and-objective-api-contracts) |
| `OperationResult` | `shared-envelope` | Common informational result body returned by successful configuration mutations. | none | `result:string` | [Details](api.md) |
| `ProcessStatus` | `direct-operation` | Formal schema for the existing per-process CPU status response. | none | `processAttr:array<ProcessInfoEntry>` | [Details](api.md) |
| `RateLimitDefaultsEntry` | `direct-operation` | Stored global or rule-scoped QoS defaults with update metadata. | `scope:string{global/rule}` | `default_tenant_rps:integer(int64)`, `default_tenant_tpm:integer(int64)`, `default_user_rps:integer(int64)`, `default_user_tpm:integer(int64)`, `rule_ident:string`, `updated_at:string(date-time)`, `vip_shared_rps:integer(int64)`, `vip_shared_tpm:integer(int64)` | [Details](../operations/ai-qos.md) |
| `RateLimitDefaultsMod` | `direct-operation` | Replacement request for global or rule-scoped user, tenant, and shared-VIP defaults. | `scope:string{global/rule}` | `default_tenant_rps:integer(int64)`, `default_tenant_tpm:integer(int64)`, `default_user_rps:integer(int64)`, `default_user_tpm:integer(int64)`, `rule_ident:string`, `vip_shared_rps:integer(int64)`, `vip_shared_tpm:integer(int64)` | [Details](../operations/ai-qos.md) |
| `ReadyStatus` | `direct-operation` | Configuration-readiness verdict plus boot, dependency, persistence, and eBPF evidence. | `ready:boolean` | `auto_persist:AutoPersistStatus`, `boot:BootStatus`, `ebpf_attachments:array<EbpfAttachmentStatus>`, `external_dependencies:array<ExternalDependencyStatus>`, `last_persist:ConfigOpRecord`, `last_restore:ConfigOpRecord`, `reasons:array<string>` | [Details](../operations/readiness-diagnostics-maintenance.md) |
| `SockMapResetResult` | `direct-operation` | Count of accelerated live connections closed by a service-scoped reset. | none | `droppedConnections:integer` | [Details](../operations/sockmap-acceleration.md) |
| `UserModelRateLimit` | `nested-component` | One model-specific token quota nested in a user's QoS row. | none | `model:string`, `tokens_per_min:integer(int64)` | [Details](../operations/ai-qos.md) |
| `UserRateLimitEntry` | `direct-operation` | Stored per-user RPS, burst, aggregate TPM, and per-model quota row. | `tenant_id:string`, `user_id:string` | `burst_size:integer(int64)`, `model_limits:array<UserModelRateLimit>`, `rps:integer(int64)`, `tokens_per_min:integer(int64)`, `updated_at:string(date-time)` | [Details](../operations/ai-qos.md) |
| `UserRateLimitMod` | `direct-operation` | Replacement request for a user's explicit and per-model quota rows. | `tenant_id:string`, `user_id:string` | `burst_size:integer(int64)`, `model_limits:array<UserModelRateLimit>`, `rps:integer(int64)`, `tokens_per_min:integer(int64)` | [Details](../operations/ai-qos.md) |
| `UserSummary` | `direct-operation` | Source-declared account identity fields. | none | `created_at:string`, `delegation_allowed:boolean`, `id:integer`, `role:string{admin/viewer}`, `username:string` | [Details](../security/management-api-authentication.md) |

## `api/swagger-extras.yml`

[Open the exact source](https://github.com/loxilb-io/loxilb-inference-gateway/blob/c7b4af87f1eda7db1a6667aa797e1d3b389d21cc/api/swagger-extras.yml). Definition count changed from **2** to **4**; **2** definitions were added and **0** removed.

| Model | Relevance | Public wire role | Required fields | Other fields | Guide |
| --- | --- | --- | --- | --- | --- |
| `ManagementError` | `companion-error` | Structured management authentication, authorization, and credential-store error for raw handlers. | none | `code:integer(int32)`, `fields:array<string>`, `message:string`, `result:string` | [Details](swagger-extras.md) |
| `RawError` | `companion-error` | Union-compatible description of the two JSON error envelope shapes used by raw handlers. | none | `code:integer(int32)`, `error:string`, `fields:array<string>`, `message:string`, `result:string` | [Details](swagger-extras.md) |

## Review boundary

All added definitions are public-relevant: each is a direct operation
model, a nested component needed to interpret one, a shared success
envelope, or a companion-spec error contract. None is classified as an
internal-only model. This classification is about API documentation
coverage, not proof that every endpoint is available in the latest release.

Machine-readable field constraints remain authoritative in the exact
Swagger source. The linked guides explain sequencing, security boundaries,
negative behavior, and release limitations that a schema alone cannot express.
