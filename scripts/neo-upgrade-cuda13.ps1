# Optional Windows CUDA 13 maintenance. Default is READ-ONLY. Run with -Apply to change packages.
param(
    [string]$Root = "C:\Projelerim\AI-Asset-Forge",
    [switch]$Apply
)
$ErrorActionPreference = "Stop"
$python = Join-Path $Root "ComfyUI\.venv\Scripts\python.exe"
$uv = "C:\Users\mert_\AppData\Local\Programs\ComfyUI\resources\uv\win\uv.exe"
if (-not (Test-Path $python)) { throw "ComfyUI Python environment not found: $python" }
if (-not (Test-Path $uv)) { throw "uv not found: $uv" }
& $python -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
if ($LASTEXITCODE -ne 0) { throw "Current PyTorch is not importable; aborting." }
if (-not $Apply) {
    Write-Host "DRY RUN. To install official CUDA 13 PyTorch builds, rerun with -Apply." -ForegroundColor Yellow
    Write-Host "Stop ComfyUI and check NVIDIA driver compatibility first. Nothing was changed."
    exit 0
}
$connection = Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue
if ($connection) { throw "ComfyUI appears to be running; stop it before upgrading." }
$backup = Join-Path $Root ("comfy-packages-before-cuda13-" + (Get-Date -Format yyyyMMdd-HHmmss) + ".txt")
& $python -m pip freeze | Set-Content -Path $backup -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "Could not back up installed package list." }
$env:UV_NATIVE_TLS = "true"
Write-Host "Updating torch and torchvision using the official cu130 wheel index." -ForegroundColor Cyan
& $uv pip install --python $python --index-url "https://download.pytorch.org/whl/cu130" --upgrade torch torchvision
if ($LASTEXITCODE -ne 0) {
    throw "Upgrade failed; package snapshot: $backup. Restore the previous version before production use."
}
& $python -c 'import torch; assert torch.cuda.is_available(); assert "+cu130" in torch.__version__, torch.__version__; x=torch.ones(4,device="cuda"); print(torch.__version__,float(x.sum()))'
if ($LASTEXITCODE -ne 0) {
    throw "CUDA verification FAILED after upgrade; package snapshot: $backup."
}
Write-Host "CUDA 13 upgrade verified; start ComfyUI and generate a test asset." -ForegroundColor Green
