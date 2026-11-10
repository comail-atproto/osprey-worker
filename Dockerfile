ARG BASE_IMAGE
FROM ${BASE_IMAGE}

RUN uv sync --locked --python=/usr/local/bin/python3.11
COPY kafka-auth-adapter /tmp/comail-osprey-kafka-auth
RUN uv pip install --offline --no-deps --no-build-isolation \
      --python=/osprey/.venv/bin/python /tmp/comail-osprey-kafka-auth \
    && PYTHONPATH=/tmp/comail-osprey-kafka-auth/src \
      /osprey/.venv/bin/python -m unittest discover \
      -s /tmp/comail-osprey-kafka-auth/tests -v \
    && rm -rf /tmp/comail-osprey-kafka-auth
ENV UV_OFFLINE=true
