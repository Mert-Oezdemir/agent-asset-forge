"""Optional MCP tools for coding agents; requires pip install -e '.[mcp]'."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .core import AssetSpec, DEFAULT_WORKFLOW, catalog, generate, import_asset


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit("Install MCP support: python -m pip install -e '.[mcp]'") from exc

    server = FastMCP("Agent Asset Forge")

    def library() -> str:
        return os.environ.get("ASSETFORGE_LIBRARY", str(Path.cwd() / "assets"))

    def workflow() -> str:
        return os.environ.get("ASSETFORGE_WORKFLOW", str(DEFAULT_WORKFLOW))

    def comfy_url() -> str:
        return os.environ.get("ASSETFORGE_COMFY_URL", "http://127.0.0.1:8188")

    @server.tool()
    def generate_image(
        name: str, prompt: str, checkpoint: str, kind: str = "image",
        style: str = "", negative_prompt: str = "blurry, low quality, artifacts, watermark, text",
        width: int = 768, height: int = 768, steps: int = 25,
        cfg: float = 7.0, seed: int | None = None,
    ) -> str:
        """Generate a 2D image using the local ComfyUI API and installed checkpoint.

        Requires a classic KSampler API workflow. Saves image and metadata
        sidecar to the configured local asset library.
        """
        spec = AssetSpec(name=name, prompt=prompt, checkpoint=checkpoint,
                         kind=kind, style=style, negative_prompt=negative_prompt,
                         width=width, height=height, steps=steps, cfg=cfg, seed=seed)
        files = generate(spec, library(), workflow(), comfy_url())
        return json.dumps({"files": [str(x) for x in files]})

    @server.tool()
    def list_assets() -> str:
        """Return recorded local asset filenames, licenses and provenance."""
        return json.dumps({"assets": catalog(library())}, ensure_ascii=False)

    @server.tool()
    def import_local_asset(
        local_file: str, name: str, license_id: str,
        source_url: str, attribution: str = "",
    ) -> str:
        """Copy an existing authorized local asset and record license/provenance.

        Caller must verify usage and redistribution rights before importing.
        """
        file = import_asset(local_file, library(), name=name, license_id=license_id,
                            source_url=source_url, attribution=attribution)
        return json.dumps({"file": str(file)})

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
