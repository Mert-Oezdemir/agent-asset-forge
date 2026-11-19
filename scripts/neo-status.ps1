# Agent Asset Forge / NEO - read-only diagnostics; -GenerateTest opts in to image output
param(
    [string]$Root = "C:\Projelerim\AI-Asset-Forge",
    [switch]$GenerateTest
)
$ErrorActionPreference = "Stop"
$comfyPy = Join-Path $Root "ComfyUI\.venv\Scripts\python.exe"
$forgeExe = Join-Path $Root "agent-asset-forge\.venv\Scripts\assetforge.exe"
$comfyMain = Join-Path $Root "ComfyUI\main.py"
$target = Join-Path $Root "assets"
Write-Host "Agent Asset Forge / NEO" -ForegroundColor Cyan
Write-Host "Root: $Root"
foreach ($path in @($comfyPy, $forgeExe, $comfyMain)) {
    if (-not (Test-Path $path)) { throw "Missing required file: $path" }
}
& $comfyPy -c 'import torch; print("torch:", torch.__version__); print("CUDA:", torch.cuda.is_available()); print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NOT FOUND")'
if ($LASTEXITCODE -ne 0) { throw "PyTorch health check failed" }
try {
    $stats = Invoke-RestMethod -Uri "http://127.0.0.1:8188/system_stats" -TimeoutSec 5
    Write-Host "ComfyUI API: OK" -ForegroundColor Green
} catch {
    Write-Warning "ComfyUI API is not running. Start it with ComfyUI-Baslat.bat."
    exit 2
}
& $forgeExe doctor
if ($LASTEXITCODE -ne 0) { throw "Asset Forge doctor failed" }
if ($GenerateTest) {
    & $forgeExe generate "beautiful highly detailed stylized game asset, enchanted forest portal, cinematic lighting" --name neo-verification --kind background --checkpoint v1-5-pruned-emaonly.safetensors --width 512 --height 512 --steps 16 --cfg 7 --output $target --timeout 600
    if ($LASTEXITCODE -ne 0) { throw "Real image generation failed" }
}
Write-Host "Status check completed." -ForegroundColor Green
