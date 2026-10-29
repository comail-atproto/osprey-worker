# Contributing

Open a pull request for changes to the build or its pinned dependencies.
Application changes belong in [upstream Osprey](https://github.com/roostorg/osprey).

## Checks

Run the build and smoke test in [README.md](README.md), plus:

```sh
shellcheck scripts/*.sh
actionlint .github/workflows/*.yml
bash scripts/test-publish.sh
bash scripts/test-auto-merge-dependabot.sh
git diff --check
```

Pull requests run these checks, dependency review and a native `linux/amd64`
image build with the offline startup test. The test does not exercise rules,
Kafka or PostgreSQL; deployments need their own integration tests.

Dependabot opens weekly pull requests for the upstream submodule, Python base
and GitHub Actions. Python stays on 3.11 because upstream's entrypoint selects
that version; major or minor upgrades need a matching entrypoint change.
Dependabot pull requests merge automatically after the required checks pass.
Other pull requests still require maintainer approval.

## Releases

Publication runs from reviewed commits on `main`. Maintainers must link the
GHCR package to this repository, grant its Actions workflows package write
access, make the package public, and configure the `release` environment to
accept only `main`. Set the repository variable
`ENABLE_OSPREY_GHCR_PUBLISHER=true` to enable publishing.

CI exports the tested image with a checksum. A fresh job restores it and
repeats the smoke test before pushing the `build-<commit>` tag and attesting
its digest. The workflow calls `scripts/publish.sh` to record the source and
build-input hashes in its `worker-provenance-<commit>` artifact.

After publication, attestation and provenance upload succeed, CI deletes only
that run's temporary image archive. Failed publications retain it for one day;
provenance remains available for 90 days and published images remain in GHCR.
Rerun all jobs to rebuild the handoff when repeating a successful publication.

Publishing uses the workflow's `GITHUB_TOKEN`. Disabling the repository variable
stops future publications. Existing images remain available; consumers can
select an earlier digest to undo an upgrade.
