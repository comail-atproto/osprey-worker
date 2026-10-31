variable "UPSTREAM_DOCKERFILE" {
  default = ""
  validation {
    condition = length(split("wget ssh &&", UPSTREAM_DOCKERFILE)) == 2
    error_message = "Expected exactly one upstream SSH package installation."
  }
}

variable "IMAGE" {
  default = "osprey-worker:local"
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
  dockerfile-inline = replace(UPSTREAM_DOCKERFILE, "wget ssh &&", "wget openssh-client &&")
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
    "upstream.revision" = UPSTREAM_REVISION
  }
}
