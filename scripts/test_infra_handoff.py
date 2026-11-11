import copy
import unittest

from scripts.check_infra_handoff import valid_handoff


class InfraHandoffTest(unittest.TestCase):
    def test_only_successful_exact_main_push_or_dispatch_with_all_jobs_can_request_proof(
        self,
    ):
        sha = "a" * 40
        repo = "comail-atproto/osprey-worker"
        run = {
            "id": 42,
            "head_sha": sha,
            "head_branch": "main",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "path": ".github/workflows/image.yml",
            "repository": {"full_name": repo},
            "head_repository": {"full_name": repo},
        }
        jobs = [
            {
                "name": name,
                "run_id": 42,
                "head_sha": sha,
                "status": "completed",
                "conclusion": "success",
            }
            for name in ("validate", "build-and-test", "publish-eligibility", "publish")
        ]
        self.assertTrue(valid_handoff(run, jobs, sha))
        self.assertTrue(valid_handoff({**run, "event": "workflow_dispatch"}, jobs, sha))
        for change in (
            {"event": "pull_request"},
            {"head_branch": "feature"},
            {"conclusion": "failure"},
            {"head_repository": {"full_name": "fork/worker"}},
            {"head_sha": "b" * 40},
        ):
            with self.subTest(change=change):
                self.assertFalse(valid_handoff({**run, **change}, jobs, sha))
        for index in range(len(jobs)):
            changed = copy.deepcopy(jobs)
            changed[index]["conclusion"] = "skipped"
            self.assertFalse(valid_handoff(run, changed, sha))
        for change in (
            {"head_sha": "c" * 40},
            {"run_id": 43},
            {"status": "in_progress"},
        ):
            changed = copy.deepcopy(jobs)
            changed[1].update(change)
            self.assertFalse(valid_handoff(run, changed, sha))
        self.assertFalse(valid_handoff(run, jobs + [jobs[-1]], sha))
        self.assertFalse(valid_handoff(run, jobs[:-1], sha))


if __name__ == "__main__":
    unittest.main()
