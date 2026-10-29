ARG BASE_IMAGE
FROM ${BASE_IMAGE}

RUN uv sync --locked --python=/usr/local/bin/python3.11
ENV UV_OFFLINE=true
