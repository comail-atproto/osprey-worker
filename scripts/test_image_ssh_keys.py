import io
import subprocess
import tarfile
import unittest
from pathlib import Path


class ImageSSHKeysTests(unittest.TestCase):
    def scan(self, *member_names):
        outer = io.BytesIO()
        with tarfile.open(fileobj=outer, mode="w") as image:
            for index, member_name in enumerate(member_names):
                layer = io.BytesIO()
                with tarfile.open(fileobj=layer, mode="w:gz") as archive:
                    item = tarfile.TarInfo(member_name)
                    item.size = 1
                    archive.addfile(item, io.BytesIO(b"x"))
                data = layer.getvalue()
                item = tarfile.TarInfo(f"blobs/sha256/layer{index}")
                item.size = len(data)
                image.addfile(item, io.BytesIO(data))
        return subprocess.run(
            ["python3", str(Path(__file__).with_name("check-image-ssh-keys.py"))],
            input=outer.getvalue(), capture_output=True,
        )

    def test_safe_layer_passes(self):
        self.assertEqual(self.scan("etc/ssh/ssh_config").returncode, 0)

    def test_host_private_key_in_any_layer_fails(self):
        self.assertNotEqual(self.scan("etc/ssh/ssh_config", "./etc/ssh/ssh_host_ed25519_key").returncode, 0)

    def test_public_host_key_is_not_private(self):
        self.assertEqual(self.scan("etc/ssh/ssh_host_ed25519_key.pub").returncode, 0)

    def test_invalid_archive_fails(self):
        result = subprocess.run(
            ["python3", str(Path(__file__).with_name("check-image-ssh-keys.py"))],
            input=b"not an image", capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
