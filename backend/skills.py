from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SkillRule:
    key: str
    name: str
    aliases: tuple[str, ...]
    code_patterns: tuple[str, ...]
    recommendation: str
    extensions: tuple[str, ...] = ()
    configuration_only: bool = False


RULES: tuple[SkillRule, ...] = (
    SkillRule(
        "api_development",
        "API development",
        ("api development", "apis", "api", "rest api", "restful api", "backend api"),
        (
            r"@(?:app|router|api)\.(?:get|post|put|patch|delete|route)\b",
            r"\b(?:app|router)\.(?:get|post|put|patch|delete|route)\s*\(",
            r"\b(?:FastAPI|Flask)\s*\(",
            r"\bexpress\s*\(",
            r"@(?:Get|Post|Put|Delete|Patch|Request)Mapping\b",
        ),
        "Add a small, documented endpoint with input validation and request/response tests, then commit both the route and tests.",
        (".py", ".js", ".mjs", ".cjs", ".ts", ".java", ".cs", ".go", ".rb", ".php"),
    ),
    SkillRule(
        "sql_databases",
        "SQL and database queries",
        ("sql", "postgresql", "postgres", "mysql", "sqlite", "database queries"),
        (
            r"\b(?:SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|CREATE\s+TABLE|ALTER\s+TABLE|JOIN)\b",
            r"\b(?:execute|executemany|query)\s*\(",
            r"\b(?:create_engine|sqlite3\.connect|psycopg|mysql\.connector)\b",
        ),
        "Add a parameterized query or migration plus a test that exercises the data path; avoid committing credentials or production data.",
        (".py", ".sql", ".js", ".ts", ".java", ".go", ".rb", ".php", ".cs"),
    ),
    SkillRule(
        "automated_testing",
        "Automated testing",
        ("automated testing", "automated tests", "unit testing", "unit tests", "integration testing", "integration tests", "testing", "pytest", "jest"),
        (
            r"\b(?:def\s+test_[A-Za-z0-9_]*|test\s*\(|it\s*\(|describe\s*\()",
            r"\b(?:assert|expect\s*\(|self\.assert[A-Za-z_]*\s*\(|pytest\.raises\s*\()",
        ),
        "Write a focused automated test with a real assertion for a requirement-relevant behavior, and keep it beside the implementation in the next commit.",
        (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".go", ".rb", ".php", ".cs"),
    ),
    SkillRule(
        "python",
        "Python",
        ("python", "python3"),
        (r"^\s*(?:from\s+[A-Za-z_][\w.]*\s+import|import\s+[A-Za-z_][\w.]*|def\s+\w+\s*\(|class\s+\w+)",),
        "Add a focused Python module that implements a job-relevant behavior and accompany it with a test or runnable example.",
        (".py",),
    ),
    SkillRule(
        "javascript",
        "JavaScript",
        ("javascript", "ecmascript", "node.js", "nodejs"),
        (r"\b(?:const|let|var|function|async\s+function|module\.exports|export\s+(?:default|const|function|class))\b",),
        "Add a small JavaScript module with a clear interface and a test that shows its expected behavior.",
        (".js", ".mjs", ".cjs", ".jsx"),
    ),
    SkillRule(
        "typescript",
        "TypeScript",
        ("typescript", "type script"),
        (r"\b(?:interface\s+\w+|type\s+\w+\s*=|enum\s+\w+|:\s*(?:string|number|boolean|Promise|[A-Z]\w*))",),
        "Add a typed TypeScript feature and a test or type-safe API boundary that makes the contract visible in the repository.",
        (".ts", ".tsx"),
    ),
    SkillRule(
        "fastapi",
        "FastAPI",
        ("fastapi",),
        (r"\b(?:FastAPI|APIRouter)\s*\(", r"@(?:app|router)\.(?:get|post|put|patch|delete)\b"),
        "Add a FastAPI route with a request model and a route-level test that records the observable behavior.",
        (".py",),
    ),
    SkillRule(
        "flask",
        "Flask",
        ("flask",),
        (r"\bFlask\s*\(", r"@\w+\.route\s*\("),
        "Add a Flask route and a test-client assertion that documents its behavior.",
        (".py",),
    ),
    SkillRule(
        "react",
        "React",
        ("react", "react.js", "reactjs"),
        (r"\b(?:useState|useEffect|useMemo|useCallback|React\.createElement)\s*\(", r"\bimport\s+React\b"),
        "Add a small React component with meaningful state or rendering logic and a component test or documented interaction.",
        (".jsx", ".tsx", ".js", ".ts"),
    ),
    SkillRule(
        "html_css",
        "HTML and CSS",
        ("html", "css", "html/css", "frontend styling"),
        (r"<\s*(?:html|main|section|form|button|div)\b", r"(?:^|\})\s*[.#]?[A-Za-z][\w-]*(?:\s*[,>{:]|\s*\{)"),
        "Add a semantic page or component with responsive styles and link it to an observable user flow.",
        (".html", ".htm", ".css", ".scss"),
    ),
    SkillRule(
        "docker",
        "Docker and containers",
        ("docker", "containerization", "containers"),
        (r"^\s*FROM\s+\S+", r"^\s*(?:CMD|ENTRYPOINT)\s+"),
        "Add a minimal Dockerfile and a short run command that builds and starts the project without embedding secrets.",
        (),
        True,
    ),
    SkillRule(
        "ci_cd",
        "CI/CD",
        ("ci/cd", "continuous integration", "continuous deployment", "github actions", "pipeline"),
        (r"^\s*jobs\s*:", r"^\s*(?:steps|on)\s*:"),
        "Add a CI workflow that installs dependencies and runs a focused test command on pull requests.",
        (".yml", ".yaml"),
        True,
    ),
    SkillRule(
        "deployment",
        "Deployment",
        ("deployment", "deploying", "deployed", "deploy"),
        (r"\b(?:deploy|deployment|render\.com|vercel|railway|fly\.io|heroku)\b",),
        "Add a deployment configuration or documented release workflow, and make clear which environment it targets without exposing credentials.",
        (".yml", ".yaml", ".toml", ".json", ".md", ".sh", ".ps1"),
        True,
    ),
    SkillRule(
        "aws",
        "AWS",
        ("aws", "amazon web services", "s3", "lambda"),
        (r"\b(?:boto3|aws_(?:lambda|s3)|AWS::|aws\s+(?:s3|lambda|deploy))\b",),
        "Add a minimal, non-secret cloud integration or infrastructure definition with a testable local boundary.",
        (".py", ".js", ".ts", ".yml", ".yaml", ".json", ".tf"),
        True,
    ),
    SkillRule(
        "azure",
        "Azure",
        ("azure", "microsoft azure", "azure functions"),
        (r"\b(?:azure\.|@azure/|AzureWebJobs|func\s+azure|Microsoft\.(?:App|KeyVault|Storage|DBforPostgreSQL|OperationalInsights)/)\b",),
        "Add a minimal Azure integration or infrastructure definition and a local test boundary; never commit credentials.",
        (".py", ".js", ".ts", ".yml", ".yaml", ".json", ".bicep"),
        True,
    ),
    SkillRule(
        "machine_learning",
        "Machine learning",
        ("machine learning", "ml", "scikit-learn", "tensorflow", "pytorch"),
        (r"\b(?:sklearn|tensorflow|torch|keras|\.fit\s*\(|predict\s*\()",),
        "Add a reproducible training or inference boundary with a small evaluation or test and document the data limitations.",
        (".py", ".ipynb"),
    ),
    SkillRule(
        "retrieval_augmented_generation",
        "Retrieval-augmented generation (RAG)",
        ("retrieval augmented generation", "retrieval-augmented generation", "rag"),
        (
            r"\b(?:as_retriever|similarity_search(?:_with_score)?|get_relevant_documents|retrieve\s*\()\b",
            r"\b(?:Chroma|FAISS|Pinecone|Qdrant|Weaviate|VectorStore|vectorstore)\b",
        ),
        "Add a retrieval call and a vector-store integration in executable source, plus a focused test that checks the retrieved context is passed into the answer boundary.",
        (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx"),
    ),
    SkillRule(
        "embeddings_vector_search",
        "Embeddings and vector search",
        ("embeddings", "embedding", "vector search", "vector database", "vector store", "chroma", "faiss", "pinecone", "qdrant"),
        (r"\b(?:OpenAIEmbeddings|HuggingFaceEmbeddings|embed_query|embed_documents|Chroma|FAISS|Pinecone|Qdrant|Weaviate|VectorStore)\b",),
        "Add an explicit embedding or vector-store call with a small retrieval test; document only the sample data and boundaries that the repository actually uses.",
        (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx"),
    ),
    SkillRule(
        "llm_integration",
        "LLM integration",
        ("llm", "large language model", "large language models", "openai api", "generative ai", "grok"),
        (r"\b(?:OpenAI|ChatOpenAI|AzureOpenAI|Anthropic|Grok|client\.(?:responses|chat\.completions))\b",),
        "Add a narrow LLM request boundary with validated inputs, a safe fallback, and a test that proves the model output cannot fabricate evidence or credentials.",
        (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx"),
    ),
    SkillRule(
        "java",
        "Java",
        ("java",),
        (r"\b(?:public\s+(?:class|static)|import\s+java\.|class\s+\w+)\b",),
        "Add a small Java class with a focused behavior and an automated test.",
        (".java",),
    ),
    SkillRule(
        "cpp",
        "C++",
        ("c++", "cplusplus"),
        (r"(?:\bstd::|#include\s*<|\btemplate\s*<|\bclass\s+\w+)",),
        "Add a focused C++ module with an executable behavior and automated tests or a reproducible build command.",
        (".cpp", ".cc", ".cxx", ".hpp", ".h"),
    ),
    SkillRule(
        "git_github",
        "Git and GitHub",
        ("git", "github", "version control"),
        (),
        "Make meaningful, reviewable commits and include a pull-request-ready change with tests or documentation; repository access alone is not treated as proof of Git skill.",
    ),
)

RULE_BY_KEY = {rule.key: rule for rule in RULES}
PREFERRED_MARKERS = re.compile(r"\b(?:preferred|nice\s+to\s+have|bonus|plus|desired|advantage)\b", re.IGNORECASE)


def _alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(alias) + r"(?![A-Za-z0-9_])", re.IGNORECASE)


def _segments(description: str) -> Iterable[tuple[int, str]]:
    for line_number, raw_line in enumerate(description.splitlines() or [description], start=1):
        line = raw_line.strip(" \t•-–")
        if not line:
            continue
        fragments = re.split(r"(?<=[.!?;])\s+(?=[A-Z0-9])", line)
        for fragment in fragments:
            cleaned = fragment.strip()
            if cleaned:
                yield line_number, cleaned


def extract_job_skills(description: str) -> list[dict[str, Any]]:
    """Normalize only directly mentioned skill phrases; unknown text is deliberately not guessed."""

    normalized: list[dict[str, Any]] = []
    for rule in RULES:
        matches: list[tuple[int, str, str, bool]] = []
        for line_number, segment in _segments(description):
            for alias in sorted(rule.aliases, key=len, reverse=True):
                match = _alias_pattern(alias).search(segment)
                if match:
                    matches.append((line_number, segment[:360], match.group(0), bool(PREFERRED_MARKERS.search(segment))))
                    break
        if not matches:
            continue
        # A direct required mention wins over a preferred-only mention.
        selected = next((item for item in matches if not item[3]), matches[0])
        normalized.append(
            {
                "key": rule.key,
                "name": rule.name,
                "requirement_type": "preferred" if selected[3] else "required",
                "matched_phrase": selected[2],
                "source_excerpt": selected[1],
                "source_line": selected[0],
            }
        )
    return normalized


def _is_comment_or_blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith(("#", "//", "/*", "*", "<!--", "--"))


def _extension(path: str) -> str:
    filename = path.rsplit("/", 1)[-1].lower()
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1]


def _is_relevant_file(rule: SkillRule, path: str) -> bool:
    lower_path = path.lower()
    filename = lower_path.rsplit("/", 1)[-1]
    if rule.key == "docker":
        return filename == "dockerfile" or "docker" in filename or "compose" in filename
    if rule.key == "ci_cd":
        return lower_path.startswith(".github/workflows/") or "pipeline" in filename or "ci" in filename
    if rule.extensions:
        return _extension(path) in rule.extensions
    return True


def _excerpt(lines: list[str], line_number: int) -> tuple[int, int, str]:
    start = max(1, line_number - 1)
    end = min(len(lines), line_number + 1)
    return start, end, "\n".join(lines[start - 1 : end])[:900]


def _evidence(
    file: dict[str, Any], lines: list[str], line_number: int, kind: str, strength: float, changed_paths: set[str]
) -> dict[str, Any]:
    start_line, end_line, excerpt = _excerpt(lines, line_number)
    path = str(file["path"])
    file_url = file.get("html_url") or ""
    if isinstance(file_url, str) and file_url:
        file_url = f"{file_url.split('#', 1)[0]}#L{start_line}-L{end_line}"
    else:
        file_url = ""
    return {
        "path": path,
        "start_line": start_line,
        "end_line": end_line,
        "excerpt": excerpt,
        "url": file_url,
        "kind": kind,
        "strength": strength,
        "changed_in_commit": path in changed_paths,
    }

def _scan_rule(
    rule: SkillRule, files: list[dict[str, Any]], changed_paths: set[str]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    results: list[dict[str, Any]] = []
    special_counts = {
        "test_declaration": 0,
        "test_assertion": 0,
        "docker_from": 0,
        "docker_command": 0,
        "ci_jobs": 0,
        "ci_steps": 0,
        "rag_retrieval": 0,
        "rag_vector_store": 0,
    }
    seen: set[tuple[str, int, str]] = set()
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in rule.code_patterns]

    for file in files:
        path = file.get("path")
        content = file.get("content")
        if not isinstance(path, str) or not isinstance(content, str) or not _is_relevant_file(rule, path):
            continue
        lines = content.splitlines()
        context_only = bool(file.get("context_only"))
        for line_number, line in enumerate(lines, start=1):
            if _is_comment_or_blank(line):
                continue
            for pattern_index, pattern in enumerate(compiled_patterns):
                if not pattern.search(line):
                    continue
                if rule.key == "automated_testing":
                    kind = "test declaration" if pattern_index == 0 else "test assertion"
                    special_counts["test_declaration" if pattern_index == 0 else "test_assertion"] += 1
                elif rule.key == "docker":
                    kind = "container build instruction" if pattern_index == 0 else "container run instruction"
                    special_counts["docker_from" if pattern_index == 0 else "docker_command"] += 1
                elif rule.key == "ci_cd":
                    kind = "CI workflow job" if pattern_index == 0 else "CI workflow trigger or step"
                    special_counts["ci_jobs" if pattern_index == 0 else "ci_steps"] += 1
                elif rule.key == "retrieval_augmented_generation":
                    kind = "retrieval operation" if pattern_index == 0 else "vector-store integration"
                    special_counts["rag_retrieval" if pattern_index == 0 else "rag_vector_store"] += 1
                elif rule.configuration_only:
                    kind = "configuration signal"
                else:
                    kind = "source implementation"
                strength = 0.32 if context_only else (0.65 if rule.configuration_only else 0.9)
                marker = (path, line_number, kind)
                if marker not in seen:
                    seen.add(marker)
                    results.append(_evidence(file, lines, line_number, kind, strength, changed_paths))
                break
    # Multiple evidence points are useful, but an assessment should stay readable.
    results.sort(key=lambda item: (-float(item["strength"]), not bool(item["changed_in_commit"]), item["path"], item["start_line"]))
    return results[:5], special_counts


def validate_evidence(evidence: dict[str, Any], files: list[dict[str, Any]]) -> bool:
    """Reject stale or fabricated references before they can reach a snapshot or UI."""

    path = evidence.get("path")
    start_line = evidence.get("start_line")
    end_line = evidence.get("end_line")
    excerpt = evidence.get("excerpt")
    if not isinstance(path, str) or not isinstance(start_line, int) or not isinstance(end_line, int) or not isinstance(excerpt, str):
        return False
    if start_line < 1 or end_line < start_line:
        return False
    for file in files:
        if file.get("path") != path or not isinstance(file.get("content"), str):
            continue
        lines = str(file["content"]).splitlines()
        if end_line > len(lines):
            return False
        expected = "\n".join(lines[start_line - 1 : end_line])[:900]
        return expected == excerpt
    return False


def _status_for(rule: SkillRule, evidence: list[dict[str, Any]], counts: dict[str, int]) -> tuple[str, str, str]:
    direct = [item for item in evidence if float(item["strength"]) >= 0.8]
    contextual = [item for item in evidence if float(item["strength"]) < 0.8]
    if rule.key == "automated_testing":
        if counts["test_declaration"] and counts["test_assertion"] and direct:
            return "demonstrated", "demonstrated", "high" if len(direct) >= 2 else "medium"
        if direct or contextual:
            return "partially_demonstrated", "partially demonstrated", "low"
    elif rule.key == "docker":
        if counts["docker_from"] and counts["docker_command"] and evidence:
            return "demonstrated", "demonstrated", "medium"
        if evidence:
            return "partially_demonstrated", "partially demonstrated", "low"
    elif rule.key == "ci_cd":
        if counts["ci_jobs"] and counts["ci_steps"] and evidence:
            return "demonstrated", "demonstrated", "medium"
        if evidence:
            return "partially_demonstrated", "partially demonstrated", "low"
    elif rule.key == "retrieval_augmented_generation":
        if counts["rag_retrieval"] and counts["rag_vector_store"] and evidence:
            return "demonstrated", "demonstrated", "medium"
        if direct or contextual:
            return "partially_demonstrated", "partially demonstrated", "low"
    elif direct:
        return "demonstrated", "demonstrated", "high" if len(direct) >= 2 else "medium"
    elif contextual:
        return "partially_demonstrated", "partially demonstrated", "low"
    return "not_demonstrated", "not demonstrated in this inspected scope", "low"


def _limitations(inspection: dict[str, Any], status_code: str, evidence: list[dict[str, Any]]) -> list[str]:
    limits = [
        f"Assessment is limited to {inspection.get('inspected_file_count', 0)} inspected files at this commit; repository code was never executed."
    ]
    if inspection.get("tree_truncated"):
        limits.append("GitHub reported a truncated file tree, so repository coverage is incomplete.")
    if inspection.get("skipped"):
        limits.append("Some files were intentionally skipped because of safety, size, generated-file, dependency, binary, or potential-secret filters.")
    if status_code == "not_demonstrated":
        limits.append("Missing evidence means not demonstrated in this inspected scope; it is not proof that the student lacks the skill.")
    elif evidence and all(float(item["strength"]) < 0.8 for item in evidence):
        limits.append("The available signal is contextual or configuration-only and is not treated as proof of mastery.")
    else:
        limits.append("Source evidence demonstrates implementation signals, not proficiency, authorship, production use, or the completeness of the project.")
    return limits


def _explanation(status_code: str, skill_name: str, evidence: list[dict[str, Any]], inspected_file_count: int) -> str:
    if status_code == "not_demonstrated":
        return (
            f"No validated source evidence for {skill_name} was found in {inspected_file_count} inspected files. "
            "It is not demonstrated in this inspected scope; that is not proof that the student lacks the skill."
        )
    primary = evidence[0]
    location = f"{primary['path']} lines {primary['start_line']}-{primary['end_line']}"
    if status_code == "partially_demonstrated":
        return (
            f"Limited or contextual evidence appears at {location}. It supports a partial signal only and should not be read as proof of mastery."
        )
    return (
        f"Validated implementation evidence appears at {location}. This supports demonstrated repository evidence for this requirement at the inspected commit, not a claim of mastery."
    )


def _claim_boundary(status_code: str, skill_name: str) -> str:
    if status_code == "not_demonstrated":
        return (
            f"No source evidence for {skill_name} was returned in this bounded scan. This is a scope finding, not proof that the student lacks the skill."
        )
    if status_code == "partially_demonstrated":
        return (
            f"The source contains a limited signal for {skill_name}. It does not prove mastery, authorship, production use, or the completeness of the project."
        )
    return (
        f"The source demonstrates an implementation signal for {skill_name} at this commit. It does not prove mastery, authorship, seniority, or hiring readiness."
    )


def build_assessment(
    job: dict[str, Any],
    inspection_result: dict[str, Any],
    changed_files: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Produce a deterministic, citation-validated assessment from an already-inspected tree."""

    files = inspection_result.get("files", [])
    if not isinstance(files, list):
        files = []
    inspection = inspection_result.get("inspection", {})
    if not isinstance(inspection, dict):
        inspection = {}
    changed_paths: set[str] = set()
    for item in changed_files or []:
        if isinstance(item, dict):
            for key in ("path", "previous_path"):
                value = item.get(key)
                if isinstance(value, str):
                    changed_paths.add(value)

    skill_assessments: list[dict[str, Any]] = []
    for requirement in job.get("skills", []):
        if not isinstance(requirement, dict):
            continue
        rule = RULE_BY_KEY.get(requirement.get("key"))
        if not rule:
            continue
        raw_evidence, counts = _scan_rule(rule, files, changed_paths)
        evidence = [item for item in raw_evidence if validate_evidence(item, files)]
        status_code, status, confidence = _status_for(rule, evidence, counts)
        skill_assessments.append(
            {
                "skill_key": rule.key,
                "skill": rule.name,
                "requirement_type": requirement.get("requirement_type", "required"),
                "job_requirement": {
                    "matched_phrase": requirement.get("matched_phrase", rule.name),
                    "source_excerpt": requirement.get("source_excerpt", ""),
                    "source_line": requirement.get("source_line"),
                },
                "status_code": status_code,
                "status": status,
                "confidence": confidence,
                "evidence": evidence,
                "changed_evidence": [item for item in evidence if item.get("changed_in_commit")],
                "limitations": _limitations(inspection, status_code, evidence),
                "explanation": _explanation(
                    status_code, rule.name, evidence, int(inspection.get("inspected_file_count", len(files)) or 0)
                ),
                "claim_boundary": _claim_boundary(status_code, rule.name),
                "next_evidence_contract": {
                    "type": "future_evidence_contract",
                    "task": rule.recommendation,
                    "purpose": "This is a future task intended to generate stronger repository evidence. It is not an existing achievement.",
                }
                if status_code != "demonstrated"
                else None,
            }
        )

    required = [item for item in skill_assessments if item["requirement_type"] == "required"]
    weighted_items = skill_assessments or []
    value_by_status = {"demonstrated": 1.0, "partially_demonstrated": 0.5, "not_demonstrated": 0.0}
    weighted_total = sum(1.0 if item["requirement_type"] == "required" else 0.5 for item in weighted_items)
    weighted_score = sum(
        (1.0 if item["requirement_type"] == "required" else 0.5)
        * value_by_status[item["status_code"]]
        for item in weighted_items
    )
    score = round((weighted_score / weighted_total) * 100) if weighted_total else None
    recommendations: list[dict[str, str]] = []
    for item in skill_assessments:
        if item["status_code"] == "demonstrated":
            continue
        rule = RULE_BY_KEY[item["skill_key"]]
        recommendations.append(
            {
                "type": "future_recommendation",
                "skill": item["skill"],
                "action": rule.recommendation,
                "reason": "This is a suggested next step to generate stronger evidence. It is not an existing achievement.",
            }
        )

    counts_summary = {
        "demonstrated": sum(item["status_code"] == "demonstrated" for item in skill_assessments),
        "partially_demonstrated": sum(item["status_code"] == "partially_demonstrated" for item in skill_assessments),
        "not_demonstrated": sum(item["status_code"] == "not_demonstrated" for item in skill_assessments),
        "required_skills": len(required),
        "all_supported_skills": len(skill_assessments),
    }
    return {
        "version": "deterministic-evidence-v1",
        "assessed_at": utc_now(),
        "inspected_commit_sha": inspection_result.get("commit_sha"),
        "skill_assessments": skill_assessments,
        "summary": counts_summary,
        "fit_score": {
            "value": score,
            "formula": "Required skills count as 1; preferred skills count as 0.5. Demonstrated=1, partially demonstrated=0.5, not demonstrated in this inspected scope=0. The total is a traceability aid, not a hiring recommendation.",
            "limitations": "The score reflects only supported requirement phrases and bounded repository evidence at one commit. It does not measure proficiency, authorship, interview performance, or all work the student has done.",
        },
        "recommendations": recommendations,
        "scope_notice": "Evidence is deterministic and linked to the inspected commit. Missing evidence means not demonstrated in this inspected scope, not proof that the student lacks the skill.",
        "inspection_limits": {
            "inspected_file_count": inspection.get("inspected_file_count", len(files)),
            "candidate_file_count": inspection.get("candidate_file_count"),
            "inspected_byte_count": inspection.get("inspected_byte_count"),
            "tree_truncated": bool(inspection.get("tree_truncated")),
            "skipped_file_count": len(inspection.get("skipped", []) if isinstance(inspection.get("skipped"), list) else []),
        },
    }


def compare_assessments(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Compare stored evidence snapshots without reinterpreting the source tree."""

    previous_items = {
        item.get("skill_key"): item
        for item in previous.get("skill_assessments", [])
        if isinstance(item, dict) and item.get("skill_key")
    }
    current_items = {
        item.get("skill_key"): item
        for item in current.get("skill_assessments", [])
        if isinstance(item, dict) and item.get("skill_key")
    }
    changes: list[dict[str, Any]] = []
    for key in sorted(set(previous_items) | set(current_items)):
        before = previous_items.get(key)
        after = current_items.get(key)
        if before is None or after is None:
            continue
        def fingerprint(item: dict[str, Any]) -> tuple[str, int, int, str]:
            return (
                str(item.get("path", "")),
                int(item.get("start_line", 0)),
                int(item.get("end_line", 0)),
                str(item.get("excerpt", "")),
            )
        before_evidence = {fingerprint(item): item for item in before.get("evidence", []) if isinstance(item, dict)}
        after_evidence = {fingerprint(item): item for item in after.get("evidence", []) if isinstance(item, dict)}
        added = [after_evidence[item] for item in after_evidence.keys() - before_evidence.keys()]
        removed = [before_evidence[item] for item in before_evidence.keys() - after_evidence.keys()]
        status_changed = before.get("status_code") != after.get("status_code")
        if status_changed or added or removed:
            changes.append(
                {
                    "skill_key": key,
                    "skill": after.get("skill") or before.get("skill"),
                    "before_status": before.get("status"),
                    "after_status": after.get("status"),
                    "status_changed": status_changed,
                    "evidence_added": added,
                    "evidence_removed": removed,
                    "claim_boundary": after.get("claim_boundary") or before.get("claim_boundary"),
                    "next_evidence_contract": after.get("next_evidence_contract"),
                }
            )
    current_score = current.get("fit_score", {}).get("value") if isinstance(current.get("fit_score"), dict) else None
    previous_score = previous.get("fit_score", {}).get("value") if isinstance(previous.get("fit_score"), dict) else None
    return {
        "previous_score": previous_score,
        "current_score": current_score,
        "score_delta": (current_score - previous_score)
        if isinstance(current_score, (int, float)) and isinstance(previous_score, (int, float))
        else None,
        "skill_changes": changes,
        "message": "No tracked skill status or validated evidence changed between these snapshots."
        if not changes
        else "Assessment differences are computed from stored, validated evidence excerpts.",
    }
