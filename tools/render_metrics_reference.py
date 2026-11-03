#!/usr/bin/env python3
"""Render or check the public release-scope metric catalog."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ACTIVATION = {
    "E": "eager scalar",
    "V": "lazy vector children",
    "P": "pre-created children",
    "C": "custom collector; collector-defined samples",
    "H": "eager TTFB histogram",
    "Q": "quota-lazy collector",
    "DP": "datapath-gated scalar",
    "T": "TTFT-window-lazy",
    "S": "startup-created child",
}

STATUS = {
    "verified-runtime": "writer plus recorded runtime evidence in the upstream manifest",
    "verified-static": "writer verified by static or unit evidence; no runtime claim",
    "conditional-with-proven-writer": "writer exists but the family appears only when its feature path is active",
    "writer-mapped": "writer source is mapped; runtime emission was not verified",
    "definition-only": "registered without a separate writer, for example a gauge computed when Prometheus scrapes it; no runtime claim",
}


def escape_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(contract: dict[str, Any]) -> str:
    source = contract["source"]
    release = contract["release_snapshot"]
    manifest = contract["metric_manifest"]
    families = sorted(
        (
            family for family in manifest["families"]
            if family.get("release_scope") == "release"
        ),
        key=lambda family: family["name"],
    )
    statuses = Counter(family["implementation_status"] for family in families)
    lines = [
        "# Metrics reference",
        "",
        "This catalog is generated from the Gateway metric manifest and contains only",
        "families marked `release`. It proves the name, type, label schema, activation",
        "class, mapped writer, and upstream evidence classification at the frozen source",
        "revision. It does **not** prove that every family is present in a particular",
        "deployment: feature activation, traffic, build tags, hardware, and runtime",
        "configuration still determine whether a series is emitted.",
        "",
        f"- Gateway source commit: `{source['commit']}`",
        f"- Selected Gateway eBPF submodule commit: `{source['ebpf_submodule_commit']}`",
        f"- Comparison release: `{source['release_tag']}` at `{source['release_commit']}`",
        f"- Comparison release eBPF submodule commit: `{release['ebpf_submodule_commit']}`",
        "- Release manifest availability: "
        + ("present" if release["metric_manifest_available"] else "**absent**"),
        f"- Manifest path: `{manifest['source_path']}`",
        f"- Manifest SHA-256: `{manifest['sha256']}`",
        f"- Embedded manifest source revision: `{manifest['provenance'].get('source_revision', 'unknown')}`",
        f"- Embedded manifest generation time: `{manifest['provenance'].get('generated_at', 'unknown')}`",
        f"- Manifest schema version: `{manifest['schema_version']}`",
        f"- Release-scope families: **{len(families)}**",
        "- Raw writer paths and evidence prose are intentionally not copied into this public catalog.",
        "",
        "The table below is therefore a selected-source catalog, not a claim",
        f"that `{source['release_tag']}` ships every listed family. The comparison",
        "release does not contain the generated metric manifest used by this page.",
        "Release packaging and runtime emission require separate qualification.",
        "",
        "## How to read evidence",
        "",
        "| Status | Meaning |",
        "| --- | --- |",
    ]
    for key, meaning in STATUS.items():
        lines.append(f"| `{key}` ({statuses.get(key, 0)}) | {meaning} |")
    lines.extend(
        [
            "",
            "A writer or registration point is source evidence, not deployment evidence.",
            "`verified-runtime` records upstream runtime evidence for that family, but this",
            "documentation build does not rerun Linux, GPU, HA, or release tests.",
            "The [verification status](verification-status.md) page keeps those evidence",
            "lanes separate.",
            "",
            "## Activation codes",
            "",
            "Combined codes such as `DP+V` require both conditions.",
            "",
            "| Code | Activation condition |",
            "| --- | --- |",
        ]
    )
    for code, meaning in ACTIVATION.items():
        lines.append(f"| `{code}` | {meaning} |")
    lines.extend(
        [
            "",
            "## Release-scope families",
            "",
            "| Family | Type | Labels | Activation | Runtime scope | Evidence status |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for family in families:
        labels = ", ".join(f"`{label}`" for label in family.get("labels", [])) or "none"
        lines.append(
            "| `{name}` | `{type}` | {labels} | `{activation}` | `{runtime}` | `{status}` |".format(
                name=escape_cell(family["name"]),
                type=escape_cell(family["type"]),
                labels=labels,
                activation=escape_cell(family.get("activation", "")),
                runtime=escape_cell(family.get("runtime_scope", "")),
                status=escape_cell(family.get("implementation_status", "")),
            )
        )
    lines.extend(
        [
            "",
            "## Label enums used by examples",
            "",
            "The example validator rejects unknown metric names and selector labels. For",
            "the closed values below it also rejects exact (`=` or `!=`) selectors that",
            "use values outside the frozen source contract.",
            "",
            "| Family | Label | Allowed values |",
            "| --- | --- | --- |",
        ]
    )
    for family, labels in sorted(manifest.get("label_enums", {}).items()):
        for label, values in sorted(labels.items()):
            lines.append(
                f"| `{family}` | `{label}` | "
                + ", ".join(f"`{escape_cell(value or '(empty)')}`" for value in values)
                + " |"
            )
    combinations = manifest.get("label_combinations", {})
    if combinations:
        label_source = manifest["label_source"]
        lines.extend([
            "", "## Source-declared label combinations", "",
            f"Request outcomes, causes, P/D phases and fallback reasons are extracted from `{label_source['source_path']}`",
            f"at the Gateway commit above (source SHA-256: `{label_source['sha256']}`).",
            "The validator also rejects selectors that match none of these combinations.",
            "Other enums above are reviewed documentation constants. Empty cause is written as `(empty)`.",
            "", "| Family | Labels | Allowed combinations |", "| --- | --- | --- |",
        ])
        for family, rule in sorted(combinations.items()):
            values = "; ".join(" / ".join(f"`{escape_cell(value or '(empty)')}`" for value in row) for row in rule["values"])
            labels = " / ".join(f"`{value}`" for value in rule["labels"])
            lines.append(f"| `{family}` | {labels} | {values} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("tests/contracts/docs_examples/gateway-api.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("docs/reference/metrics.md")
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    expected = render(json.loads(args.contract.read_text()))
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(expected)
        return 0
    if not args.output.exists() or args.output.read_text() != expected:
        print(
            f"{args.output} is stale; run {Path(__file__).name} --write",
            file=sys.stderr,
        )
        return 1
    print(f"{args.output}: up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
