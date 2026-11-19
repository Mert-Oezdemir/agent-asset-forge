"""Offline unit tests. No ComfyUI server or GPU is required."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from assetforge.core import (
    AssetSpec, ComfyUIClient, apply_spec, catalog, generate,
    import_asset, pack, read_workflow, slugify,
)
from assetforge.cli import specs_from_manifest


class FakeClient:
    def queue(self, workflow):
        self.graph = workflow
        return "prompt-test"

    def wait(self, prompt_id, timeout=300):
        assert prompt_id == "prompt-test"
        return {"outputs": {"9": {"images": [
            {"filename": "output.png", "subfolder": "", "type": "output"}
        ]}}}

    def image_bytes(self, meta):
        return b"mocked-image"


class PipelineTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Fantasy Sword!!!"), "fantasy-sword")
        self.assertEqual(slugify("💫"), "asset")

    def test_validation(self):
        with self.assertRaises(ValueError):
            AssetSpec(name="x", prompt="test", checkpoint="model", width=93)
        with self.assertRaises(ValueError):
            AssetSpec(name="x", prompt="test", checkpoint="")

    def test_workflow_patch(self):
        graph = read_workflow()
        spec = AssetSpec(name="Sword", prompt="shiny sword", checkpoint="custom.ckpt",
                         style="4k", width=512, height=640, seed=42)
        output, seed = apply_spec(graph, spec)
        self.assertEqual(seed, 42)
        self.assertEqual(output["6"]["inputs"]["text"], "shiny sword, 4k")
        self.assertEqual(output["4"]["inputs"]["ckpt_name"], "custom.ckpt")
        self.assertEqual(output["5"]["inputs"]["height"], 640)
        self.assertNotEqual(graph["4"]["inputs"]["ckpt_name"], "custom.ckpt")

    def test_incompatible_workflow(self):
        graph = read_workflow()
        graph.pop("9")
        with self.assertRaisesRegex(ValueError, "SaveImage"):
            apply_spec(graph, AssetSpec(name="x", prompt="x", checkpoint="x"))

    def test_dry_run(self):
        result = generate(AssetSpec(name="x", prompt="x", checkpoint="x", seed=0),
                          dry_run=True)
        self.assertEqual(result["seed"], 0)
        self.assertIn("9", result["workflow"])

    def test_mocked_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            files = generate(AssetSpec(name="Forest", prompt="forest",
                             checkpoint="model.ckpt", seed=7),
                             output=directory, client=FakeClient())
            self.assertEqual(files[0].read_bytes(), b"mocked-image")
            records = catalog(directory)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["seed"], 7)
            self.assertEqual(records[0]["license"], "unverified")

    def test_import_and_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.png"
            source.write_bytes(b"sample")
            library = root / "assets"
            target = import_asset(source, library, name="Sword", license_id="CC0-1.0",
                                  source_url="https://example.org/sword")
            (library / ".env").write_text("SECRET_KEY=nope")
            archive = pack(library, root / "out.zip")
            with zipfile.ZipFile(archive) as z:
                self.assertIn("assets/" + target.name, z.namelist())
                self.assertNotIn("assets/.env", z.namelist())
                manifest = json.loads(z.read("manifest.json"))
                self.assertEqual(manifest["assets"][0]["license"], "CC0-1.0")

    def test_require_import_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "x.png"
            source.write_bytes(b"a")
            with self.assertRaises(ValueError):
                import_asset(source, directory, name="X", license_id="", source_url="url")

    def test_manifest_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{"name": "S", "prompt": "sword"}]}))
            self.assertEqual(specs_from_manifest(manifest, "checkpoint.ckpt")[0].checkpoint, "checkpoint.ckpt")
            manifest.write_text(json.dumps({"assets": [{"name": "x", "prompt": "x", "bad": 1}]}))
            with self.assertRaisesRegex(ValueError, "Unknown"):
                specs_from_manifest(manifest, "checkpoint.ckpt")

    def test_reject_file_urls(self):
        with self.assertRaises(ValueError):
            ComfyUIClient("file:///etc/passwd")
        with self.assertRaises(ValueError):
            ComfyUIClient("http://name:secret@localhost:8188")


if __name__ == "__main__":
    unittest.main()
