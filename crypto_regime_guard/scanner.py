from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_QUERIES = [
    "crypto trading bot",
    "cryptocurrency trading bot",
    "bitcoin trading bot",
    "freqtrade strategy",
    "grid trading bot crypto",
    "crypto market making bot",
    "crypto arbitrage bot",
    "binance trading bot",
    "bybit trading bot",
    "algorithmic trading crypto",
]

SUSPICIOUS_KEYWORDS = [
    "hack",
    "cheat",
    "crack",
    "private-key",
    "seed phrase",
    "free money",
    "sniper",
    "stealer",
    "pump",
]


@dataclass(frozen=True)
class RepoEvaluation:
    full_name: str
    html_url: str
    description: str
    stars: int
    forks: int
    open_issues: int
    language: str
    pushed_at: str
    archived: bool
    license_key: str
    score: float
    verdict: str
    risk_flags: str


class GitHubRepoScanner:
    def __init__(self, token: str | None = None, sleep_seconds: float = 0.2) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.sleep_seconds = sleep_seconds

    def search(self, limit: int = 350, include_owner_repos: bool = False) -> list[RepoEvaluation]:
        seen: dict[str, dict[str, Any]] = {}
        per_page = 100
        for query in DEFAULT_QUERIES:
            for page in range(1, 5):
                if len(seen) >= limit:
                    break
                payload = self._get_json(
                    "https://api.github.com/search/repositories?"
                    + urllib.parse.urlencode(
                        {
                            "q": f"{query} in:name,description,topics",
                            "sort": "stars",
                            "order": "desc",
                            "per_page": per_page,
                            "page": page,
                        }
                    )
                )
                for item in payload.get("items", []):
                    seen.setdefault(item["full_name"], item)
                    if len(seen) >= limit:
                        break
                time.sleep(self.sleep_seconds)
            if len(seen) >= limit:
                break

        if include_owner_repos:
            for item in self._owner_repos():
                text = f"{item.get('name', '')} {item.get('description', '')}".lower()
                if any(term in text for term in ["crypto", "trading", "bot", "freqtrade", "backtest"]):
                    seen.setdefault(item["full_name"], item)

        evaluations = [self.evaluate_repo(item) for item in seen.values()]
        evaluations.sort(key=lambda repo: (repo.score, repo.stars), reverse=True)
        return evaluations[:limit]

    def evaluate_repo(self, item: dict[str, Any]) -> RepoEvaluation:
        description = item.get("description") or ""
        full_name = item.get("full_name") or ""
        text = f"{full_name} {description}".lower()
        pushed_at = item.get("pushed_at") or "1970-01-01T00:00:00Z"
        archived = bool(item.get("archived"))
        stars = int(item.get("stargazers_count") or 0)
        forks = int(item.get("forks_count") or 0)
        open_issues = int(item.get("open_issues_count") or 0)
        license_info = item.get("license") or {}
        license_key = license_info.get("key") or "unknown"
        risk_flags = [keyword for keyword in SUSPICIOUS_KEYWORDS if keyword in text]

        score = self._score(stars, forks, pushed_at, archived, license_key, risk_flags, text)
        verdict = self._verdict(score, archived, risk_flags)
        return RepoEvaluation(
            full_name=full_name,
            html_url=item.get("html_url") or "",
            description=description.replace("\n", " "),
            stars=stars,
            forks=forks,
            open_issues=open_issues,
            language=item.get("language") or "",
            pushed_at=pushed_at,
            archived=archived,
            license_key=license_key,
            score=round(score, 2),
            verdict=verdict,
            risk_flags=",".join(risk_flags),
        )

    def _score(
        self,
        stars: int,
        forks: int,
        pushed_at: str,
        archived: bool,
        license_key: str,
        risk_flags: list[str],
        text: str,
    ) -> float:
        star_score = min(30.0, math.log10(stars + 1) * 8.0)
        fork_score = min(12.0, math.log10(forks + 1) * 5.0)
        recency_score = self._recency_score(pushed_at)
        license_score = 8.0 if license_key and license_key != "unknown" else 0.0
        relevance_score = 20.0 if "trading" in text and "bot" in text else 10.0
        penalty = 0.0
        if archived:
            penalty += 25.0
        penalty += min(35.0, 8.0 * len(risk_flags))
        return max(0.0, star_score + fork_score + recency_score + license_score + relevance_score - penalty)

    @staticmethod
    def _recency_score(pushed_at: str) -> float:
        try:
            pushed = dt.datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
        age_days = (dt.datetime.now(dt.UTC) - pushed).days
        if age_days <= 90:
            return 30.0
        if age_days <= 365:
            return 22.0
        if age_days <= 730:
            return 12.0
        if age_days <= 1460:
            return 5.0
        return 0.0

    @staticmethod
    def _verdict(score: float, archived: bool, risk_flags: list[str]) -> str:
        if risk_flags:
            return "avoid-review-security"
        if archived:
            return "historical-only"
        if score >= 70:
            return "strong-candidate"
        if score >= 50:
            return "watchlist"
        if score >= 30:
            return "niche-or-early"
        return "low-signal"

    def _owner_repos(self) -> list[dict[str, Any]]:
        if not self.token:
            return []
        repos: list[dict[str, Any]] = []
        for page in range(1, 6):
            payload = self._get_json(
                "https://api.github.com/user/repos?"
                + urllib.parse.urlencode(
                    {
                        "affiliation": "owner",
                        "per_page": 100,
                        "page": page,
                        "sort": "updated",
                    }
                )
            )
            if not payload:
                break
            repos.extend(payload)
            time.sleep(self.sleep_seconds)
        return repos

    def _get_json(self, url: str) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "crypto-regime-guard-research-scanner",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310 - GitHub API only
            return json.loads(response.read().decode("utf-8"))


def write_csv(evaluations: list[RepoEvaluation], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RepoEvaluation.__dataclass_fields__.keys()))
        writer.writeheader()
        for item in evaluations:
            writer.writerow(item.__dict__)


def write_markdown(evaluations: list[RepoEvaluation], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# GitHub Crypto Trading Bot Evaluation",
        "",
        f"Generated rows: {len(evaluations)}",
        "",
        "Scoring is a triage heuristic, not investment advice and not a security audit.",
        "",
        "| Rank | Repo | Stars | Pushed | Score | Verdict | Risk flags |",
        "|---:|---|---:|---|---:|---|---|",
    ]
    for rank, item in enumerate(evaluations, start=1):
        lines.append(
            f"| {rank} | [{item.full_name}]({item.html_url}) | {item.stars} | "
            f"{item.pushed_at[:10]} | {item.score:.2f} | {item.verdict} | {item.risk_flags} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate GitHub crypto trading bot repositories.")
    parser.add_argument("--limit", type=int, default=350)
    parser.add_argument("--output", type=Path, default=Path("artifacts/repo-evaluation.csv"))
    parser.add_argument("--markdown", type=Path, default=Path("artifacts/repo-evaluation.md"))
    parser.add_argument("--include-owner-repos", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scanner = GitHubRepoScanner()
    evaluations = scanner.search(limit=args.limit, include_owner_repos=args.include_owner_repos)
    write_csv(evaluations, args.output)
    write_markdown(evaluations, args.markdown)
    print(f"wrote {len(evaluations)} evaluations to {args.output} and {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
