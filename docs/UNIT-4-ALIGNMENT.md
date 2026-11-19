# Unit 4 exercises and AEC judge calibration

The supplied Unit 4 folder contains seven notebook files. The task and answer copies share exercise instructions. There are 30 distinct exercises in four notebooks, including the optional optimizer. The supplied sequence goes from Notebook 3 to Notebook 5.

## Notebook 1 · Build and measure a prompt in layers

| Exercise | What the exercise measures | How it applies to AEC |
| --- | --- | --- |
| 1. Plain baseline | Score a minimal prompt and inspect five mistakes. Track accuracy, malformed outputs and cost separately. | Preserve the candidate, rubric, settings, raw judgments and human reference for each comparison. The existing v3 judge already contains detailed instructions. |
| 2. Repeatability | Repeat identical calls and record the range of scores and which cases flip. | Measure variation on development data under separately identified runs. The course's four-point spread on bank routing cannot be used as an AEC estimate. |
| 3. Role and context | Compare a short role and label definitions with the plain prompt. Isolate the effect of role wording. | Define what each rubric dimension measures and which candidate fields supply the evidence. |
| 4. Worked examples | Compare narrow and broad example coverage, then add the chosen set to the accumulated prompt. Keep evaluation messages out of the examples. | Test reviewed AEC examples on other categories. Report this as a cross-category development comparison. A fully disjoint example bank gives a stronger held-out test. |
| 5. Mark input boundaries | Measure the effect of delimiters on classification and test input escaping and output parsing separately. | Make the task, source, candidate and reviewed examples distinguishable. Keep candidate text in a data role. |
| 6. Structured output | Compare instructions in prose with a schema-enforced answer. Measure rejected answers and classification accuracy. | Check the six binary decisions and justifications, then score semantic correctness independently of parsing. |
| 7. Long references | Compare document-first with question-first layout. Check quoted passages verbatim and confirm they belong to the right section. Measure cache use separately. | Ground API claims in the matching product and version. A quotation about a similar class or call cannot establish the candidate's claim. |
| 8. Target a confused pair | Test three wordings of one rule on the confused pair and on the general workload. Count regressions in both directions. | Test a rule distinguishing a named hazard from an actionable precaution. Inspect false approvals and false rejections in every dimension. |
| 9. Held-out scoreboard | Run every saved version on untouched messages. Compare each technique alone and its incremental effect when added to prior layers. Compare models on matched prompts. | Keep a plain row, a plain-plus-layer row and a cumulative row on identical cases. Select the method on development evidence before the assessed run. |

## Notebook 2 · Improve the instruction and the decision rule

| Exercise | What the exercise measures | How it applies to AEC |
| --- | --- | --- |
| 1. Answering and acting | Establish separate baselines for routing accuracy and correct tool behavior. Inspect actual actions and arguments. | An answer can describe an appropriate workflow while prescribing an invalid API or MCP operation. Score the dimensions independently. |
| 2. Steps and outcome | Compare a prescribed sequence with a stated outcome and a criterion for completion. | Identify what result the brief requires and the candidate action that produces or verifies it. |
| 3. Reasoning effort | Compare low, medium and high effort with a verbal instruction on the same calculations. Record correct answers, token usage and cost. | Treat effort as a separate experimental setting when supported. Keep the course temperature requirement and report truncation. |
| 4. Ask or act | Vary one decision rule and count both premature action and unnecessary clarification. | A stricter judge can fix false passes and introduce false failures. Count both. |
| 5. Operational rules | Compare behavior before and after rules for reversibility, investigation, minimal scope and preserving genuine checks. Test ordinary tasks again. | Where an answer claims an action, inspect its prerequisites, scope and side effects. The same test applies to direct API calls and MCP tools. |
| 6. Contradiction audit | Find conflicting instructions, give the applicable rule precedence and remeasure behavior. | Compare the frozen rubric with the judge prompt. For example, D2 names the safety field, while broader wording can invite credit for a precaution that appears only in the steps. |
| 7. Small edits from failures | Give the model development mistakes, inspect its proposed edits, remove case-specific patches, then compare old and new prompts on unseen cases. | Use disagreements to identify a general rule. Keep assessed reviews and case-specific corrections out of the prompt. |
| 8. Model transfer | Compare two models first at their defaults and then at matched explicit settings. | Pin the served weights and record supported parameters. Attribute a prompt gain only within a matched model comparison. |
| 9. Optional optimization | Use separate training and selection data, a fixed scoring budget and a held-out check for the optimized prompt. | Any optimizer needs an adequate labeled working set and a per-dimension objective. Optimizer training scores cannot establish assessed calibration. |

