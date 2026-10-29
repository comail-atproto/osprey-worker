variable "IMAGE" {
  default = "ghcr.io/comail-atproto/osprey-worker:local"
}

variable "BUILD_REVISION" {
  default = "local"
}

variable "UPSTREAM_REVISION" {
  default = "local"
}

group "default" {
  targets = ["worker"]
}

target "python" {
  dockerfile = "Dockerfile.python"
  platforms = ["linux/amd64"]
}

target "upstream" {
  context = "upstream"
  dockerfile = "osprey_worker/Dockerfile"
  contexts = {
    "python:3.11-slim" = "target:python"
  }
  platforms = ["linux/amd64"]
}

target "worker" {
  dockerfile = "Dockerfile"
  args = {
    BASE_IMAGE = "upstream"
  }
  contexts = {
    upstream = "target:upstream"
  }
  platforms = ["linux/amd64"]
  tags = [IMAGE]
  labels = {
    "org.opencontainers.image.source" = "https://github.com/comail-atproto/osprey-worker"
    "org.opencontainers.image.description" = "Osprey rule-evaluation worker with dependencies prepared for offline startup."
    "org.opencontainers.image.licenses" = "Apache-2.0"
    "org.opencontainers.image.revision" = BUILD_REVISION
    "at.comail.upstream-revision" = UPSTREAM_REVISION
  }
}
