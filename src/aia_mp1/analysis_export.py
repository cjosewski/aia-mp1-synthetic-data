"""Local evidence bundles and five auditable, non-paired cohort figures."""

import csv
import importlib.metadata
import shutil
from pathlib import Path

from .analysis import file_hash, load_analysis, output_directory
from .assessment import save_new
from .evaluation_schemas import DIMENSIONS
from .schemas import CATEGORIES
from .tracing import now

PHASES = ("baseline", "corrected")


def chart_tables(report: dict) -> dict:
    """Explicit missing cells are exported as blanks in CSV, never numerical zero."""
    tables = {name: [] for name in ("dimensions", "segments", "agreement", "categories", "overall")}
    rubric = report["baseline"]["rubric"]
    thresholds = {d["id"]: d["pass_rate_minimum"] for d in rubric["dimensions"]}
    for phase in PHASES:
        snapshot = report[phase]
        for dimension in DIMENSIONS:
            row = snapshot["judge_quality"]["dimensions"][dimension] if snapshot else {}
            tables["dimensions"].append(
                {
                    "cohort": phase,
                    "dimension": dimension,
                    "pass_rate": row.get("pass_rate"),
                    "pass": row.get("pass"),
                    "observed": row.get("observed"),
                    "population": row.get("population"),
                    "missing": row.get("missing"),
                    "corrected_threshold": thresholds[dimension],
                }
            )
            cal = snapshot["calibration"] if snapshot else None
            agreement = cal["summary"]["dimensions"][dimension] if cal else {}
            tables["agreement"].append(
                {
                    "cohort": phase,
                    "dimension": dimension,
                    "agreement": agreement.get("agreement"),
                    "matching": agreement.get("matching"),
                    "compared": agreement.get("compared"),
                    "missing": agreement.get("missing"),
                    "threshold": 0.8,
                }
            )
            for category in CATEGORIES:
                row = (
                    snapshot["judge_segments"][category]["dimensions"][dimension]
                    if snapshot
                    else {}
                )
                tables["segments"].append(
                    {
                        "cohort": phase,
                        "category": category,
                        "dimension": dimension,
                        "pass_rate": row.get("pass_rate"),
                        "pass": row.get("pass"),
                        "observed": row.get("observed"),
                        "population": row.get("population"),
                    }
                )
        for category in CATEGORIES:
            row = snapshot["category_distribution"][category] if snapshot else {}
            tables["categories"].append(
                {
                    "cohort": phase,
                    "category": category,
                    "schema_valid_candidates": row.get("schema_valid_candidates"),
                    "after_deduplication": row.get("after_deduplication"),
                    "retained": row.get("retained"),
                    "target": 10,
                }
            )
        row = snapshot["judge_quality"]["overall"] if snapshot else {}
        tables["overall"].append(
            {
                "cohort": phase,
                **{
                    k: row.get(k)
                    for k in ("pass", "fail", "observed", "population", "missing", "pass_rate")
                },
            }
        )
    return tables