## Notebook 3 · Compare several calls with one

| Exercise | What the exercise measures | How it applies to AEC |
| --- | --- | --- |
| 1. One-call baseline | Measure accuracy, billed cost and response time on the same job. | Record valid returns, six agreement counts, token usage and elapsed time for the local judge. |
| 2. Voting | Compare five sampled answers and their vote with a single answer. Report disagreement and sequential versus parallel time. | Repeated, correlated technical mistakes can survive a vote. Measure the contribution of aggregation separately from sampling. |
| 3. Chaining | Extract issues, retrieve the relevant policy for each, then answer. Check the intermediate evidence and what survives into the final output. | Separate task obligations, version-specific evidence and judgment. Record the stage at which a supported fact goes missing. |
| 4. Grounded review | Give the same original outputs to a bare reviewer and to one instructed to recheck against specific source rows. Count wrong-to-right and right-to-wrong changes. | A second call can check the candidate field, receiver, signature or state against explicit evidence. Reuse the first judgment and compare both correction directions. |
| 5. Planning | Compare a whole-job call with a bounded plan, independent groups and a final combination. Check complete coverage and false alarms. Repeat on a simple job. | Enforce coverage of all six dimensions if work is split. Only add calls when the accuracy or timing supports them. |
| 6. Choose by workload | Compare accuracy, calls, cost and latency within each task. Make separate choices for interactive and overnight work. | Judge calibration runs offline. Preserve the time and compute cost of each candidate method alongside its agreement. |

## Notebook 5 · Measure what safeguards preserve

| Exercise | What the exercise measures | How it applies to AEC |
| --- | --- | --- |
| 1. Two baselines | Score undesired behavior and successful ordinary service under the same configuration. Inspect the tool log. | Track false approvals and false rejections beside schema validity. |
| 2. Conversation coverage | Expand the evaluation set to cover direct, role-based and multi-turn pressure, then recompute the baseline. | If the stress-test population grows, version the set and compare methods on matching denominators. |
| 3. Document boundary | Check whether uploaded data influenced an action, using the observed tool result. | Treat source excerpts and generated answers as data. A statement inside either cannot authorize an operation. |
| 4. Prompt safeguards | Add explicit role boundaries and document fencing. Recheck ordinary cases for regressions. | Keep evidence and instructions distinct and check whether added boundaries discard useful evidence. |
| 5. Code safeguards | Test input, output and tool-side checks independently, then add them to the prompt safeguards. Measure normal cases that are blocked. | Validate schema, model identity, evidence binding and tool arguments in code wherever these are observable. |
| 6. Final scorecard | Reuse stored results to compare three cumulative levels by failure family and ordinary performance. | Rebuild per-dimension counts from original raw returns. Show denominators and retain regressions alongside improvements. |

## Reading the AEC experiment

The first Devstral comparison holds the model, temperature, ten targets and rubric fixed and adds two reviewed examples to v3. Each target's category is excluded when selecting demonstrations. That measures the incremental effect of examples on v3. The plain-prompt comparison, run-to-run spread and a fully independent confirmation set are separate measurements. The bank exercises' scores do not supply any of them.

For every new layer, retain the plain prompt, the plain prompt with that layer alone, the previous combined prompt and the new combined prompt. Compare the same case IDs, the count of decisions corrected and broken, and latency. Keep the composed prompt only when the new evidence warrants it. The project advances a judge after ten valid development returns, at least eight matches per dimension and an explanation audit. Assessed calibration requires all 50 judgments and at least 16 matches on each of the six dimensions across the 20 frozen human reviews.
