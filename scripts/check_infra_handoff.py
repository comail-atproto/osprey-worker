"""Check the Osprey publication before requesting Infra qualification."""

import argparse
import json
import re
from pathlib import Path

REPOSITORY = "comail-atproto/osprey-worker"
JOBS = ("validate", "build-and-test", "publish-eligibility", "publish")


def valid_handoff(run, jobs, current):
    run_id, sha = run.get("id"), run.get("head_sha", "")
    if (
        type(run_id) is not int
        or run_id <= 0
        or not re.fullmatch(r"[a-f0-9]{40}", sha)
        or sha != current
        or run.get("repository", {}).get("full_name") != REPOSITORY
        or run.get("head_repository", {}).get("full_name") != REPOSITORY
        or run.get("path") != ".github/workflows/image.yml"
        or run.get("head_branch") != "main"
        or run.get("event") not in {"push", "workflow_dispatch"}
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
    ):
        return False
    for name in JOBS:
        matching = [job for job in jobs if job.get("name") == name]
        if (
            len(matching) != 1
            or matching[0].get("run_id") != run_id
            or matching[0].get("head_sha") != sha
            or matching[0].get("status") != "completed"
            or matching[0].get("conclusion") != "success"
        ):
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="GitHub Actions run JSON")
    parser.add_argument("jobs", type=Path, help="GitHub Actions jobs JSON")
    parser.add_argument("current_sha", help="current producer main revision")
    args = parser.parse_args()
    run = json.loads(args.run.read_text())
    jobs = json.loads(args.jobs.read_text())["jobs"]
    if not valid_handoff(run, jobs, args.current_sha):
        raise SystemExit("Osprey publication did not pass the trusted main handoff")


if __name__ == "__main__":
    main()
