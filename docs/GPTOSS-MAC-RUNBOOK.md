# Mac runbook — GPT-OSS-20B candidate screening

Prepared November 13, 2026 for Chad Josewski. Follow the numbered steps in order.
Use the same Apple Silicon Mac that returned the last evaluation. All commands
below belong in **macOS Terminal**. Leave the Linux machine available for Herd work.

## 1. Understand this test

You are testing whether **GPT-OSS-20B MXFP4** can judge the ten saved engineering
responses more reliably than the previous candidates. The program asks it for
six rubric decisions and explanations, then compares them with your frozen
reviews. You do not need to enter or revise any reviews.

Only GPT-OSS makes new completion requests. The package includes the already
audited Mac Llama and Qwen judgments for comparison. The questions, answers,
reference context, rubric and judge-v2 instructions are unchanged. Human labels
are used for local scoring only and are not sent in model requests.

This candidate is a different model family available on your NAS. OpenAI documents
its reasoning and structured-output capabilities; those are a reason to test it,
not evidence that it is a stronger engineering judge. See the
[model announcement](https://openai.com/index/introducing-gpt-oss/) and
[pinned GGUF](https://huggingface.co/ggml-org/gpt-oss-20b-GGUF/blob/b97cbb20d1995efd41dce8c4dd1ddf86e8db375b/gpt-oss-20b-MXFP4.gguf).
Weights are Apache-2.0; the upstream gpt-oss usage policy also applies.

**Budget:** ten cases, at most two attempts each, at most **20 new completion
requests**. There are already 43 starts across the earlier qualification and
development runs; the cumulative maximum is now 63. This is a separate allocation.
The run command explicitly activates it. Each request has a 300-second timeout,
a 4,096-token cap and temperature 0.1. There are no hidden client retries or
extra completion probes. Health, identity and hash checks do not ask for judgments.

**Finish condition:** return the exported ZIP after ten resolved cases, or return
the preserved evidence if the run stops. Two consecutive unsuccessful responses
(including invalid JSON and timeouts) stop the run. Failure is useful evidence;
do not adjust settings or start a fresh folder to make the result pass.

These are known development cases. A promising result still needs fresh blind
confirmation before judge qualification and assessed calibration. The model's
template/reasoning differs from the other models, and the comparison is historical,
not a randomized or repeated-seed benchmark.

## 2. Copy and unpack the new package

1. In Finder press **Command-K**.
2. Connect to `smb://192.168.0.55/AIA` and sign in with your existing NAS account.
3. Open `MP1-handoff` and copy **MP1-GPTOSS-MAC.zip** to your Mac's home folder
   (Finder **Go → Home**).
4. Double-click it. The resulting folder must be `~/MP1-GPTOSS-MAC`.
5. Open its `HANDOFF.md` and continue here. Keep the previous Mac package intact.

If this folder already contains a `results` directory from an attempted GPT-OSS
run, preserve it and use the pause/error rules in Step 8. Do not overwrite it.

## 3. Reuse the installed tools and copy the model

In Terminal:

```sh
uname -m
uv --version
llama-server --version
```

Expected architecture: `arm64`. Reuse **llama.cpp b12110-cd959bae9**, the build
recorded in the previous Mac results (version output may show build and commit
separately). Do not upgrade/reinstall it for this comparison. If a command is
missing or the build changed, stop and send the output; the preflight also checks
the actual running server build and Mac hostname.

Create the local model folder:

```sh
mkdir -p "$HOME/Models/MP1"
```

In the mounted AIA share, open:

```text
LLM_models/ggml-org__gpt-oss-20b-GGUF/
```

Copy **gpt-oss-20b-MXFP4.gguf** into your home folder's **Models/MP1** folder.
It is 12,109,566,624 bytes (about 12.1 GB). Wait for copying to finish. You do not
need a new download or the EAGLE draft model. If the exact file is already in
that local folder, retain it; preflight verifies the actual served file's hash:

```text
27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901
```

## 4. Prepare and verify the evaluation files

In Terminal:

```sh
cd "$HOME/MP1-GPTOSS-MAC/project"
uv sync --locked
uv run --locked python ../evaluate.py verify
```

Expected: **PASS** confirming the frozen files and input identities. Dependency
setup may access the internet; all model inference stays local. Do not source
the Windows/WSL environment script on the Mac. Stop if verification fails.

## 5. Start the model in Terminal window A

Plug the Mac into power and keep it awake. This is a substantial local workload;
avoid competing model jobs. If your previous evaluation server is still running,
first confirm that its client finished, then press **Control-C in that server's
Terminal window**. If port 8081 is occupied by an unidentified service, stop and
report that instead of killing a process.

Create the startup-log folder:

```sh
mkdir -p "$HOME/MP1-GPTOSS-MAC/results"
```

Start the server:

```sh
llama-server \
  --model "$HOME/Models/MP1/gpt-oss-20b-MXFP4.gguf" \
  --host 127.0.0.1 --port 8081 \
  --ctx-size 16384 --parallel 1 \
  2>&1 | tee "$HOME/MP1-GPTOSS-MAC/results/server-gptoss-$(date -u +%Y%m%dT%H%M%SZ).log"
```

Leave this window open. Wait for the server's listening/ready message. This uses
the model's embedded chat template and the engine's default reasoning settings.
Do not add a different template, reasoning-effort flag, draft model or sampling
override. The existing engine enables its Jinja template handling by default;
the [server reference](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
documents these controls and JSON response support. Actual compatibility with
this model and the frozen client remains part of this test.

If loading fails, preserve the log and go to Step 8. The server listens only on
this Mac. No Herd configuration, Linux service, API key or LAN endpoint change
is needed.

## 6. Verify the running model in Terminal window B

Open another Terminal window and run:

```sh
cd "$HOME/MP1-GPTOSS-MAC/project"
uv run --locked python ../evaluate.py preflight gptoss
```

Expected: **PASS** after checking the served GGUF checksum, same Mac/server
build, one slot, context 16,384 and loopback endpoint. Hashing the 12.1 GB file
can take a few minutes. No judgment request has been made yet.

If preflight stops, keep its message and return the startup log. Do not bypass
the model, platform or build checks.

## 7. Run the ten cases

In Terminal window B:

```sh
uv run --locked python ../evaluate.py run gptoss --authorize-new-budget
```

The flag records your activation of the separate maximum-20-request allocation.
The runner repeats the read-only preflight before starting. Expect lines such as
`gptoss: example 1/10, attempt 1/2`, followed by a valid judgment or failed attempt.
Do not run Llama or Qwen again. No browser interaction or manual scoring is needed.

Wait for `gptoss phase finished: 10/10 resolved`, or a **STOP** message. A request
may take up to five minutes; the generous full-budget ceiling is 100 minutes of
request time, although the stop rule often ends an unsuccessful run much sooner.
Keep both Terminal windows open while requests are active.

## 8. Finish, or preserve a stopped run

After the run finishes normally, use Terminal B:

```sh
uv run --locked python ../evaluate.py report
uv run --locked python ../evaluate.py export
```

The report shows GPT-OSS alongside **archived Mac v2** Llama/Qwen results. All
agreement denominators remain ten, with unresolved cases never counted as passes.
The export prints the full path of a new `MP1-results-<timestamp>.zip` in the
`MP1-GPTOSS-MAC` folder. Copy that ZIP to the NAS **AIA/MP1-handoff** folder and
send its filename. You may then stop this server with Control-C in Terminal A.

If the run stops after two unsuccessful attempts, do not rerun it. Run `report`
and `export` above and return the evidence, even if no cases resolved. If loading
or preflight failed, `export` can still package the saved startup log.

If interrupted, do not delete attempt records or start a new copy. An existing
start without a result is an **unknown outcome** and consumes its attempt.
`report` will refuse that incomplete ledger; `export` can preserve it once no
process is active and there is no lock. If `.running.lock` remains, do not delete
it: confirm the client is no longer running, compress the entire results folder
with Finder, and return it with the STOP message for inspection.

A clean pause between completed requests can be resumed with the same `run`
command, folder, server and settings. Previously completed cases are skipped.
A two-failure stop or unknown outcome cannot be resumed automatically. No
timeouts, token limits, prompts or labels should be changed within this experiment.

The returned ZIP contains model traces and local file paths. Keep it on the
private share; raw evidence does not belong in GitHub.
