"""ComfyUI image asset generation and provenance-aware asset library."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import copy
import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

DEFAULT_WORKFLOW = Path(__file__).parent / "workflows" / "sd15-api.json"
IMPORT_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".glb", ".gltf",
              ".obj", ".fbx", ".blend", ".wav", ".mp3", ".ogg"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:64] or "asset"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     suffix=".tmp", delete=False) as out:
        temporary = Path(out.name)
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write("\n")
    os.replace(temporary, path)


@dataclass(frozen=True)
class AssetSpec:
    name: str
    prompt: str
    checkpoint: str
    kind: str = "image"
    style: str = ""
    negative_prompt: str = "blurry, low quality, artifacts, watermark, text"
    width: int = 768
    height: int = 768
    steps: int = 25
    cfg: float = 7
    seed: int | None = None

    def __post_init__(self) -> None:
        if not all(v.strip() for v in (self.name, self.prompt, self.checkpoint)):
            raise ValueError("name, prompt and checkpoint are required")
        for key in ("width", "height"):
            value = getattr(self, key)
            if not (64 <= value <= 4096 and value % 8 == 0):
                raise ValueError(f"{key} must be a multiple of 8 between 64 and 4096")
        if not 1 <= self.steps <= 100 or not 0.1 <= self.cfg <= 30:
            raise ValueError("steps must be 1..100 and cfg must be 0.1..30")
        if self.seed is not None and not (0 <= self.seed < 2**53):
            raise ValueError("seed must be between 0 and 2^53-1")


def read_workflow(path: str | Path = DEFAULT_WORKFLOW) -> dict[str, Any]:
    graph = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(graph, dict) or not graph or any(
        not isinstance(node, dict) or "class_type" not in node or "inputs" not in node
        for node in graph.values()
    ):
        raise ValueError("Expected ComfyUI API-format workflow JSON")
    return graph


def _one(graph: dict, class_type: str) -> dict:
    found = [node for node in graph.values() if node["class_type"] == class_type]
    if len(found) != 1:
        raise ValueError(f"Workflow must contain exactly one {class_type} node")
    return found[0]


def apply_spec(graph: dict[str, Any], spec: AssetSpec) -> tuple[dict[str, Any], int]:
    graph = copy.deepcopy(graph)
    loader = _one(graph, "CheckpointLoaderSimple")
    latent = _one(graph, "EmptyLatentImage")
    sampler = _one(graph, "KSampler")
    saver = _one(graph, "SaveImage")
    links = sampler["inputs"]
    try:
        positive = graph[str(links["positive"][0])]
        negative = graph[str(links["negative"][0])]
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError("KSampler needs direct positive and negative CLIP links") from exc
    if positive is negative or positive["class_type"] != "CLIPTextEncode" or negative["class_type"] != "CLIPTextEncode":
        raise ValueError("Expected separate positive and negative CLIPTextEncode nodes")
    seed = spec.seed if spec.seed is not None else uuid.uuid4().int % 2**53
    loader["inputs"]["ckpt_name"] = spec.checkpoint
    positive["inputs"]["text"] = ", ".join(filter(None, (spec.prompt, spec.style)))
    negative["inputs"]["text"] = spec.negative_prompt
    latent["inputs"].update(width=spec.width, height=spec.height, batch_size=1)
    links.update(seed=seed, steps=spec.steps, cfg=spec.cfg)
    saver["inputs"]["filename_prefix"] = f"AssetForge_{slugify(spec.name)}"
    return graph, seed


class ComfyUIClient:
    def __init__(self, url: str = "http://127.0.0.1:8188", timeout: int = 30):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("ComfyUI URL must be an HTTP(S) URL without credentials")
        self.url = url.rstrip("/")
        self.timeout = timeout

    def request(self, path: str, payload: dict | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url + path, data=data,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST" if payload is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", errors="replace")
            raise RuntimeError(f"ComfyUI HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Could not reach ComfyUI: {exc.reason}") from exc

    def queue(self, graph: dict) -> str:
        result = self.request("/prompt", {"prompt": graph, "client_id": str(uuid.uuid4())})
        if not isinstance(result, dict) or not result.get("prompt_id"):
            raise RuntimeError(f"ComfyUI rejected workflow: {result}")
        return str(result["prompt_id"])

    def wait(self, prompt_id: str, timeout: int = 300) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            record = self.request("/history/" + urllib.parse.quote(prompt_id, safe=""))
            record = record.get(prompt_id) if isinstance(record, dict) else None
            if record:
                status = record.get("status", {})
                if status.get("status_str") == "error" or status.get("completed") is False:
                    raise RuntimeError(f"ComfyUI generation failed: {status}")
                if not record.get("outputs"):
                    raise RuntimeError("ComfyUI finished without output images")
                return record
            time.sleep(1)
        raise TimeoutError(f"ComfyUI job did not finish within {timeout} seconds")

    def image_bytes(self, image: dict) -> bytes:
        if image.get("type") != "output":
            raise ValueError("Only ComfyUI output images are accepted")
        name = str(image.get("filename", ""))
        if not name or Path(name).name != name:
            raise ValueError("Unsafe or missing image filename")
        query = urllib.parse.urlencode({"filename": name,
            "subfolder": str(image.get("subfolder", "")), "type": "output"})
        req = urllib.request.Request(self.url + "/view?" + query)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = response.read(40 * 1024 * 1024 + 1)
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Failed to download output: {exc}") from exc
        if not data or len(data) > 40 * 1024 * 1024:
            raise ValueError("Image was empty or exceeded 40 MiB")
        return data


def generate(spec: AssetSpec, output: str | Path = "assets",
             workflow: str | Path = DEFAULT_WORKFLOW,
             url: str = "http://127.0.0.1:8188", timeout: int = 300,
             *, client: ComfyUIClient | None = None, dry_run: bool = False) -> list[Path] | dict:
    graph, seed = apply_spec(read_workflow(workflow), spec)
    if dry_run:
        return {"seed": seed, "workflow": graph}
    client = client or ComfyUIClient(url)
    prompt_id = client.queue(graph)
    job = client.wait(prompt_id, timeout)
    images = [image for node in job.get("outputs", {}).values()
              for image in node.get("images", []) if image.get("type") == "output"]
    if not images:
        raise RuntimeError("No output images in ComfyUI history")
    root = Path(output).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for index, image in enumerate(images, 1):
        extension = Path(str(image.get("filename", ""))).suffix.lower()
        if extension not in IMAGE_EXT:
            raise ValueError(f"Unsupported image extension: {extension}")
        name = f"{slugify(spec.name)}-{seed}-{index}-{uuid.uuid4().hex[:6]}{extension}"
        target = root / name
        data = client.image_bytes(image)
        with tempfile.NamedTemporaryFile(dir=root, delete=False) as file:
            temporary = Path(file.name)
            file.write(data)
        os.replace(temporary, target)
        write_json(root / (name + ".json"), {
            "filename": name, "name": spec.name, "kind": spec.kind,
            "source": "generated", "backend": "ComfyUI",
            "prompt_id": prompt_id, "seed": seed, "created_at": _now(),
            "license": "unverified",
            "license_note": "Review checkpoint/model output terms before redistribution.",
            "parameters": {**asdict(spec), "seed": seed}
        })
        results.append(target)
    return results


def import_asset(path: str | Path, output: str | Path, *,
                 name: str, license_id: str, source_url: str,
                 attribution: str = "") -> Path:
    source = Path(path).expanduser().resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in IMPORT_EXT:
        raise ValueError("Unsupported asset extension or not a file")
    if not all(x.strip() for x in (name, license_id, source_url)):
        raise ValueError("Asset name, license and source URL are required")
    root = Path(output).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    dest = root / f"{slugify(name)}-{uuid.uuid4().hex[:8]}{source.suffix.lower()}"
    shutil.copyfile(source, dest)
    write_json(root / (dest.name + ".json"), {
        "filename": dest.name, "name": name, "source": "imported",
        "source_url": source_url, "license": license_id,
        "attribution": attribution, "created_at": _now()
    })
    return dest


def catalog(folder: str | Path = "assets") -> list[dict]:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        return []
    entries = []
    for sidecar in sorted(root.glob("*.json")):
        try:
            item = json.loads(sidecar.read_text(encoding="utf-8"))
            if isinstance(item, dict) and item.get("filename") and (root / Path(item["filename"]).name).is_file():
                entries.append(item)
        except (OSError, json.JSONDecodeError):
            pass
    return entries


def pack(folder: str | Path = "assets", destination: str | Path = "assets.zip") -> Path:
    root = Path(folder).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Asset path must be a folder")
    target = Path(destination).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    items = catalog(root)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in items:
            filename = Path(item["filename"]).name
            archive.write(root / filename, arcname=f"assets/{filename}")
            archive.write(root / (filename + ".json"), arcname=f"assets/{filename}.json")
        archive.writestr("manifest.json", json.dumps({"assets": items}, ensure_ascii=False, indent=2))
    return target
