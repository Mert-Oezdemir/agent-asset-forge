# Neo / Windows - sonraki adımlar

Bu rehber, daha önce Neo bilgisayarında **gerçek görsel üretimiyle doğrulanan** yerel kurulumu geliştirmek içindir.

Mevcut kurulum:

- Dizin: C:\Projelerim\AI-Asset-Forge
- Ekran kartı: NVIDIA RTX 3080 Ti / 12 GB VRAM
- RAM: 32 GB
- ComfyUI: 0.46.0
- Doğrulanmış PyTorch: 2.11.0 + CUDA 12.8
- Doğrulanmış temel checkpoint: v1-5-pruned-emaonly.safetensors
- Oluşturulan ilk görsel: assets\neo-ilk-test-20261119-1-de6da2.png

**Uyarı:** Aşağıdaki sonraki yükseltmelerin Neo'da tamamlandığı söylenmiyor. Önceden çalışan sistemi koru.

## Kontrol aracı

PowerShell:

    cd C:\Projelerim\AI-Asset-Forge
    powershell -ExecutionPolicy Bypass -File .\agent-asset-forge\scripts\neo-status.ps1

ComfyUI 127.0.0.1:8188 üzerinde açık olmalı. Gerçek test görseli de üretmek istiyorsan aynı komuta -GenerateTest ekle.

## CUDA 13 (isteğe bağlı)

ComfyUI'nin resmî yönergeleri NVIDIA RTX 20 ve üzeri ekran kartlarında CUDA 13 tabanlı PyTorch'u tavsiye ediyor. 12.8 ile Neo üzerinde görsel üretimi zaten çalıştı. Bu yükseltme optimizasyonlar içindir; mecburi değil.

Önce ComfyUI sunucusunu kapat. Ardından salt okunur kontrol:

    powershell -ExecutionPolicy Bypass -File .\agent-asset-forge\scripts\neo-upgrade-cuda13.ps1

Ekran kartı sürücüsü ve uyumluluk durumunu kontrol et. Yükseltmek için aynı komuta -Apply parametresi ekle. Script değişiklikten önce paket listesini ayrı dosyaya yazar ve sonucu CUDA ile doğrular. Otomatik rollback yapmaz.

## SDXL ile daha kaliteli konsept art

1024 px boyutunda 2D asset denemek için mevcut SD1.5 modeline ek olarak SDXL tabanlı bir checkpoint kullanılabilir. Örnek, sadece JSON manifestidir: examples/sdxl-quality-manifest.json.

1. Lisansını kontrol ettiğin, ComfyUI ile uyumlu bir SDXL base checkpoint indir.
2. Dosyayı ComfyUI\models\checkpoints dizinine koy.
3. Asset Forge doctor ile modelin listelendiğini doğrula.
4. Örnek JSON içindeki REPLACE_WITH_YOUR_SDXL_BASE_CHECKPOINT.safetensors adını gerçek model adıyla değiştir.
5. Asset Forge batch komutunu çalıştır.

    assetforge batch examples\sdxl-quality-manifest.json --output assets

Bu örnek yeni modeli otomatik indirmez. 12 GB VRAM ile çalışan diğer GPU uygulamalarının kapatılması gerekebilir. Üçüncü taraf modelin lisansına ve dağıtım haklarına dikkat et.

## MCP ile kod agentı

Cursor içinde C:\Projelerim\AI-Asset-Forge dizinini aç. Projeye önceden oluşturulan .cursor\mcp.json bağlantısını aktifleştir. MCP araçlarının listelendiğini doğrula.

Örnek:

"Asset Forge MCP aracıyla 512x512 fantastik orman arka planı oluştur. v1-5-pruned-emaonly.safetensors modelini kullan. Gerçekte oluşan PNG'yi denetle ve projeme ekle."

## Bilinen sınırlar

Mevcut sürüm 2D raster asset üretir. Blender ve FFmpeg'nin bilgisayarda kurulu olması tek başına otomatik video ve 3D araçları olduğu anlamına gelmez. Bunlar ayrı entegrasyon gerektirir.

Kaynak: https://github.com/Comfy-Org/ComfyUI
