"""Command line interface for Agent Asset Forge."""
from __future__ import annotations

from dataclasses import fields
import argparse
import json
import os
from pathlib import Path
import sys

from .core import (
    AssetSpec, ComfyUIClient, DEFAULT_WORKFLOW, catalog,
    generate, import_asset, pack, write_json,
)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", default=os.getenv("ASSETFORGE_LIBRARY", "assets"))
    parser.add_argument("--workflow", default=os.getenv("ASSETFORGE_WORKFLOW", str(DEFAULT_WORKFLOW)))
    parser.add_argument("--url", default=os.getenv("ASSETFORGE_COMFY_URL", "http://127.0.0.1:8188"))
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true", help="Print workflow without generating an image")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="assetforge",
        description="Generate image assets using ComfyUI and track licensing")
    p.add_argument("--version", action="version", version="assetforge 0.1.0")
    sub = p.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate an image through ComfyUI")
    gen.add_argument("prompt")
    gen.add_argument("--name", required=True)
    gen.add_argument("--checkpoint", required=True)
    gen.add_argument("--kind", default="image")
    gen.add_argument("--style", default="")
    gen.add_argument("--negative-prompt", default="blurry, low quality, artifacts, watermark, text")
    gen.add_argument("--width", type=int, default=768)
    gen.add_argument("--height", type=int, default=768)
    gen.add_argument("--steps", type=int, default=25)
    gen.add_argument("--cfg", type=float, default=7)
    gen.add_argument("--seed", type=int)
    _common(gen)

    batch = sub.add_parser("batch", help="Generate images from a JSON manifest")
    batch.add_argument("manifest")
    batch.add_argument("--checkpoint", help="Checkpoint default for entries without a checkpoint")
    _common(batch)

    imp = sub.add_parser("import", help="Import an existing locally licensed asset")
    imp.add_argument("file")
    imp.add_argument("--name", required=True)
    imp.add_argument("--license", required=True, dest="license_id")
    imp.add_argument("--source-url", required=True)
    imp.add_argument("--attribution", default="")
    imp.add_argument("--output", default=os.getenv("ASSETFORGE_LIBRARY", "assets"))

    doctor = sub.add_parser("doctor", help="Check the ComfyUI server and installed checkpoints")
    doctor.add_argument("--url", default=os.getenv("ASSETFORGE_COMFY_URL", "http://127.0.0.1:8188"))

    init = sub.add_parser("init", help="Create an example batch manifest")
    init.add_argument("--path", default="assetforge-manifest.json")

    cat = sub.add_parser("catalog", help="Show catalog of imported and generated assets")
    cat.add_argument("--output", default=os.getenv("ASSETFORGE_LIBRARY", "assets"))

    packaging = sub.add_parser("pack", help="Export catalogued assets in a ZIP")
    packaging.add_argument("--output", default=os.getenv("ASSETFORGE_LIBRARY", "assets"))
    packaging.add_argument("--destination", default="assetforge-assets.zip")
    return p


def specs_from_manifest(path: str | Path, checkpoint: str | None = None) -> list[AssetSpec]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("assets"), list):
        raise ValueError('Manifest must contain an "assets" list')
    if not payload["assets"]:
        raise ValueError("Manifest assets list is empty")
    valid = {field.name for field in fields(AssetSpec)}
    specs: list[AssetSpec] = []
    for index, raw in enumerate(payload["assets"]):
        if not isinstance(raw, dict):
            raise ValueError(f"Asset at index {index} must be an object")
        extra = raw.keys() - valid
        if extra:
            raise ValueError(f"Unknown asset fields at index {index}: {sorted(extra)}")
        values = raw.copy()
        if checkpoint and not values.get("checkpoint"):
            values["checkpoint"] = checkpoint
        specs.append(AssetSpec(**values))
    return specs


def _json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "generate":
            spec = AssetSpec(
                name=args.name, prompt=args.prompt, checkpoint=args.checkpoint,
                kind=args.kind, style=args.style, negative_prompt=args.negative_prompt,
                width=args.width, height=args.height, steps=args.steps,
                cfg=args.cfg, seed=args.seed,
            )
            _json(generate(spec, args.output, args.workflow, args.url,
                           args.timeout, dry_run=args.dry_run))
        elif args.command == "batch":
            results = []
            for spec in specs_from_manifest(args.manifest, args.checkpoint):
                result = generate(spec, args.output, args.workflow, args.url,
                                  args.timeout, dry_run=args.dry_run)
                results.append({"name": spec.name, "result": result})
            _json({"results": results})
        elif args.command == "import":
            result = import_asset(
                args.file, args.output, name=args.name,
                license_id=args.license_id, source_url=args.source_url,
                attribution=args.attribution,
            )
            _json({"file": str(result)})
        elif args.command == "doctor":
            result = ComfyUIClient(args.url).request("/object_info/CheckpointLoaderSimple")
            names = (result.get("CheckpointLoaderSimple", {})
                     .get("input", {}).get("required", {}).get("ckpt_name", [[]])[0])
            _json({"reachable": True, "url": args.url, "checkpoints": names})
        elif args.command == "init":
            target = Path(args.path)
            if target.exists():
                raise FileExistsError(f"Refusing to overwrite {target}")
            write_json(target, {"assets": [
                {"name": "moonlit-forest", "prompt": "Moonlit cinematic fantasy forest",
                 "checkpoint": "YOUR_INSTALLED_CHECKPOINT.safetensors"},
                {"name": "ancient-sword", "prompt": "Ancient fantasy sword concept art",
                 "checkpoint": "YOUR_INSTALLED_CHECKPOINT.safetensors"},
            ]})
            _json({"created": str(target)})
        elif args.command == "catalog":
            _json({"assets": catalog(args.output)})
        elif args.command == "pack":
            _json({"archive": str(pack(args.output, args.destination))})
    except (ValueError, FileNotFoundError, FileExistsError, KeyError, RuntimeError,
            ConnectionError, TimeoutError, OSError, TypeError) as exc:
        print(f"assetforge: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