def render_charts(report: dict, target: Path) -> dict:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import seaborn as sns

    target.mkdir(parents=True, exist_ok=False)
    tables = chart_tables(report)
    for name, rows in tables.items():
        with (target / f"{name}.csv").open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    sns.set_theme(style="whitegrid", context="notebook")
    colors = ("#315b83", "#c05b21")
    captions = {}
    status = (
        "MEASURED CRITERIA READY" if report["status"] == "ready" else "PRELIMINARY — INCOMPLETE"
    )

    def save(fig, name, caption):
        fig.suptitle(f"{caption}\n{status}", fontsize=13)
        fig.tight_layout(rect=(0, 0.04, 1, 0.92))
        fig.text(
            0.02,
            0.01,
            "NA = unmeasured. Rates use observed N; see CSV for missing counts.",
            fontsize=9,
        )
        fig.savefig(target / f"{name}.png", dpi=170)
        fig.savefig(target / f"{name}.svg")
        plt.close(fig)
        captions[name] = caption

    def rate_bars(ax, table, field, threshold=None):
        for pi, phase in enumerate(PHASES):
            rows = [r for r in tables[table] if r["cohort"] == phase]
            xs = np.arange(6) + (pi - 0.5) * 0.35
            values = [r[field] * 100 if r[field] is not None else np.nan for r in rows]
            ax.bar(xs, values, width=0.35, color=colors[pi], label=phase.title())
            for x, row, value in zip(xs, rows, values, strict=True):
                n = row.get("observed", row.get("compared"))
                ax.text(
                    x,
                    min(value + 2, 104) if row[field] is not None else 3,
                    f"N={n}" if row[field] is not None else "NA",
                    ha="center",
                    fontsize=8,
                )
        if threshold:
            ax.plot(np.arange(6), threshold, "k_", markersize=25, label="Required threshold")
        ax.set(xticks=np.arange(6), xticklabels=DIMENSIONS, ylim=(0, 112), ylabel="Percent")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)

    fig, ax = plt.subplots(figsize=(10, 5))
    rate_bars(
        ax,
        "dimensions",
        "pass_rate",
        [r["corrected_threshold"] * 100 for r in tables["dimensions"][:6]],
    )
    save(
        fig,
        "01-dimension-pass-rates",
        "Judge pass rates by dimension; thresholds apply to corrected cohort",
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, phase in zip(axes, PHASES, strict=True):
        rows = {
            (r["category"], r["dimension"]): r for r in tables["segments"] if r["cohort"] == phase
        }
        values = np.array(
            [
                [
                    rows[c, d]["pass_rate"] if rows[c, d]["pass_rate"] is not None else np.nan
                    for d in DIMENSIONS
                ]
                for c in CATEGORIES
            ]
        )
        sns.heatmap(
            values,
            mask=np.isnan(values),
            vmin=0,
            vmax=1,
            cmap="YlGnBu",
            ax=ax,
            xticklabels=DIMENSIONS,
            yticklabels=CATEGORIES,
            cbar=phase == "corrected",
        )
        for ci, c in enumerate(CATEGORIES):
            for di, d in enumerate(DIMENSIONS):
                r = rows[c, d]
                label = (
                    f"{r['pass_rate']:.0%}\nN={r['observed']}"
                    if r["pass_rate"] is not None
                    else "NA"
                )
                ax.text(
                    di + 0.5,
                    ci + 0.5,
                    label,
                    ha="center",
                    va="center",
                    color="white"
                    if r["pass_rate"] is not None and r["pass_rate"] > 0.65
                    else "black",
                    fontsize=9,
                )
        ax.set(title=phase.title(), ylabel="")
        ax.tick_params(axis="y", rotation=0)
    save(
        fig,
        "02-segment-heatmaps",
        "Category × dimension judge pass rates; each cell reports its observed N",
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    rate_bars(ax, "agreement", "agreement", [80] * 6)
    save(fig, "03-human-judge-agreement", "Agreement against frozen blind human references")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, phase in zip(axes, PHASES, strict=True):
        rows = [r for r in tables["categories"] if r["cohort"] == phase]
        for index, (field, label) in enumerate(
            (("schema_valid_candidates", "Before gate/quota"), ("retained", "Retained"))
        ):
            values = [r[field] if r[field] is not None else np.nan for r in rows]
            ax.bar(
                np.arange(5) + (index - 0.5) * 0.35,
                values,
                width=0.35,
                label=label,
                color=colors[index],
            )
        ax.axhline(10, color="black", linestyle="--", label="Target retained = 10")
        ax.set(
            xticks=np.arange(5),
            xticklabels=[c.replace("_", "\n") for c in CATEGORIES],
            title=phase.title(),
            ylabel="Item count",
        )
        if not report[phase]:
            ax.text(0.5, 0.5, "NA — no corrected cohort", transform=ax.transAxes, ha="center")
        ax.legend(fontsize=8)
    save(
        fig,
        "04-category-distribution",
        "Schema-valid candidates before gate/quota and retained cohort counts",
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    for index, field in enumerate(("pass", "fail")):
        values = [
            r[field] / r["observed"] * 100 if r["observed"] else np.nan for r in tables["overall"]
        ]
        ax.bar(
            np.arange(2) + (index - 0.5) * 0.35,
            values,
            width=0.35,
            label=field.title(),
            color=colors[index],
        )
    for i, row in enumerate(tables["overall"]):
        ax.text(
            i,
            103 if row["observed"] else 5,
            f"N={row['observed']}" if row["observed"] else "NA",
            ha="center",
        )
    ax.set(
        xticks=[0, 1],
        xticklabels=[p.title() for p in PHASES],
        ylim=(0, 112),
        ylabel="Percent of observed items",
    )
    ax.legend()
    comparison = report["comparison"]
    reduction = comparison["relative_failure_reduction"] if comparison else None
    ax.set_xlabel(
        f"Relative failure reduction: {reduction:.1%}"
        if reduction is not None
        else "Relative failure reduction: undefined / unmeasured"
    )
    save(
        fig,
        "05-overall-pass-fail",
        "Overall all-six pass/fail: independent cohort aggregates, not paired items",
    )
    receipt = {
        "report_sha256": report["sha256"],
        "created_at": now(),
        "captions": captions,
        "versions": {p: importlib.metadata.version(p) for p in ("matplotlib", "seaborn", "numpy")},
        "files": {p.name: file_hash(p) for p in sorted(target.iterdir())},
    }
    save_new(target / "charts.json", receipt)
    return receipt


def export_local(root: Path, report_id: str, export_id: str, *, charts: bool = True) -> dict:
    """Copy verified sources, all generation attempts and report. Never publish a bundle."""
    report = load_analysis(root, report_id)
    target = output_directory(root, export_id)
    target.mkdir(parents=True, exist_ok=False)
    source_root = root.resolve()
    hashes = {}
    for phase in PHASES:
        snapshot = report[phase]
        if not snapshot:
            continue
        for relative, expected in snapshot["input_hashes"].items():
            source = source_root / relative
            if not source.resolve().is_relative_to(source_root) or file_hash(source) != expected:
                raise ValueError("export source changed or escaped artifact root")
            destination = target / "evidence" / relative
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            if file_hash(destination) != expected:
                raise ValueError("export copy differs")
        assessment = source_root / "assessments" / snapshot["assessment_id"]
        shutil.copyfile(assessment / "data.jsonl", target / f"{phase}.jsonl")
    save_new(target / "report.json", report)
    if charts:
        render_charts(report, target / "charts")
    # Verify the snapshot once more before sealing the package.
    if load_analysis(root, report_id) != report:
        raise ValueError("analysis changed during export")
    for path in sorted(target.rglob("*")):
        if path.is_file():
            hashes[path.relative_to(target).as_posix()] = file_hash(path)
    receipt = {
        "schema_version": "1",
        "created_at": now(),
        "report_sha256": report["sha256"],
        "distribution": "local_only; review source permissions before any external sharing",
        "completion": report["status"],
        "files": hashes,
    }
    save_new(target / "export-manifest.json", receipt)
    return receipt
