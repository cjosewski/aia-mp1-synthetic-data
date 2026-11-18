# P1-03 course submission — Home DIY Repair

The course submission starts with a fresh baseline in five repair categories.
The generator writes original answers at runtime from the category and an
original topic cue. The benchmark provides only category counts. The two
published splits together contain 1,000 records in each category at revision
`074f64327b4d19fd83052f614ca9d25f89cfe6ee`.
[Published benchmark](https://huggingface.co/datasets/dipenbhuva/home-diy-repair-qa/tree/074f64327b4d19fd83052f614ca9d25f89cfe6ee)

## Review the baseline on Windows

On the project workstation, double-click `Review-DIY-Baseline.cmd` in the
handoff folder. It opens the human labeling CLI and saves each completed item.
Start at step 3 below. Steps 1–2 open the same review manually.

1. Open Windows Terminal or PowerShell. Enter `wsl -d Ubuntu`.
2. Paste this block in Ubuntu. It opens the saved blind review on this workstation.

   ```bash
   cd /mnt/d/_Repos/_AIA/aia-mp1-synthetic-data
   export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
   source tools/environment.sh
   export AIA_MP1_DOMAIN=home-diy
   export DIY_ROOT=../artifacts/evidence/P1-03/home-diy
   uv run --locked python -m aia_mp1 label --artifact-root "$DIY_ROOT" --assessment-id diy-baseline-review-001 --reviewer "Chad Josewski" --review-stage blind
   ```

3. Read the homeowner's question and all seven fields for each selected item.
   Evaluate the **written advice**. You do not need to perform the repairs.
   Enter 1 or 0 for each dimension using the anchors displayed by the CLI.
   For D3, check every tool against the household availability and under-$50
   rule. For D4, check whether the homeowner can do the job and whether the
   answer calls a professional when needed. Record the concrete reason for a
   failure in the notes.
4. Finish 20 items, four per category. Relaunch the same command to resume.
   Verify the saved count with the following command.

   ```bash
   uv run --locked python -m aia_mp1 label-status --artifact-root "$DIY_ROOT" --assessment-id diy-baseline-review-001
   ```

5. Tell Codex when the 20 reviews are complete and whether you completed them
   before seeing any judge ratings. That declaration accompanies the frozen
   human reference.

## Reproduce baseline collection

The operator uses the same WSL environment and a private local model endpoint.
`config/diy/baseline.json` identifies the generator, its checksum, alias,
temperature (0.6), prompt, port and evidence root. Configure the endpoint
credential through the environment variable named in that file. For a fresh
collection, verify the checksum of the Mac model against `model_sha256` in the
config. On the Mac start the generator on an available dedicated port with:

```bash
/opt/homebrew/bin/llama-server --model "$HOME/Models/MP1/Qwen3-30B-A3B-Q4_K_M.gguf" \
  --alias mp1-diy-qwen30b --host 127.0.0.1 --port 8086 --ctx-size 8192 \
  --parallel 1 --reasoning off
```

From WSL, use an authenticated SSH session to the Mac with local forwarding
`-L 127.0.0.1:18086:127.0.0.1:8086`. In the collection terminal verify
`curl -fsS http://127.0.0.1:18086/v1/models` reports `mp1-diy-qwen30b`.
The loopback server shown above accepts a placeholder SDK token. Set
`export MP1_DIY_LOCAL_TOKEN=local-session-placeholder` for that invocation.
Use a new collection ID for each independent run.

```bash
uv run --locked python -m aia_mp1 source-check --pack config/diy/topics.json
uv run --locked python -m aia_mp1 collect --config config/diy/baseline.json --collection-id diy-baseline-002
uv run --locked python -m aia_mp1 cohort --artifact-root "$DIY_ROOT" --collection-id diy-baseline-002 --cohort-id diy-baseline-002
uv run --locked python -m aia_mp1 assessment --artifact-root "$DIY_ROOT" --cohort-id diy-baseline-002 --assessment-id diy-baseline-review-002
```

Collection retains ten items per category after schema validation, six cheap
dimension checks and deduplication. Read the generation ledger for initial
schema validity, the batch gate reports for dropped checks, and the cohort
summary for retained counts. The human and judge use the same original
[rubric](../config/diy/rubric.json).

## Acceptance after the review

Use an independent judge through Instructor and Pydantic at a temperature
below 0.6. Score all 50 retained items and compare each dimension against the
20 frozen reviews. Revise the judge prompt on the same items until all six
dimensions reach at least 16/20. Record each iteration.

Only then select a generator correction from the worst measured category and
dimension. Generate another balanced cohort of at least 50, review at least
20, and use the calibrated judge on the complete cohort. Compare dimension
rates, the all-six pass rate and relative failure reduction. Record both the
numeric ≥80% reduction verdict and the stricter >80% wording in the brief.
Use the [analysis runbook](ANALYSIS-RUNBOOK.md) with the DIY domain and evidence
root for metrics, charts and traces.
