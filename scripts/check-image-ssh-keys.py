#!/usr/bin/env python3
"""Reject SSH host private keys in any layer of a docker-save archive."""
import io
import posixpath
import re
import sys
import tarfile


def main():
    layers = 0
    with tarfile.open(fileobj=sys.stdin.buffer, mode="r|*") as image:
        for member in image:
            if not member.isfile() or not (
                member.name.startswith("blobs/sha256/") or member.name.endswith("/layer.tar")
            ):
                continue
            stream = image.extractfile(member)
            if stream is None:
                raise ValueError("cannot read image member")
            stream = io.BufferedReader(stream)
            prefix = stream.peek(512)
            is_layer = prefix.startswith(b"\x1f\x8b") or prefix[257:262] == b"ustar"
            if not is_layer:
                if prefix.lstrip().startswith((b"{", b"[")):
                    continue
                raise ValueError("unknown image blob format")
            layers += 1
            with tarfile.open(fileobj=stream, mode="r|*") as layer:
                for entry in layer:
                    name = posixpath.normpath("/" + entry.name).lstrip("/")
                    if re.fullmatch(r"etc/ssh/ssh_host_[^/]*_key", name):
                        raise ValueError("image layer contains an SSH host private key")
    if not layers:
        raise ValueError("image contains no readable layers")


if __name__ == "__main__":
    main()
