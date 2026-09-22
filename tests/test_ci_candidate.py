import base64
import hashlib
import importlib.util
import io
import json
import pathlib
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "candidate", pathlib.Path(__file__).parents[1] / "scripts/ci_candidate.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class CandidateTests(unittest.TestCase):
    def candidate(self, directory, member="payload"):
        root = pathlib.Path(directory) / "pack"
        (root / "linux_20").mkdir(parents=True)
        archive = root / "linux_20/a.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            payload = b"candidate"
            entry = tarfile.TarInfo(member)
            entry.size = len(payload)
            tar.addfile(entry, io.BytesIO(payload))
        manifest = {
            "runEnvironments": [{"name": "linux_20"}],
            "distribution": {"urlStrategy": "local-relative", "packages": [{
                "environment": "linux_20", "url": "linux_20/a.tar.gz",
                "integrity": "sha512-" + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode(),
                "size": archive.stat().st_size,
            }]},
        }
        (root / "package.ktm.json").write_text(json.dumps(manifest))
        return root

    def seal(self, root):
        receipt = root.parent / "seal"
        receipt.write_text(json.dumps(c.inventory(root)))
        return receipt

    def test_stage_and_mutation_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.candidate(directory)
            receipt = self.seal(root)
            output = root.parent / "out"
            c.stage(root, receipt, "linux_20", output)
            self.assertEqual((output / "payload").read_bytes(), b"candidate")
            (root / "extra").write_text("unexpected")
            with self.assertRaises(ValueError):
                c.verify(root, receipt)

    def test_reject_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.candidate(directory, "../escape")
            receipt = self.seal(root)
            with self.assertRaises(ValueError):
                c.stage(root, receipt, "linux_20", root.parent / "out")
            self.assertFalse((root.parent / "escape").exists())

    def test_reject_incorrect_manifest_checksum_before_sealing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.candidate(directory)
            with (root / "linux_20/a.tar.gz").open("ab") as stream:
                stream.write(b"tampered")
            with self.assertRaises(ValueError):
                c.inventory(root)

    def test_reject_external_or_traversing_manifest_path(self):
        for url in ["../escape.tar.gz", "https://example.invalid/a.tar.gz"]:
            with self.subTest(url=url), tempfile.TemporaryDirectory() as directory:
                root = self.candidate(directory)
                path = root / "package.ktm.json"
                manifest = json.loads(path.read_text())
                manifest["distribution"]["packages"][0]["url"] = url
                path.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    c.inventory(root)


if __name__ == "__main__":
    unittest.main()
