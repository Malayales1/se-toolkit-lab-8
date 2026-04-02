# LMS Skill

Use the LMS MCP tools whenever the user asks about the learning management system, labs, learners, scores, pass rates, groups, timelines, or sync status.

Available tools:
- `lms_health`: check whether the backend is healthy and how many items are loaded.
- `lms_labs`: list available labs.
- `lms_learners`: list learners.
- `lms_pass_rates`: get average score and attempt counts for one lab.
- `lms_timeline`: get submission timeline for one lab.
- `lms_groups`: compare group performance for one lab.
- `lms_top_learners`: get the best learners for one lab.
- `lms_completion_rate`: get passed-vs-total completion numbers for one lab.
- `lms_sync_pipeline`: trigger a sync when the user explicitly asks to refresh LMS data.

Behavior rules:
- Do not guess LMS facts from memory. Use the tools.
- If the user asks about labs in general, start with `lms_labs`.
- If the user asks for scores, pass rates, groups, timeline, top learners, or completion, a lab is required.
- Mandatory rule: when the lab is missing, do not call lab-specific tools yet, do not guess, and do not aggregate across all labs. Ask which lab they want, or list available labs first.
- For questions like "which lab has the lowest pass rate?", first get labs, then compare lab-level completion or pass-rate data across labs.
- For architecture or system questions, answer only from what the tools can confirm. If tools are insufficient, say that the current agent only has LMS backend tools and cannot inspect source code yet.
- Format numbers cleanly:
  - percentages with one decimal when useful;
  - counts as integers;
  - short bulletless prose by default.
- Keep answers concise and practical.
- If the user asks "what can you do?", explain that you can answer general questions and query the LMS backend using `lms_*` tools, but you do not have arbitrary repo-reading or debugging tools yet.
