ARG BASE_IMAGE
FROM ${BASE_IMAGE}

COPY patches/kafka-python-2.3.3.patch /usr/local/share/osprey-kafka.patch
RUN git apply /usr/local/share/osprey-kafka.patch \
    && uv sync --locked --python=/usr/local/bin/python3.11
COPY kafka-auth-adapter /tmp/comail-osprey-kafka-auth
RUN uv pip install --offline --no-deps --no-build-isolation \
      --python=/osprey/.venv/bin/python /tmp/comail-osprey-kafka-auth \
    && PYTHONPATH=/tmp/comail-osprey-kafka-auth/src \
      /osprey/.venv/bin/python -m unittest discover \
      -s /tmp/comail-osprey-kafka-auth/tests -v \
    && rm -rf /tmp/comail-osprey-kafka-auth
RUN apt-get purge -y git openssh-client gcc g++ cpp 'cpp-*' \
      binutils 'binutils-*-linux-gnu'
ENV UV_OFFLINE=true
