# Changelog

All notable changes to the documentation site are recorded here. Versioned
snapshots of the site are published on `v*` tags via [mike](https://github.com/jimporter/mike);
this file explains what changed between them.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Endpoint Picker use-case family: deploy vLLM, the Gateway API Inference
  Extension Endpoint Picker and loxilb-igw from downloadable manifests, create
  the EPP rule directly or through kube-loxilb (`InferencePool` + `HTTPRoute`),
  a four-point smoke test, switching between EPP, CHWBL and round robin,
  observability, a reproduction harness, troubleshooting and teardown, plus the
  measurements of the three routing modes (cache reuse, TTFT, throughput,
  failure modes) with the raw results archive.
  The vLLM manifest starts the pods with `--enable-prompt-tokens-details`, so
  every answer's `usage` block reports the prompt tokens served from the
  prefix cache.
- Backend TLS Verification and Client Certificates page: certificate registry
  entries by usage (`ca`, `client`), `mtls_backend.verify_server_cert`,
  `backend_ca_cert_id`, `backend_client_cert_id`, `backend_tls_server_name`,
  the read-only `backend_tls_effective` state, the `backend_tls_verify`
  capability, in-place policy changes, certificate rotation, and the upgrade
  notes for the retired `mtls_backend` path and inline-material arguments.
  The frontend mTLS page, configuration reference, running modes, CLI
  reference and troubleshooting no longer describe backend verification as
  not wired.
- Admission Flow Control guide: the per-rule capacity admission gate
  (`fc_mode`, ceilings, bounded queue, adaptive ceiling, warm-up, tenant fair
  share, admission headers), its refusal codes, configuration examples for
  `curl` and `loxicmd`, metrics and troubleshooting. The `fc_*` fields,
  `loxicmd create lb --fc-*` flags, admission metrics, and maintenance drain
  behavior are reflected in the configuration reference, CLI reference,
  monitoring, troubleshooting, and readiness/maintenance pages.
- Open-source project scaffolding: governance, maintainers, contributing guide
  (with DCO and Conventional Commits policy), full Contributor Covenant v2.1
  code of conduct, security policy, issue/PR templates, Dependabot, CI
  (hygiene, strict build, link check, secret scan), and mike-versioned deploys.
- Documentation for the AI gateway feature set: model load balancing, LLM
  routing, KV-cache-aware routing, P/D disaggregation, vLLM/SGLang
  integration, SSE & quota management, API key management, MCP gateway, and
  the full configuration reference.
- Security guides (OPA L4 policy, mTLS for AI backends), operations guides
  (monitoring, Grafana, troubleshooting, audit logging), management-plane
  guides (LoxiLB UI, OAM API), and reference pages (API, CLI, system
  requirements).

### Changed

- Tracked Gateway contract refreshed from `c7b4af8` to `b954a57`: read-only EPP
  connection state on a rule read (`eppState`, `eppStateSince`,
  `eppLastError`), an EPP on a `pd_disagg_mode` rule now requires
  `eppFailureMode=FailOpen`, regenerated metric manifest and a new eBPF pin;
  generated reference pages and the verification-status tuple follow.
- Load-balancer rules: what a `POST` for an existing rule does (which omitted
  fields a replace keeps, what is applied in place, what restarts), and the
  refusals of a create or a replace (`400` naming `externalIP` or
  `tls_ciphers`, `409 lbrule-exists`, `412 LB_DATAPLANE_INSTALL_FAILED`).
  `tls_ciphers` states that the one string must serve TLS 1.3 and TLS 1.2.
  `POST /config/cert` answers with the `certId`. A rule read reports the
  member timeouts, the TLS-tuning fields and `mtls_frontend.client_crl_path`.

- Prepare a Supported Model: TensorRT-LLM as a single pool. The installer's
  `--engine trtllm`, the per-engine probe sets, the engine options file and
  launch line, block size 32, and the readiness causes specific to that
  engine. TensorRT-LLM Integration: a strict rule with a model profile, the
  engine's Prometheus path (`/prometheus/metrics`; `/metrics` is a queue a
  read empties), and the restart that exits with `Address already in use`.

- Backend TLS page and troubleshooting: a rule whose endpoints turn the
  gateway away after the TLS handshake (no client certificate named, or one
  they do not accept) now answers `502` (HTTP/1.1) or `503` (HTTP/2)
  `backend_unreachable` with a complete response and a data plane log line,
  where the connection was closed without an answer; and a backend TLS policy
  change or certificate rotation now closes kept-alive HTTP/1.1 client
  connections of a relaying rule once nothing is owed on them (at the latest
  after 30 seconds), where re-creating the rule was advised.
- Documentation hardening ahead of the public release: placeholder
  credentials in examples, production TLS-verification guidance, OPA server
  hardening notes, checksum guidance for third-party downloads, and corrected
  implementation-status notes verified against the gateway source.
