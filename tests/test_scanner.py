from crypto_regime_guard.scanner import GitHubRepoScanner


def test_scanner_scores_archived_and_suspicious_lower() -> None:
    scanner = GitHubRepoScanner(token=None)
    good = scanner.evaluate_repo(
        {
            "full_name": "example/crypto-trading-bot",
            "html_url": "https://github.com/example/crypto-trading-bot",
            "description": "safe crypto trading bot with backtesting",
            "stargazers_count": 1000,
            "forks_count": 100,
            "open_issues_count": 5,
            "language": "Python",
            "pushed_at": "2026-06-01T00:00:00Z",
            "archived": False,
            "license": {"key": "mit"},
        }
    )
    bad = scanner.evaluate_repo(
        {
            "full_name": "example/crypto-bot-crack-hack",
            "html_url": "https://github.com/example/crypto-bot-crack-hack",
            "description": "free money hack cheat",
            "stargazers_count": 1000,
            "forks_count": 100,
            "open_issues_count": 5,
            "language": "Python",
            "pushed_at": "2026-06-01T00:00:00Z",
            "archived": True,
            "license": None,
        }
    )
    assert good.score > bad.score
    assert bad.verdict == "avoid-review-security"
