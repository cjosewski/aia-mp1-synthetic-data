# Course brief reconciliation — November 18, 2026

Chad supplied the Mini Project 1 course text in this session. This record
compares its explicit constraints with the engineering-code adaptation already
underway. It does not revise frozen human ratings, the original 80% agreement
rule, or historical results. The pasted text was not independently re-read
from the course portal in this checkpoint.

| Course requirement in Chad's text | Engineering project state | Disposition |
| --- | --- | --- |
| Customization may change the topic, not the technical stack or criteria | Five engineering categories replace the five DIY categories; the seven-field schema and six binary dimensions remain structurally present | Topic change is disclosed; replacement benchmark still needs disposition |
| D3 rates affordable homeowner tools | D3 rates real, available engineering APIs and libraries | Criterion changed; explicit instructor acceptance of this mapping is not in the current record |
| D4 rates DIY capability and when to call a professional | D4 rates whether engineering results need licensed-engineer review/sign-off | Criterion changed; explicit instructor acceptance of this mapping is not in the current record |
| Judge uses a lower temperature than generator | Local Qwen uses 0.1 against a higher-temperature generator; approved GPT-6.2 Astra omits temperature because its API does not support it | Local arm satisfies the literal setting; hosted arm needs a course disposition before it can replace the required assessed judge |
| Instructor and Pydantic are used for structured judge output | Local judge uses Instructor and Pydantic; isolated Astra comparison uses OpenAI strict JSON Schema plus Pydantic validation | Hosted comparison is technically structured but does not meet the literal Instructor requirement yet |
| At least 50 items, at least 20 human labels, six-dimension agreement >=80% each | Frozen engineering baseline has 50 retained items and 20 authentic reviews; Astra comparison reaches the numeric gate on those reviews | Numeric gate is measured; source-free comparison and course-conformity limitations remain separate |
| Baseline/corrected comparison, >=80% overall corrected pass and >80% failure reduction | Corrected engineering cohort exists, but the final independent comparison remains pending | Do not claim project completion from Phase A alone |

The [requirements record](requirements.md) already identified the D3/D4
mapping and benchmark replacement as unresolved instructor decisions. The new
customization text makes the constraint explicit: **a topic change alone does
not authorize changing scoring criteria**. Chad has been asked whether a
specific instructor decision approved those mappings. Until such evidence is
recorded, describe the engineering rubric as an owner adaptation and keep
course acceptance unresolved.

The Astra experiment remains useful evidence of model behavior. Its
per-dimension agreement does not by itself establish compliance with the
course's lower-temperature and Instructor requirements. The local Qwen control
continues under the original toolchain and lower temperature.
