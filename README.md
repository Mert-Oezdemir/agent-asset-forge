# Agent Asset Forge

**Local-first AI image asset generation for coding agents.** Use a running ComfyUI installation to create 2D game/web assets, save them with metadata, import licensed assets, package a reusable library and expose tools to AI agents through MCP.

[Turkce kurulum rehberi](docs/README.tr.md)

> v0.1.0 starter kit. Ten offline tests passed on a checked-out copy from GitHub. Real image generation requires a local ComfyUI server and a compatible installed checkpoint; live image generation has not been tested.

## Features

- Generate images using ComfyUI's API and a classic KSampler checkpoint workflow
- Batch-generate from JSON manifests
- Import local assets with provenance and manually declared licenses
- Catalog files with JSON metadata, including model, prompt, seed and license
- Export tracked assets to ZIP without accidentally including unrelated files or API keys
- Optional MCP server: generate_image, list_assets, import_local_asset

This release does NOT automatically create 3D models, videos, spritesheets, playable games or download licensed Fab/Quixel marketplace assets. Additional models and integrations are necessary for those workflows.

## Requirements

Python 3.10+, ComfyUI at http://127.0.0.1:8188 (or configured address), a compatible installed checkpoint, and sufficient compute. The source code does not require paid subscriptions.

## Install

    git clone https://github.com/Mert-Oezdemir/agent-asset-forge.git
    cd agent-asset-forge
    python -m venv .venv
    # macOS/Linux: source .venv/bin/activate
    # Windows PowerShell: .venv\Scripts\Activate.ps1
    python -m pip install -e .
    assetforge --help

Run ComfyUI separately, then inspect available checkpoint filenames:

    assetforge doctor

Replace the placeholder model filename below with a real checkpoint reported by the doctor command.

## Generate images

    assetforge generate "cinematic moonlit forest with fog" --name forest-bg --checkpoint "YOUR_INSTALLED_CHECKPOINT.safetensors" --kind background --width 768 --height 768 --output assets

Offline workflow preview (does NOT generate an image):

    assetforge generate "glowing fantasy sword" --name sword --checkpoint example.ckpt --dry-run

Batch generation:

    assetforge batch examples/manifest.json --output assets

For the batch manifest, first replace placeholder model names with an installed checkpoint. To generate a new manifest:

    assetforge init --path my-assets.json

## Import existing licensed assets

    assetforge import ./downloaded/sword.png --name sword --license CC0-1.0 --source-url https://example.org/source --output assets

The license is user-declared, **not automatically verified**. Check source terms, attribution and redistribution rules before use. AI-generated output records default to license "unverified" because checkpoint/output license terms can differ.

## Catalog and export

    assetforge catalog --output assets
    assetforge pack --output assets --destination assets-export.zip

Only cataloged asset files, JSON sidecars and a manifest are packaged. Secret files and downloaded models are excluded.

## AI agent integration via MCP

Install the optional MCP dependency:

    python -m pip install -e ".[mcp]"

Copy examples/vscode-mcp.json to .vscode/mcp.json and adjust the Python interpreter path to your virtual environment. Enable the server in your editor's MCP settings.

MCP tools:

- generate_image: create a raster image via local ComfyUI and save it
- list_assets: retrieve the local asset catalog
- import_local_asset: copy an existing licensed file and record provenance

Environment variables:
- ASSETFORGE_COMFY_URL: default http://127.0.0.1:8188
- ASSETFORGE_LIBRARY: default ./assets
- ASSETFORGE_WORKFLOW: default packaged sd15-api.json

The bundled workflow requires CheckpointLoaderSimple, EmptyLatentImage, KSampler, SaveImage and separate CLIPTextEncode positive/negative nodes. Export custom workflows using ComfyUI API-format JSON. Flux, video, 3D and arbitrary custom-node graphs are not directly supported.

Example instruction for a coding agent: "Generate a forest background using my installed ComfyUI checkpoint, check the actual returned file, then use that file as an asset in my game. Report any tool errors."

## Tests

    python -m unittest discover -s tests -v

GitHub Actions runs the offline tests on Python 3.10, 3.12 and 3.13. These tests use a fake ComfyUI backend. Running and visually reviewing real model outputs requires your own local setup.

## Security

Keep ComfyUI on localhost unless you have configured authentication/network controls. Give AI agents access only to approved project directories. Do not publish personal data, API keys, copyrighted assets or checkpoint weights without appropriate rights.

## License

MIT for the software source code. **Third-party models and generated/imported assets have independent licensing terms.** See [LICENSE](LICENSE).
