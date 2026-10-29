# Osprey worker image

This repository packages the [upstream Osprey worker](https://github.com/roostorg/osprey)
for rule evaluation. The image is `ghcr.io/comail-atproto/osprey-worker`.
It does not include Comail deployment settings, credentials or moderation rules.

## Build source

The `upstream` Git submodule pins the application source. `Dockerfile.python`
pins its Python base image. Docker Bake supplies that base to upstream's
unchanged Dockerfile, then our small `Dockerfile` prepares the workspace
packages and sets `UV_OFFLINE=true`. Startup does not need to download Python
packages or build tools.

The supported platform is `linux/amd64`. To build and check it with Docker
Engine and Buildx:

```sh
git clone --recurse-submodules https://github.com/comail-atproto/osprey-worker.git
cd osprey-worker
export BUILD_REVISION="$(git rev-parse HEAD)"
export UPSTREAM_REVISION="$(git -C upstream rev-parse HEAD)"
export IMAGE=ghcr.io/comail-atproto/osprey-worker:local
docker buildx bake --load worker
bash scripts/smoke-test.sh "$IMAGE"
```

The smoke test checks the image's architecture and source labels, then starts
the worker CLI with networking disabled. It catches missing startup packages;
it does not test a consumer's Kafka, PostgreSQL, moderation rules or mail flows.
Those need integration acceptance before a deployment selects a new image.

## Maintenance and releases

Dependabot opens weekly update PRs for the upstream submodule, Python base and
GitHub Actions. Python major/minor upgrades need a coordinated change because
the upstream entrypoint selects Python 3.11. Scott reviews changes; updates are
not merged automatically.
CI uses public GitHub-hosted Linux runners, with no private source credentials.
Required checks are workflow/shell validation, dependency review and the image
build/startup test, each limited to 15 minutes or less.

After a reviewed change reaches `main`, CI exports the tested image. A fresh
job verifies its archive checksum, loads it and repeats the offline test before
publishing. Published images have a `build-<repository commit>` tag and an
immutable digest. The release also records upstream source, recipe and lock
hashes, builder identity, and a GitHub build attestation. Use the digest when
deploying; a new image does not change a consumer's selected version.

Before enabling publication, link the GHCR package to this repository and make
the image public. Configure the `release` environment to accept only `main`,
then set `ENABLE_OSPREY_GHCR_PUBLISHER=true`. Retire the previous publisher
after the first publication and independent pull pass. The publishing job uses
only its short-lived `GITHUB_TOKEN`; no personal access token is needed.

`scripts/publish.sh` is called by that job to record the pushed digest and
source provenance. Keep existing image digests and archives available when
updating or reverting a consumer. Reverting this repository prepares another
build; it does not restore a deployed service.

## License

This packaging is under Apache-2.0. Upstream Osprey retains its own copyright
and [Apache-2.0 license](upstream/LICENSE.md). See [LICENSE](LICENSE).
