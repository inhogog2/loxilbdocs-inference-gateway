from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_examples", ROOT / "tools/validate_examples.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
ExampleValidator = MODULE.ExampleValidator


class DocumentationExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = ExampleValidator(ROOT)

    def test_all_normal_fixtures_pass(self) -> None:
        report = self.validator.validate_repository()
        self.assertEqual([], report.errors, "\n".join(report.errors))

    def test_public_scan_honors_mkdocs_exclusions_and_negations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "mkdocs.yml").write_text(
                "docs_dir: public\nexclude_docs: |\n"
                "  internal/\n  **/CLAUDE.md\n  drafts/\n  !drafts/released.md\n"
                "markdown_extensions:\n"
                "  - custom: !!python/name:unavailable.module.function\n"
            )
            names = (
                "public/index.md", "public/internal/private.md",
                "public/internal/nested/private.md", "public/CLAUDE.md",
                "public/nested/CLAUDE.md", "public/drafts/private.md",
                "public/drafts/released.md", "snippets/common/visible.md",
            )
            for name in names:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# Fixture\n\n```bash\nprintf 'example\\n'\n```\n")
            expected = {
                "public/index.md", "public/drafts/released.md",
                "snippets/common/visible.md",
            }
            self.assertEqual(
                {path.relative_to(root).as_posix() for path in MODULE.public_markdown_paths(root)},
                expected,
            )
            self.assertEqual(
                {block.path.as_posix() for _, block, _ in MODULE.collect_public_blocks(root)},
                expected,
            )

    def test_excluding_internal_docs_does_not_hide_public_address_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "mkdocs.yml").write_text("exclude_docs: |\n  internal/\n")
            for name in ("docs/internal/private.md", "docs/public.md"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Example address: " + "10." + "0.0.7\n")
            report = ExampleValidator(root, contract_dir=ROOT / "tests/contracts/docs_examples").validate_repository()
            address_errors = [error for error in report.errors if "RFC1918 host address" in error]
            self.assertEqual(len(address_errors), 1)
            self.assertTrue(address_errors[0].startswith("docs/public.md:"))

    def test_red_twin_unclassified_example_is_killed(self) -> None:
        inventory = json.loads(
            (ROOT / "tests/contracts/docs_examples/example-inventory.json").read_text()
        )
        inventory["entries"].pop()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example-inventory.json"
            path.write_text(json.dumps(inventory))
            report = MODULE.ValidationReport()
            self.validator.validate_inventory(
                MODULE.collect_public_blocks(ROOT), report, path
            )
        self.assertTrue(
            any("example is not classified in inventory" in error for error in report.errors),
            "missing example classification must fail closed",
        )

    def test_red_twin_duplicate_example_is_killed(self) -> None:
        collected = MODULE.collect_public_blocks(ROOT)
        identity, block, digest = collected[0]
        report = MODULE.ValidationReport()
        self.validator.validate_inventory(
            collected + [(f"duplicate-{identity}", block, digest)], report
        )
        self.assertTrue(
            any("must use a canonical snippet" in error for error in report.errors),
            "duplicate examples must fail closed",
        )

    def test_mutating_examples_have_enforced_contracts(self) -> None:
        inventory = json.loads(
            (ROOT / "tests/contracts/docs_examples/example-inventory.json").read_text()
        )
        mutations = [
            entry for entry in inventory["entries"]
            if entry.get("mutation_contract", {}).get("detected")
        ]
        self.assertGreater(len(mutations), 0)
        for entry in mutations:
            with self.subTest(example=entry["id"]):
                contract = entry["mutation_contract"]
                self.assertTrue(contract["independent_oracle"])
                self.assertTrue(contract["negative_no_mutation"])
                self.assertTrue(contract["active_path"])
                self.assertTrue(contract["cleanup"])
                self.assertTrue(contract["cleanup_verification"])
                if contract["mode"] == "illustrative-fragment":
                    self.assertEqual("illustrative-only", entry["status"])

    def test_red_twin_missing_mutation_oracle_is_killed(self) -> None:
        inventory = json.loads(
            (ROOT / "tests/contracts/docs_examples/example-inventory.json").read_text()
        )
        mutation = next(
            entry for entry in inventory["entries"]
            if entry.get("mutation_contract", {}).get("detected")
        )
        mutation["mutation_contract"]["independent_oracle"] = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example-inventory.json"
            path.write_text(json.dumps(inventory))
            report = MODULE.ValidationReport()
            self.validator.validate_inventory(
                MODULE.collect_public_blocks(ROOT), report, path
            )
        self.assertTrue(
            any("lacks contract fields" in error for error in report.errors),
            "missing independent oracle must fail closed",
        )

    def test_red_twin_mutation_fragment_cannot_be_promoted(self) -> None:
        inventory = json.loads(
            (ROOT / "tests/contracts/docs_examples/example-inventory.json").read_text()
        )
        fragment = next(
            entry for entry in inventory["entries"]
            if entry.get("mutation_contract", {}).get("mode") == "illustrative-fragment"
        )
        fragment["status"] = "verified"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example-inventory.json"
            path.write_text(json.dumps(inventory))
            report = MODULE.ValidationReport()
            self.validator.validate_inventory(
                MODULE.collect_public_blocks(ROOT), report, path
            )
        self.assertTrue(
            any("fragment must be illustrative-only" in error for error in report.errors),
            "a mutation fragment must not become a false-green verified workflow",
        )

    def test_red_twin_rfc1918_host_address_is_killed(self) -> None:
        self.assertEqual(
            ["10.23.45.67"],
            self.validator.private_example_addresses(
                "send traffic to 10.23.45.67 after configuration"
            ),
        )

    def test_named_rfc1918_networks_remain_valid_policy_terms(self) -> None:
        self.assertEqual(
            [],
            self.validator.private_example_addresses(
                "deny 10.0.0.0/8, 172.16.0.0/12, and 192.168.0.0/16"
            ),
        )

    def test_mutation_detector_covers_rest_and_cli(self) -> None:
        rest = MODULE.Block(
            Path("docs/example.md"), 1, "bash",
            'curl --request PATCH "$CONTROL_API/config/ai/apikey/example"',
        )
        cli = MODULE.Block(
            Path("docs/example.md"), 2, "bash",
            "loxicmd delete lb 192.0.2.10 --tcp=8080",
        )
        self.assertEqual(
            ["PATCH /config/ai/apikey/example"],
            self.validator.mutation_operations(rest),
        )
        self.assertEqual(
            ["loxicmd delete lb"],
            self.validator.mutation_operations(cli),
        )
        appliance = MODULE.Block(
            Path("docs/example.md"), 3, "bash",
            "loxicmd appliance restore execute ./plan.json --challenge-file ./challenge",
        )
        self.assertEqual(
            ["loxicmd appliance restore execute"],
            self.validator.mutation_operations(appliance),
        )

    def test_red_twin_route_typo_is_killed(self) -> None:
        errors = self.validator.validate_route("POST", "/config/workre/metrics")
        self.assertTrue(errors)

    def test_red_twin_removed_flag_is_killed(self) -> None:
        errors = self.validator.validate_cli_command(
            "loxicmd create lb 192.0.2.10 --tcp=8080:8000 "
            "--endpoints=198.51.100.11:1 --removed-flag=true"
        )
        self.assertTrue(errors)

    def test_release_metric_manifest_is_frozen_without_missing_writers(self) -> None:
        manifest = self.validator.gateway_contract["metric_manifest"]
        families = [
            family for family in manifest["families"]
            if family["release_scope"] == "release"
        ]
        self.assertEqual(298, len(families))
        self.assertEqual(298, len(manifest["families"]))
        # Upstream labels scrape-time GaugeFuncs (api/prometheus/ai_metrics.go)
        # definition-only because nothing writes them ahead of a scrape. Any
        # other release family without a writer is still a failure.
        missing_writers = sorted(f["name"] for f in families if not f["writer_present"])
        self.assertEqual(["loxilb_ai_epp_inflight", "loxilb_ai_epp_pending"], missing_writers)
        self.assertTrue(all(f["implementation_status"] == "definition-only"
                            for f in families if not f["writer_present"]))
        self.assertTrue(all(family["evidence_present"] for family in families))

    def test_gateway_main_and_release_sources_are_exactly_frozen(self) -> None:
        contract = self.validator.gateway_contract
        self.assertEqual(
            "c7b4af87f1eda7db1a6667aa797e1d3b389d21cc",
            contract["source"]["commit"],
        )
        self.assertEqual(
            "f00d8b3f7de5b70e3971167a791ce5a3cf5d78e4",
            contract["source"]["ebpf_submodule_commit"],
        )
        self.assertEqual("v0.9.8.9-rc.1", contract["source"]["release_tag"])
        self.assertEqual(
            "f08b18beda587217265c9ba6419159119914795c",
            contract["source"]["release_commit"],
        )
        self.assertFalse(contract["release_snapshot"]["metric_manifest_available"])
        self.assertEqual(
            "5536a2117ad2ad1128900a0d808ad7dec2eee2b5",
            contract["release_snapshot"]["ebpf_submodule_commit"],
        )

    def test_cli_main_and_release_sources_are_exactly_frozen(self) -> None:
        source = self.validator.cli_contract["source"]
        self.assertEqual(
            "28832f0c60ab717d8cb5133114edf2c45e22a85c",
            source["main_commit"],
        )
        self.assertEqual("v0.9.8.9-rc.2", source["release_tag"])
        self.assertEqual(
            "2dd7dbe215982859c2ee5cfc836fe34ac4e54a37",
            source["release_tag_object"],
        )
        self.assertEqual(
            "5dd978c25c967b8192c5fe9cd448783e1e74be7c",
            source["release_commit"],
        )

    def test_public_metric_fixture_omits_raw_writer_and_evidence_text(self) -> None:
        allowed = {
            "name", "type", "labels", "activation", "release_scope",
            "runtime_scope", "implementation_status", "writer_present",
            "evidence_present",
        }
        for family in self.validator.gateway_contract["metric_manifest"]["families"]:
            with self.subTest(metric=family["name"]):
                self.assertEqual(allowed, set(family))
        serialized = json.dumps(self.validator.gateway_contract).lower()
        private_markers = (
            "work-" "package",
            "w" "p-5",
            "llbig" "w",
            "loxilb" "-app",
        )
        for private_marker in private_markers:
            with self.subTest(private_marker=private_marker):
                self.assertNotIn(private_marker, serialized)

    def test_public_claim_evidence_membership_and_cases_are_frozen(self) -> None:
        claims = {
            claim["claim"]: claim
            for claim in self.validator.gateway_contract["claim_evidence"]["claims"]
        }
        self.assertEqual("wired", claims["jwt-policy-and-token-accounting"]["workflow_membership"])
        self.assertEqual("wired", claims["qos-ha-and-scope-metrics"]["workflow_membership"])
        self.assertEqual("wired", claims["pd-and-worker-scrape-metrics"]["workflow_membership"])
        self.assertEqual("not-wired", claims["sockmap-observability"]["workflow_membership"])
        self.assertEqual(
            [".github/workflows/ai-gateway-sanity.yml"],
            claims["jwt-policy-and-token-accounting"]["matching_workflows"],
        )
        self.assertEqual([".github/workflows/ha-two-node-nightly.yml"], claims["qos-ha-and-scope-metrics"]["matching_workflows"])
        self.assertEqual(
            {
                ".github/workflows/monitoring-drill.yml",
                ".github/workflows/monitoring-e2e.yml",
            },
            set(claims["monitoring-stack"]["matching_workflows"]),
        )
        self.assertEqual(
            {"G2", "M4", "U1", "U2", "UH1", "UH2", "UE", "UE3"},
            set(claims["jwt-policy-and-token-accounting"]["case_ids"]),
        )
        self.assertEqual(
            {"SYNC-1", "SYNC-2", "QOS-METRIC-1", "QOS-METRIC-2", "QOS-HA-013", "QOS-HA-014"},
            set(claims["qos-ha-and-scope-metrics"]["case_ids"]),
        )

    def test_red_twin_metric_typo_is_killed(self) -> None:
        self.assertTrue(self.validator.validate_promql("rate(loxilb_ai_requestz_total[5m])"))

    def test_red_twin_metric_label_is_killed(self) -> None:
        self.assertTrue(
            self.validator.validate_promql(
                'loxilb_ai_worker_scrape_total{worker="198.51.100.11"}'
            )
        )

    def test_red_twin_metric_enum_is_killed(self) -> None:
        self.assertTrue(
            self.validator.validate_promql(
                'loxilb_ai_worker_scrape_total{result="healthy"}'
            )
        )

    def test_release_lifecycle_commands_are_frozen(self) -> None:
        for command in (
            "get snapshot", "create restore", "create persist",
            "get ready", "get diagnostics", "get maintenance",
            "set maintenance", "appliance status",
        ):
            with self.subTest(command=command):
                contract = self.validator.cli_contract["commands"][command]
                self.assertTrue(contract["release"]["available"])
                self.assertTrue(contract["main"]["available"])

    def test_removed_appliance_lifecycle_cannot_be_enabled_by_marker(self) -> None:
        for family, leaves in {
            "restore": ("plan", "execute"), "update": ("plan", "execute", "status"),
            "rollback": ("plan", "execute", "status"), "factory-reset": ("plan", "execute"),
        }.items():
            for leaf in leaves:
                with self.subTest(family=family, leaf=leaf):
                    errors = self.validator.validate_cli_command(
                        f"loxicmd appliance {family} {leaf}", "CLI availability: main-only")
                    self.assertTrue(any("absent" in error for error in errors))

    def test_recovery_operations_are_in_the_swagger_union(self) -> None:
        operations = (
            ("GET", "/config/snapshot"),
            ("POST", "/config/restore"),
            ("POST", "/config/persist"),
            ("GET", "/status/ready"),
            ("GET", "/status/capabilities"),
            ("GET", "/diagnostics"),
            ("GET", "/maintenance"),
            ("PUT", "/maintenance"),
        )
        for method, route in operations:
            with self.subTest(method=method, route=route):
                self.assertEqual([], self.validator.validate_route(method, route))

    def test_engine_kv_and_sockmap_operations_are_in_the_swagger_union(self) -> None:
        operations = (
            ("GET", "/config/ai/model-profiles"),
            ("GET", "/config/ai/model-profiles/example-profile"),
            (
                "GET",
                "/config/loadbalancer/externalipaddress/192.0.2.10/port/8080/protocol/tcp/kvexactstatus",
            ),
            (
                "POST",
                "/config/loadbalancer/externalipaddress/192.0.2.10/port/8080/protocol/tcp/sockmapreset",
            ),
        )
        for method, route in operations:
            with self.subTest(method=method, route=route):
                self.assertEqual([], self.validator.validate_route(method, route))

    def test_engine_support_catalog_exact_tuples_are_frozen(self) -> None:
        entries = self.validator.gateway_contract["support_catalog"]["entries"]
        tuples = {
            (
                entry["engine"],
                entry["version"],
                entry.get("revision", ""),
                entry.get("image", {}).get("platformDigest", ""),
                entry["gatewayRelease"],
                entry["profile"],
                entry["promotion"],
            )
            for entry in entries
        }
        self.assertEqual(
            {
                ("vllm", "v0.23.0", "", "", "v0.9.8.9-rc.1", "vllm-kv-array-v1", "candidate"),
                (
                    "vllm", "v0.28.0", "2cf0a6915ce544dc493a0990f2ea38d81601128a",
                    "sha256:61fc8a896b0a4fbbbdc063bc4b0dbc25ce98e02b5050c24aeb7830ac02039b14",
                    "v0.9.8.9-rc.1", "vllm-kv-map-v2", "validated",
                ),
                (
                    "sglang", "v0.5.18", "71de97b264b04dcd514cf904003028aefe9775c8",
                    "sha256:9e148f5ac788e856a06166bd6347a831831eb9fcfab4d1770874823a7c29a1a1",
                    "v0.9.8.9-rc.1", "sglang-kv-rank-v1", "validated",
                ),
                ("trtllm", "v1.2.1", "", "", "v0.9.8.9-rc.1", "trtllm-kv-http-v1", "candidate"),
                (
                    "trtllm", "1.3.0rc24", "1cef02e901be43081b1ba6d4981e94ed3bd9c1e8",
                    "sha256:a867619fd56c85225927dac27e2111ae90ff66e23c59d9c5f8b9f345577cab6d",
                    "v0.9.8.9-rc.1", "trtllm-kv-http-preview-v1", "validated",
                ),
                ("llamacpp", "v0.3.0", "", "", "v0.9.8.9-rc.1", "llamacpp-nokv-v1", "candidate"),
            },
            tuples,
        )

    def test_validated_catalog_tuples_have_real_engine_evidence(self) -> None:
        entries = self.validator.gateway_contract["support_catalog"]["entries"]
        for entry in entries:
            if entry["promotion"] != "validated":
                continue
            with self.subTest(engine=entry["engine"], version=entry["version"]):
                self.assertTrue(entry["revision"])
                self.assertTrue(entry.get("image", {}).get("platformDigest"))
                for capability in entry["capabilities"].values():
                    self.assertEqual("pass", capability["evidence"]["realEngine"])

    def test_required_engine_scenario_sources_are_frozen(self) -> None:
        trees = {
            entry["path"]
            for entry in self.validator.gateway_contract["scenario_evidence"]["trees"]
        }
        self.assertEqual(
            {
                "cicd/kv-mixed-version",
                "cicd/kv-profile-admission",
                "cicd/kv-sglang-attest",
                "cicd/sockmap-fullproxy",
                "cicd/vllm-kvcache-routing-cpu",
                "cicd/vllm-pd-admission-cpu",
            },
            trees,
        )

    def test_admission_flags_are_main_only_and_enumerated(self) -> None:
        contract = self.validator.cli_contract["commands"]["create lb"]
        for flag in (
            "--fc-mode", "--fc-max-outstanding", "--fc-max-queue-depth",
            "--fc-adaptive", "--fc-tenant-max-share-pct", "--fc-expose-headers",
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, contract["main"]["flags"])
                self.assertNotIn(flag, contract["release"]["flags"])
        self.assertEqual(
            ["off", "observe", "enforce", "inherit"], contract["enums"]["--fc-mode"]
        )
        errors = self.validator.validate_cli_command(
            "loxicmd create lb 192.0.2.10 --tcp=8080:8000 "
            "--endpoints=198.51.100.11:1 --mode=fullproxy --fc-mode=maybe",
            context="CLI availability: main-only",
        )
        self.assertTrue(errors)
        errors = self.validator.validate_cli_command(
            "loxicmd create lb 192.0.2.10 --tcp=8080:8000 "
            "--endpoints=198.51.100.11:1 --mode=fullproxy --fc-mode=enforce",
        )
        self.assertTrue(errors)  # main-only without the marker

    def test_strict_kv_fields_are_rest_only(self) -> None:
        flags = set(self.validator.cli_contract["commands"]["create lb"]["main"]["flags"])
        self.assertNotIn("--kv-exact-api-mode", flags)
        self.assertNotIn("--kv-model-profile", flags)

    def test_jwt_profile_binding_flag_is_cli_main_only(self) -> None:
        contract = self.validator.cli_contract["commands"]["create lb"]
        self.assertIn("--jwt-auth-profile", contract["main"]["flags"])
        self.assertNotIn("--jwt-auth-profile", contract["release"]["flags"])

    def test_pd_bootstrap_port_is_supported_by_cli_main_and_release(self) -> None:
        contract = self.validator.cli_contract["commands"]["create lb"]
        self.assertIn("--pd-bootstrap-port", contract["main"]["flags"])
        self.assertIn("--pd-bootstrap-port", contract["release"]["flags"])

    def test_strict_kv_field_schema_is_frozen(self) -> None:
        spec = self.validator.gateway_contract["specs"][0]
        fields = spec["definitions"]["LoadbalanceEntry"]["properties"][
            "serviceArguments"
        ]["properties"]
        self.assertEqual(
            {"completions", "chat", "both"}, set(fields["kvExactApiMode"]["enum"])
        )
        self.assertEqual("string", fields["kvModelProfile"]["type"])
        self.assertEqual(
            {"off", "both", "request", "response"}, set(fields["sockMapMode"]["enum"])
        )

    def test_red_twin_kv_api_mode_without_exact_is_killed(self) -> None:
        body = {
            "serviceArguments": {
                "externalIP": "192.0.2.10", "port": 8080, "protocol": "tcp",
                "mode": 4, "kvExactApiMode": "chat",
            },
            "endpoints": [],
        }
        self.assertTrue(
            self.validator.validate_contract_semantics("POST", "/config/loadbalancer", body)
        )

    def test_red_twin_sockmap_with_request_rewrite_is_killed(self) -> None:
        for conflicting in (
            {"sse_mode": True},
            {"pd_disagg_mode": True},
            {"api_key_auth": "disabled"},
            {"api_key_auth": "required"},
            {"api_key_auth": "jwt"},
            {"api_key_auth": "apikey-or-jwt"},
        ):
            with self.subTest(conflicting=conflicting):
                body = {
                    "serviceArguments": {
                        "externalIP": "192.0.2.10", "port": 8080,
                        "protocol": "tcp", "mode": 4, "sockMapMode": "both",
                        **conflicting,
                    },
                    "endpoints": [],
                }
                self.assertTrue(
                    self.validator.validate_contract_semantics(
                        "POST", "/config/loadbalancer", body
                    )
                )

    def test_sockmap_response_with_apikey_keeps_request_admission(self) -> None:
        body = {
            "serviceArguments": {
                "externalIP": "192.0.2.10", "port": 8080,
                "protocol": "tcp", "mode": 4, "sockMapMode": "response",
                "api_key_auth": "required",
            },
            "endpoints": [],
        }
        self.assertEqual(
            [],
            self.validator.validate_contract_semantics(
                "POST", "/config/loadbalancer", body
            ),
        )

    def test_red_twin_sockmap_response_with_sse_is_killed(self) -> None:
        body = {
            "serviceArguments": {
                "externalIP": "192.0.2.10", "port": 8080,
                "protocol": "tcp", "mode": 4, "sockMapMode": "response",
                "sse_mode": True,
            },
            "endpoints": [],
        }
        self.assertTrue(
            self.validator.validate_contract_semantics(
                "POST", "/config/loadbalancer", body
            )
        )

    def test_capability_readiness_contract_is_frozen(self) -> None:
        spec = self.validator.gateway_contract["specs"][0]
        capability = spec["definitions"]["CapabilityStatus"]
        self.assertEqual({"name", "ready"}, set(capability["required"]))
        self.assertEqual("string", capability["properties"]["name"]["type"])
        self.assertNotIn("enum", capability["properties"]["name"])

        capability_list = spec["definitions"]["CapabilityStatusList"]
        self.assertEqual({"capabilities"}, set(capability_list["required"]))
        self.assertEqual(
            "#/definitions/CapabilityStatus",
            capability_list["properties"]["capabilities"]["items"]["$ref"],
        )

    def test_maintenance_requires_explicit_enabled_state(self) -> None:
        errors = self.validator.validate_json_body("PUT", "/maintenance", {})
        self.assertTrue(errors)

    def test_red_twin_wrong_enum_is_killed(self) -> None:
        errors = self.validator.validate_cli_command(
            "loxicmd create lb 192.0.2.10 --tcp=8080:8000 "
            "--endpoints=198.51.100.11:1 --mode=sideways"
        )
        self.assertTrue(errors)

    def test_red_twin_wrong_json_field_casing_is_killed(self) -> None:
        body = {
            "endpointIP": "198.51.100.11:8000",
            "queued_requests": 1,
            "kv_cache_usage_perc": 50,
        }
        errors = self.validator.validate_json_body(
            "POST", "/config/worker/metrics", body
        )
        self.assertTrue(errors)

    def test_red_twin_missing_required_field_is_killed(self) -> None:
        body = {
            "endpoint_ip": "198.51.100.11:8000",
            "kv_cache_usage_perc": 50,
        }
        errors = self.validator.validate_json_body(
            "POST", "/config/worker/metrics", body
        )
        self.assertTrue(errors)

    def test_five_state_credential_contract_is_frozen(self) -> None:
        spec = self.validator.gateway_contract["specs"][0]
        field = spec["definitions"]["LoadbalanceEntry"]["properties"][
            "serviceArguments"
        ]["properties"]["api_key_auth"]
        self.assertEqual(
            {"disabled", "required", "jwt", "apikey-or-jwt"},
            set(field["enum"]),
        )
        self.assertNotIn("default", field)

    def test_companion_apikey_patch_contract_has_all_runtime_fields(self) -> None:
        matches = self.validator.matching_operations(
            "PATCH", "/config/ai/apikey/example-key-id"
        )
        self.assertEqual(2, len(matches))
        body_property_sets = []
        for _, operation in matches:
            for parameter in operation.get("parameters", []):
                if parameter.get("in") == "body":
                    body_property_sets.append(
                        set(parameter.get("schema", {}).get("properties", {}))
                    )
        self.assertIn(
            {
                "allowed_models", "enabled", "rate_limit_rps",
                "burst_size", "tokens_per_min",
                "priority_class", "default_objective", "allowed_objectives",
            },
            body_property_sets,
        )

    def test_objective_only_apikey_patches_are_valid(self) -> None:
        for body in (
            {"priority_class": "standard"},
            {"default_objective": "interactive"},
            {"allowed_objectives": []},
        ):
            with self.subTest(body=body):
                self.assertEqual([], self.validator.validate_json_body(
                    "PATCH", "/config/ai/apikey/example-key-id", body
                ))

    def test_invalid_or_null_only_objective_patch_is_rejected(self) -> None:
        for body in ({"priority_class": "highest"}, {"default_objective": None}):
            with self.subTest(body=body):
                self.assertTrue(self.validator.validate_json_body(
                    "PATCH", "/config/ai/apikey/example-key-id", body
                ))

    def test_red_twin_empty_apikey_patch_is_killed(self) -> None:
        errors = self.validator.validate_json_body(
            "PATCH", "/config/ai/apikey/example-key-id", {}
        )
        self.assertTrue(errors)

    def test_explicit_empty_allowlist_patch_is_not_a_noop(self) -> None:
        errors = self.validator.validate_json_body(
            "PATCH",
            "/config/ai/apikey/example-key-id",
            {"allowed_models": []},
        )
        self.assertEqual([], errors)

    def test_red_twin_jwt_without_profile_is_killed(self) -> None:
        body = {
            "serviceArguments": {"api_key_auth": "jwt"},
            "endpoints": [],
        }
        errors = self.validator.validate_contract_semantics(
            "POST", "/config/loadbalancer", body
        )
        self.assertTrue(errors)

    def test_red_twin_profile_on_required_rule_is_killed(self) -> None:
        body = {
            "serviceArguments": {
                "api_key_auth": "required",
                "jwt_auth_profile": "issuer-a",
            },
            "endpoints": [],
        }
        errors = self.validator.validate_contract_semantics(
            "POST", "/config/loadbalancer", body
        )
        self.assertTrue(errors)

    def test_red_twin_qos_rule_defaults_without_identity_is_killed(self) -> None:
        errors = self.validator.validate_contract_semantics(
            "POST",
            "/config/ai/ratelimit/defaults",
            {"scope": "rule", "default_user_rps": 1},
        )
        self.assertTrue(errors)

    def test_red_twin_empty_user_model_is_killed(self) -> None:
        errors = self.validator.validate_contract_semantics(
            "POST",
            "/config/ai/user/ratelimit",
            {
                "tenant_id": "team-a",
                "user_id": "user-a",
                "model_limits": [{"tokens_per_min": 100}],
            },
        )
        self.assertTrue(errors)

    def test_wrong_limit_type_reports_errors_instead_of_crashing(self) -> None:
        errors = self.validator.validate_json_body(
            "POST",
            "/config/ai/user/ratelimit",
            {
                "tenant_id": "team-a",
                "user_id": "user-a",
                "rps": "not-a-number",
            },
        )
        self.assertTrue(errors)

    def test_red_twin_inline_management_bearer_is_killed(self) -> None:
        errors = self.validator.validate_curl_credential_hygiene(
            "curl -H 'Authorization: Bearer $TOKEN' https://gateway.example.com"
        )
        self.assertTrue(errors)

    def test_red_twin_inline_api_key_is_killed(self) -> None:
        errors = self.validator.validate_curl_credential_hygiene(
            "curl -H 'X-Api-Key: $INFERENCE_API_KEY' https://ai.example.com"
        )
        self.assertTrue(errors)

    def test_protected_header_file_passes_credential_hygiene(self) -> None:
        errors = self.validator.validate_curl_credential_hygiene(
            "curl --header @control-plane.headers https://gateway.example.com"
        )
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
