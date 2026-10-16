from __future__ import annotations

import asyncio
import base64
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, unquote, urlparse

import httpx

from .config import Settings
from .errors import GitHubError


ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".cc",
    ".cxx",
    ".c",
    ".h",
    ".hpp",
    ".rs",
    ".swift",
    ".kt",
    ".kts",
    ".sql",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".tf",
    ".bicep",
    ".ini",
    ".cfg",
    ".md",
    ".txt",
    ".sh",
    ".ps1",
}
ALLOWED_FILENAMES = {
    "dockerfile",
    "makefile",
    "procfile",
    "gemfile",
    "rakefile",
}
SKIP_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "venv",
    ".venv",
    "env",
    "site-packages",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    "target",
    "out",
    "bin",
    "obj",
    "__pycache__",
}
SECRET_NAME_PATTERN = re.compile(
    r"(^|[._-])(\.env|env|secret|credential|private|id_rsa|id_ed25519|token|key)([._-]|$)",
    re.IGNORECASE,
)
CONTEXT_ONLY_FILENAMES = {
    "readme.md",
    "readme.txt",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
}


@dataclass
class InspectedFile:
    path: str
    content: str
    size: int
    sha: str | None
    html_url: str
    context_only: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_github_repository_url(repository_url: str) -> tuple[str, str, str]:
    """Accept a canonical github.com repository URL, never credentials or a file URL."""

    parsed = urlparse(repository_url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname != "github.com":
        raise GitHubError(
            "invalid_repository_url",
            "Use a public GitHub repository URL such as https://github.com/owner/repository.",
            422,
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise GitHubError(
            "invalid_repository_url",
            "The repository URL must not contain credentials, a query, or a fragment.",
            422,
        )
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        raise GitHubError(
            "invalid_repository_url",
            "Provide the repository root URL, not a file, branch, or issue link.",
            422,
        )
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    allowed = re.compile(r"^[A-Za-z0-9_.-]+$")
    if not owner or not repository or not allowed.match(owner) or not allowed.match(repository):
        raise GitHubError("invalid_repository_url", "The GitHub owner or repository is invalid.", 422)
    return owner, repository, f"https://github.com/{owner}/{repository}"


def _path_decision(path: str, size: int | None, max_file_bytes: int) -> tuple[bool, str | None]:
    normalized = path.replace("\\", "/")
    lower = normalized.lower()
    pieces = [piece.lower() for piece in normalized.split("/")]
    filename = pieces[-1]
    if any(piece in SKIP_DIRECTORIES for piece in pieces[:-1]):
        return False, "dependency, cache, or generated directory"
    if SECRET_NAME_PATTERN.search(filename) or filename.startswith(".env"):
        return False, "potential secret file"
    if filename.endswith((".min.js", ".min.css", ".map", ".lock")):
        return False, "generated, minified, or lock file"
    if size is not None and size > max_file_bytes:
        return False, "file exceeds configured size limit"
    suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if suffix not in ALLOWED_EXTENSIONS and filename not in ALLOWED_FILENAMES:
        return False, "unsupported or likely binary file type"
    if lower.startswith("docs/") and suffix in {".md", ".txt"}:
        return True, None
    return True, None


def _is_probably_binary(content: bytes) -> bool:
    if b"\x00" in content:
        return True
    if not content:
        return False
    control_count = sum(byte < 9 or (13 < byte < 32) for byte in content)
    return control_count / len(content) > 0.18


class GitHubClient:
    """Bounded, read-only GitHub REST client. It never clones or executes repository code."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-career-coach-mvp",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> Any:
        last_transport_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await client.request(method, path, params=params)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as exc:
                last_transport_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                raise GitHubError(
                    "github_unavailable",
                    "GitHub could not be reached. Check the network and try again.",
                    503,
                ) from exc

            # GitHub returns 301 when a repository was renamed or transferred. Follow at most
            # three redirects and only within the configured GitHub API origin, so a repository
            # URL can never use the server token to redirect this client to an arbitrary host.
            redirects = 0
            redirect_transport_error: Exception | None = None
            while 300 <= response.status_code < 400:
                location = response.headers.get("Location")
                if not location:
                    raise GitHubError(
                        "github_redirect_invalid",
                        "GitHub returned an invalid redirect while reading the repository.",
                        502,
                    )
                redirect_url = response.url.join(location)
                configured = urlparse(self.settings.github_api_url)
                parsed_redirect = urlparse(str(redirect_url))
                if (
                    parsed_redirect.scheme != configured.scheme
                    or parsed_redirect.hostname != configured.hostname
                    or parsed_redirect.port != configured.port
                ):
                    raise GitHubError(
                        "github_redirect_rejected",
                        "GitHub returned a redirect outside the configured API origin; it was not followed.",
                        502,
                    )
                redirects += 1
                if redirects > 3:
                    raise GitHubError(
                        "github_redirect_limit",
                        "GitHub returned too many redirects while reading the repository.",
                        502,
                    )
                try:
                    response = await client.request(method, str(redirect_url))
                except (httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as exc:
                    redirect_transport_error = exc
                    break
            if redirect_transport_error is not None:
                last_transport_error = redirect_transport_error
                if attempt < 2:
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                raise GitHubError(
                    "github_unavailable",
                    "GitHub could not be reached. Check the network and try again.",
                    503,
                ) from redirect_transport_error

            remaining = response.headers.get("X-RateLimit-Remaining")
            retry_after = response.headers.get("Retry-After")
            if response.status_code == 403 and remaining == "0":
                details = {"retry_after_seconds": retry_after} if retry_after else None
                raise GitHubError(
                    "github_rate_limited",
                    "GitHub rate limit reached. The monitor will retry on its next check.",
                    429,
                    details,
                )
            if response.status_code == 429:
                if attempt < 2:
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                raise GitHubError(
                    "github_rate_limited",
                    "GitHub rate limit reached. The monitor will retry on its next check.",
                    429,
                )
            if response.status_code in {401}:
                raise GitHubError(
                    "github_authentication_failed",
                    "GitHub rejected the server-side token. Check GITHUB_TOKEN.",
                    401,
                )
            if response.status_code == 403:
                raise GitHubError(
                    "github_access_denied",
                    "GitHub denied access to this repository. A private repository needs a valid server-side token.",
                    403,
                )
            if response.status_code == 404:
                raise GitHubError(
                    "repository_not_found",
                    "GitHub could not find this repository or the token cannot access it.",
                    404,
                )
            if response.status_code >= 500:
                if attempt < 2:
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                raise GitHubError(
                    "github_unavailable",
                    "GitHub is temporarily unavailable. The monitor will retry later.",
                    503,
                )
            if response.is_error:
                raise GitHubError(
                    "github_request_failed",
                    "GitHub rejected the request. Verify the repository URL and try again.",
                    502,
                )
            try:
                return response.json()
            except ValueError as exc:
                raise GitHubError(
                    "github_invalid_response",
                    "GitHub returned an unexpected response.",
                    502,
                ) from exc
        raise GitHubError(
            "github_unavailable", "GitHub could not be reached. Check the network and try again.", 503
        ) from last_transport_error

    async def _metadata_and_commit(
        self, client: httpx.AsyncClient, owner: str, repository: str, ref: str | None = None
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        encoded_repo = f"{quote(owner, safe='')}/{quote(repository, safe='')}"
        metadata = await self._request_json(client, "GET", f"/repos/{encoded_repo}")
        default_branch = metadata.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch:
            raise GitHubError(
                "github_invalid_response", "GitHub did not provide a default branch for this repository.", 502
            )
        selected_ref = ref or default_branch
        commit = await self._request_json(
            client, "GET", f"/repos/{encoded_repo}/commits/{quote(selected_ref, safe='')}"
        )
        sha = commit.get("sha")
        if not isinstance(sha, str) or not sha:
            raise GitHubError("github_invalid_response", "GitHub did not provide a commit SHA.", 502)
        return metadata, commit, sha

    async def inspect_repository(self, repository_url: str, ref: str | None = None) -> dict[str, Any]:
        owner, repository, canonical_url = parse_github_repository_url(repository_url)
        timeout = httpx.Timeout(self.settings.github_timeout_seconds)
        async with httpx.AsyncClient(
            base_url=self.settings.github_api_url,
            headers=self._headers(),
            timeout=timeout,
            follow_redirects=False,
        ) as client:
            metadata, commit, sha = await self._metadata_and_commit(client, owner, repository, ref)
            resolved_owner = metadata.get("owner", {}).get("login") if isinstance(metadata.get("owner"), dict) else None
            resolved_repository = metadata.get("name")
            resolved_html_url = metadata.get("html_url")
            if isinstance(resolved_owner, str) and isinstance(resolved_repository, str):
                owner, repository, canonical_url = parse_github_repository_url(
                    resolved_html_url
                    if isinstance(resolved_html_url, str)
                    else f"https://github.com/{resolved_owner}/{resolved_repository}"
                )
            encoded_repo = f"{quote(owner, safe='')}/{quote(repository, safe='')}"
            tree = await self._request_json(
                client,
                "GET",
                f"/repos/{encoded_repo}/git/trees/{quote(sha, safe='')}",
                params={"recursive": "1"},
            )
            entries = tree.get("tree") if isinstance(tree, dict) else None
            if not isinstance(entries, list):
                raise GitHubError("github_invalid_response", "GitHub did not return a repository file tree.", 502)

            candidates: list[dict[str, Any]] = []
            skipped: list[dict[str, str]] = []
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("type") != "blob":
                    continue
                path = entry.get("path")
                if not isinstance(path, str):
                    continue
                allowed, reason = _path_decision(path, entry.get("size"), self.settings.github_max_file_bytes)
                if not allowed:
                    if len(skipped) < 80:
                        skipped.append({"path": path, "reason": reason or "not inspected"})
                    continue
                candidates.append(entry)

            def priority(entry: dict[str, Any]) -> tuple[int, str]:
                path = str(entry.get("path", "")).lower()
                if any(marker in path for marker in ("test", "spec", "api", "route", "service", "main", "app")):
                    return (0, path)
                if path.endswith((".py", ".js", ".ts", ".tsx", ".java", ".go", ".sql")):
                    return (1, path)
                return (2, path)

            candidates.sort(key=priority)
            eligible_file_count = len(candidates)
            if eligible_file_count > self.settings.github_max_files:
                for entry in candidates[self.settings.github_max_files : self.settings.github_max_files + 80]:
                    if len(skipped) >= 80:
                        break
                    skipped.append(
                        {
                            "path": str(entry.get("path", "unknown")),
                            "reason": "configured file-count limit reached",
                        }
                    )
            candidates = candidates[: self.settings.github_max_files]
            files: list[InspectedFile] = []
            total_bytes = 0
            for entry in candidates:
                path = str(entry["path"])
                content_response = await self._request_json(
                    client,
                    "GET",
                    f"/repos/{encoded_repo}/contents/{quote(path, safe='/')}",
                    params={"ref": sha},
                )
                if not isinstance(content_response, dict):
                    if len(skipped) < 80:
                        skipped.append({"path": path, "reason": "unexpected content response"})
                    continue
                reported_size = content_response.get("size", entry.get("size", 0))
                if not isinstance(reported_size, int) or reported_size < 0:
                    reported_size = 0
                if reported_size > self.settings.github_max_file_bytes:
                    if len(skipped) < 80:
                        skipped.append({"path": path, "reason": "file exceeds configured size limit"})
                    continue
                if total_bytes + reported_size > self.settings.github_max_total_bytes:
                    if len(skipped) < 80:
                        skipped.append({"path": path, "reason": "total inspection byte limit reached"})
                    continue
                encoded_content = content_response.get("content")
                if not isinstance(encoded_content, str) or content_response.get("encoding") != "base64":
                    if len(skipped) < 80:
                        skipped.append({"path": path, "reason": "GitHub did not provide readable UTF-8 content"})
                    continue
                try:
                    raw_content = base64.b64decode(encoded_content, validate=False)
                except (ValueError, TypeError):
                    if len(skipped) < 80:
                        skipped.append({"path": path, "reason": "invalid base64 content"})
                    continue
                if _is_probably_binary(raw_content):
                    if len(skipped) < 80:
                        skipped.append({"path": path, "reason": "binary content"})
                    continue
                if len(raw_content) > self.settings.github_max_file_bytes:
                    if len(skipped) < 80:
                        skipped.append({"path": path, "reason": "file exceeds configured size limit"})
                    continue
                if total_bytes + len(raw_content) > self.settings.github_max_total_bytes:
                    if len(skipped) < 80:
                        skipped.append({"path": path, "reason": "total inspection byte limit reached"})
                    continue
                total_bytes += len(raw_content)
                filename = path.rsplit("/", 1)[-1].lower()
                context_only = filename in CONTEXT_ONLY_FILENAMES or path.lower().startswith("docs/")
                files.append(
                    InspectedFile(
                        path=path,
                        content=raw_content.decode("utf-8", errors="replace"),
                        size=len(raw_content),
                        sha=content_response.get("sha") if isinstance(content_response.get("sha"), str) else None,
                        html_url=content_response.get("html_url")
                        if isinstance(content_response.get("html_url"), str)
                        else f"{canonical_url}/blob/{sha}/{quote(path, safe='/')}",
                        context_only=context_only,
                    )
                )

        commit_payload = commit.get("commit") if isinstance(commit, dict) else {}
        commit_date = commit_payload.get("author", {}).get("date") if isinstance(commit_payload, dict) else None
        return {
            "owner": owner,
            "name": repository,
            "repository_url": canonical_url,
            "default_branch": metadata.get("default_branch"),
            "commit_sha": sha,
            "commit_url": commit.get("html_url")
            if isinstance(commit.get("html_url"), str)
            else f"{canonical_url}/commit/{sha}",
            "commit_date": commit_date if isinstance(commit_date, str) else None,
            "files": [file.as_dict() for file in files],
            "inspection": {
                "inspected_at": utc_now(),
                "tree_truncated": bool(tree.get("truncated")) if isinstance(tree, dict) else False,
                "candidate_file_count": eligible_file_count,
                "inspected_file_count": len(files),
                "inspected_byte_count": total_bytes,
                "max_files": self.settings.github_max_files,
                "max_file_bytes": self.settings.github_max_file_bytes,
                "max_total_bytes": self.settings.github_max_total_bytes,
                "skipped": skipped,
            },
        }

    async def latest_commit(self, repository: dict[str, Any]) -> dict[str, Any]:
        owner = repository.get("owner")
        name = repository.get("name")
        branch = repository.get("default_branch")
        if not all(isinstance(value, str) and value for value in (owner, name, branch)):
            raise GitHubError("repository_configuration_invalid", "Stored repository details are incomplete.", 500)
        timeout = httpx.Timeout(self.settings.github_timeout_seconds)
        async with httpx.AsyncClient(
            base_url=self.settings.github_api_url,
            headers=self._headers(),
            timeout=timeout,
            follow_redirects=False,
        ) as client:
            _, commit, sha = await self._metadata_and_commit(client, owner, name, branch)
        return {
            "sha": sha,
            "url": commit.get("html_url")
            if isinstance(commit.get("html_url"), str)
            else f"https://github.com/{owner}/{name}/commit/{sha}",
        }

    async def compare_commits(
        self, repository: dict[str, Any], previous_sha: str, current_sha: str
    ) -> list[dict[str, str]]:
        owner = repository.get("owner")
        name = repository.get("name")
        if not all(isinstance(value, str) and value for value in (owner, name)):
            raise GitHubError("repository_configuration_invalid", "Stored repository details are incomplete.", 500)
        encoded_repo = f"{quote(owner, safe='')}/{quote(name, safe='')}"
        timeout = httpx.Timeout(self.settings.github_timeout_seconds)
        async with httpx.AsyncClient(
            base_url=self.settings.github_api_url,
            headers=self._headers(),
            timeout=timeout,
            follow_redirects=False,
        ) as client:
            comparison = await self._request_json(
                client,
                "GET",
                f"/repos/{encoded_repo}/compare/{quote(previous_sha, safe='')}...{quote(current_sha, safe='')}",
            )
        raw_files = comparison.get("files", []) if isinstance(comparison, dict) else []
        changes: list[dict[str, str]] = []
        for file in raw_files[:300]:
            if not isinstance(file, dict) or not isinstance(file.get("filename"), str):
                continue
            item = {"path": file["filename"], "status": str(file.get("status", "modified"))}
            if isinstance(file.get("previous_filename"), str):
                item["previous_path"] = file["previous_filename"]
            changes.append(item)
        return changes
