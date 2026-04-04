#!/usr/bin/env python3

import argparse
import io
import json
import os
import pathlib
import urllib.error
import urllib.request
import zipfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def github_request(url: str, token: str) -> urllib.request.addinfourl:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    return urllib.request.urlopen(request)


def github_get_json(url: str, token: str) -> dict:
    with github_request(url, token) as response:
        return json.loads(response.read().decode("utf-8"))


def github_get_bytes(url: str, token: str) -> bytes:
    with github_request(url, token) as response:
        return response.read()


def find_artifact(artifacts: list[dict], artifact_name: str) -> dict:
    for artifact in artifacts:
        if artifact.get("name") == artifact_name and not artifact.get("expired", False):
            return artifact
    raise RuntimeError(f"Artifact not found or expired: {artifact_name}")


def extract_summary_bytes(artifact_zip: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(artifact_zip)) as archive:
        for name in archive.namelist():
            normalized = pathlib.PurePosixPath(name)
            if normalized.name == "summary.json":
                return archive.read(name)
    raise RuntimeError("summary.json was not found inside the downloaded artifact")


def download_summary(repo: str, run_id: int, artifact_name: str, token: str) -> bytes:
    artifacts_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts"
    payload = github_get_json(artifacts_url, token)
    artifact = find_artifact(payload.get("artifacts", []), artifact_name)
    zip_url = f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact['id']}/zip"
    return extract_summary_bytes(github_get_bytes(zip_url, token))


def main() -> None:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")

    try:
        summary_bytes = download_summary(args.repo, args.run_id, args.artifact_name, token)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API request failed: {exc}") from exc

    output_path = pathlib.Path(args.output)
    output_path.write_bytes(summary_bytes)


if __name__ == "__main__":
    main()
