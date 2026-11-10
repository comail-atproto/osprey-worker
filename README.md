# Osprey worker image

Container images for the [Osprey rule-evaluation worker](https://github.com/roostorg/osprey),
with dependencies installed at build time so startup works without package downloads.
The supported platform is `linux/amd64`.

## Use the image

Images are published to `ghcr.io/comail-atproto/osprey-worker` with a
`build-<commit>` tag. Choose a version from the
[package page](https://github.com/orgs/comail-atproto/packages/container/package/osprey-worker)
and pin its `sha256` digest in your deployment configuration.

The image contains the worker and its dependencies. Supply your own rules,
configuration and services using the [upstream documentation](https://github.com/roostorg/osprey#readme).
Check those integrations before upgrading; the image smoke test covers startup only.

## Kafka authentication

The image installs a separate Comail pluggy adapter. It uses Osprey's input
and output hooks and leaves the pinned upstream package files unchanged.

For SASL/PLAIN input, set `OSPREY_INPUT_STREAM_SOURCE=plugin` and provide both
`COMAIL_KAFKA_USERNAME` and `COMAIL_KAFKA_PASSWORD_FILE`. The password file
must be mounted in the worker container and contain one non-empty UTF-8 line.
The adapter reads the file at startup and removes one trailing LF or CRLF.
A partial or invalid pair stops startup. If both variables are absent,
the adapter lets the existing upstream input plugin handle the stream.
SASL/PLAIN does not encrypt credentials; use it over an encrypted network.

For authenticated output, set both credential variables, set
`COMAIL_KAFKA_OUTPUT_SINK=true`, and set `OSPREY_KAFKA_OUTPUT_SINK=false`.
This avoids starting a second, unauthenticated producer. The adapter uses the
existing OSPREY topic, broker and client ID settings. When
`COMAIL_KAFKA_OUTPUT_SINK` is unset, upstream continues to control output sinks.

## Build locally

Install Docker Engine with Buildx, then run:

```sh
git clone --recurse-submodules https://github.com/comail-atproto/osprey-worker.git
cd osprey-worker
export BUILD_REVISION="$(git rev-parse HEAD)"
export UPSTREAM_REVISION="$(git -C upstream rev-parse HEAD)"
export IMAGE=osprey-worker:local
export UPSTREAM_DOCKERFILE="$(cat upstream/osprey_worker/Dockerfile)"
docker buildx bake --load worker
bash scripts/smoke-test.sh "$IMAGE"
```

The test checks the image's architecture and source revisions, then starts the
worker CLI with networking disabled to catch missing startup dependencies.

## How it is built

- `upstream/` pins the original application source as a Git submodule.
- `Dockerfile.python` pins the Python base image by digest.
- `docker-bake.hcl` builds the pinned upstream recipe with the SSH client in place of the server package. It rejects unexpected changes to that install line.
- `Dockerfile` prepares the workspace packages, installs the Kafka adapter, and enables offline package resolution.

Dependabot proposes weekly updates to the source, base image and GitHub Actions.
Its pull requests are approved and merged automatically after all required
checks pass. Before publishing, a fresh job restores the tested image and
repeats the offline startup check. Each release records its source revisions,
build inputs and a GitHub build attestation.

See [CONTRIBUTING.md](CONTRIBUTING.md) for checks and release setup.

## License

This packaging is under [Apache-2.0](LICENSE). The pinned
[upstream source](upstream) includes Osprey's copyright and Apache-2.0 license.
