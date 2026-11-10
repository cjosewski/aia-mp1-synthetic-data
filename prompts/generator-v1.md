Generate one original engineering-code question and answer for category {category}.

This is a standalone synthetic task for a local smoke test. No external reference corpus is supplied. Do not claim that the answer has been independently verified, benchmarked, approved or executed. Use only APIs and libraries you can name accurately, identify the relevant version or installation assumptions, and avoid uncertain API calls rather than inventing them.

Choose a small, specific task within the category. The five possible categories concern GIS scripting, AEC automation, structural-analysis code, CAD APIs and nonmedical simulation. Use synthetic or personal examples only. Exclude employer/client material, proprietary physiology and medical simulation. Do not include credentials, personal records or private project details.

Return only the structured payload requested by the response schema, with exactly these seven fields:

- question: a specific, contextualized engineering-code question.
- answer: coherent guidance that addresses the question and ties together the needed tools, concrete actions, relevant hazards and useful advice. Do not merely concatenate the other fields.
- equipment_problem: the precise task or failure being addressed. Keep this canonical field name even though the task concerns software.
- tools_required: a list with at least one real tool, library or API; state version or installation requirements where relevant.
- steps: a list of at least three concrete, ordered actions. Include relevant units, coordinate systems, tolerances, backup actions or observable checks instead of vague instructions.
- safety_info: a task-specific correctness or data-loss hazard and a concrete precaution. Identify any result that requires licensed-engineer review or sign-off. Generic phrases such as "be careful" or "use caution" are insufficient.
- tips: a list with at least one nonobvious, task-specific insight that is not a repeated step or generic encouragement.

Every string and list entry must be nonblank. Keep the answer internally consistent with equipment_problem, the declared tools and the listed steps. Where code cannot establish physical validity or professional approval, say so explicitly. Do not add metadata fields; the calling pipeline records category, model, prompt version and trace identity separately.
