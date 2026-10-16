# Problem statement traceability

The supplied official brief is **W-PS-2: AI Career Coach** in `Actual Problem Statement/Agentic AI Track.pdf`, combined pages 5-7. It asks for a live loop:

```text
real job requirements -> GitHub repository evidence -> evidence-backed gaps
-> real code commit -> automatic updated assessment
```

This implementation maps each mandatory point to a concrete behavior:

| Official requirement | MVP behavior |
| --- | --- |
| Real job or internship requirements and source link | The job form persists the title, company, source URL, pasted description, and directly matched source excerpts. A fetch helper is available, but manual text remains supported. |
| Actual GitHub repository | The backend uses the GitHub REST API to read the repository metadata, default branch, commit SHA, tree, and bounded file contents. |
| Traceable portfolio evidence | Each displayed signal includes a path, line range, source excerpt, commit SHA, confidence, explanation, and limitations. Evidence is checked against inspected content before storage. |
| Clear gaps | Missing signals are labelled **not demonstrated in this inspected scope**. The product never concludes that a student lacks the skill. |
| Detect changes and reassess | A server-side polling loop checks the default branch SHA. A different SHA triggers a fresh inspection and snapshot automatically. |
| Before/after proof | SQLite preserves immutable snapshots, changed-file metadata where GitHub comparison is available, and a comparison of added/removed validated evidence. |

Optional features from the brief are intentionally narrow. The product provides evidence-building tasks, clearly labelled as future recommendations; it does not claim resume generation, job application tracking, authorship verification, production experience, or hiring recommendations.
