#!/usr/bin/env python3

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Iterable


BEHAVIOR_WORKFLOW_NAMES = {
    "Behavior Benchmark Smoke",
    "Behavior Benchmark Full",
    "Behavior Benchmark Subagents Smoke",
}

ACTIVE_STATUSES = {"queued", "in_progress", "waiting", "pending", "requested"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-run-id", type=int, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--max-active", type=int, default=2)
    parser.add_argument("--poll-seconds", type=int, default=15)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    return parser.parse_args()


def build_request(url: str, token: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "claude-crew-benchmark-slot-gate",
        },
    )


def fetch_active_behavior_runs(*, api_url: str, repo: str, token: str, head_sha: str) -> list[dict]:
    url = f"{api_url}/repos/{repo}/actions/runs?per_page=100"
    request = build_request(url, token)
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)

    runs = payload.get("workflow_runs", [])
    selected: list[dict] = []
    for run in runs:
        if run.get("name") not in BEHAVIOR_WORKFLOW_NAMES:
            continue
        if run.get("head_sha") != head_sha:
            continue
        if run.get("status") not in ACTIVE_STATUSES:
            continue
        selected.append(run)
    return selected


def order_active_runs(runs: Iterable[dict]) -> list[dict]:
    return sorted(
        runs,
        key=lambda run: (
            run.get("created_at", ""),
            int(run.get("id", 0)),
        ),
    )


def current_run_has_slot(*, current_run_id: int, runs: Iterable[dict], max_active: int) -> tuple[bool, list[int]]:
    ordered = order_active_runs(runs)
    allowed_run_ids = [int(run["id"]) for run in ordered[:max_active]]
    return current_run_id in allowed_run_ids, allowed_run_ids


def main() -> int:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not args.repo:
        print("GITHUB_REPOSITORY or --repo is required", file=sys.stderr)
        return 2
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2

    deadline = time.monotonic() + args.timeout_seconds
    while True:
        try:
            active_runs = fetch_active_behavior_runs(
                api_url=args.api_url,
                repo=args.repo,
                token=token,
                head_sha=args.head_sha,
            )
        except urllib.error.HTTPError as exc:
            print(f"GitHub API request failed with HTTP {exc.code}", file=sys.stderr)
            return 1
        except urllib.error.URLError as exc:
            print(f"GitHub API request failed: {exc}", file=sys.stderr)
            return 1

        has_slot, allowed_ids = current_run_has_slot(
            current_run_id=args.current_run_id,
            runs=active_runs,
            max_active=args.max_active,
        )
        active_ids = [int(run["id"]) for run in order_active_runs(active_runs)]
        print(
            f"Active benchmark workflow runs for {args.head_sha[:12]}: {active_ids}. "
            f"Allowed now: {allowed_ids}."
        )
        if has_slot:
            print(f"Run {args.current_run_id} has a benchmark slot.")
            return 0
        if time.monotonic() >= deadline:
            print(
                f"Timed out waiting for benchmark slot after {args.timeout_seconds}s. "
                f"Current run {args.current_run_id} never entered the first {args.max_active}.",
                file=sys.stderr,
            )
            return 1
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
