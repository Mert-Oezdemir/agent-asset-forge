# Agent Asset Forge — Türkçe rehber

Higgsfield aboneliğine gerek duymayan, açık kaynak bir **AI görsel asset üretim başlangıç paketi**. Bir yapay zekâ kod agentı, MCP üzerinden yerel ComfyUI'ye görsel üretim görevi verebilir; oluşturulan görseller oyun veya web projelerinde kullanılabilecek bir klasörde saklanır.

**Önemli sınırlar:** İlk sürüm yalnızca 2D raster görseller üretir. Video, fotogerçekçi 3D model, rig/animasyon, AAA oyun ortamı ya da Fab/Quixel otomatik taraması mevcut değildir. Bunlar ilave modeller ve entegrasyonlarla geliştirilmelidir. Gerçek görsel üretiminin çalışması ve kalitesi donanımına, checkpoint'e ve ComfyUI yapılandırmana bağlıdır.

## 1. Gereklilikler

- Python 3.10 veya üzeri
- Bilgisayarda çalışan [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- ComfyUI içindeki models/checkpoints klasörüne yüklenmiş, kullanmaya yetkili olduğun klasik KSampler iş akışına uygun checkpoint
- Modeline uygun GPU/RAM
- İsteğe bağlı: VS Code/Cursor gibi MCP destekleyen bir AI kod agentı

## 2. Kurulum

    git clone https://github.com/Mert-Oezdemir/agent-asset-forge.git
    cd agent-asset-forge
    python -m venv .venv

Windows PowerShell:

    .venv\Scripts\Activate.ps1

macOS/Linux:

    source .venv/bin/activate

Sonra:

    python -m pip install -e .
    assetforge doctor

Doctor komutu ComfyUI'nin çalıştığını ve checkpoint adlarını kontrol eder. ComfyUI'yi önceden başlatmalısın.

## 3. İlk görselini üret

    assetforge generate "misty fantasy forest, cinematic lighting" --name orman --checkpoint "MODEL_ADIN.safetensors" --width 768 --height 768 --output assets

MODEL_ADIN.safetensors kısmına doctor komutunun gösterdiği gerçek dosya adını yaz.

ComfyUI olmadan üretilecek iş akışını görmek için:

    assetforge generate "magic sword" --name kilic --checkpoint deneme.ckpt --dry-run

Bu test komutu **gerçek görsel üretmez**.

## 4. Toplu üretim

    assetforge batch examples/manifest.json --output assets

examples/manifest.json içindeki örnek checkpoint adlarını değiştir. Kendi taslağını oluşturmak için:

    assetforge init --path benim-assetlerim.json

## 5. Hazır asset ekleme ve lisans kaydı

    assetforge import ./indirilen/kilic.png --name kilic --license CC0-1.0 --source-url https://example.org/asset --output assets

Verilen lisansın doğruluğundan sen sorumlusun. Program lisansı internetten otomatik doğrulamaz. Üretilen görsellerin hakları için de checkpoint lisansını kontrol et.

Kütüphaneyi listele ve ZIP olarak paketle:

    assetforge catalog --output assets
    assetforge pack --output assets --destination assetler.zip

## 6. AI agentına bağlama

    python -m pip install -e ".[mcp]"

examples/vscode-mcp.json dosyasını proje içindeki .vscode/mcp.json konumuna kopyala. Sunucuyu doğru Python sanal ortamından çalıştıracak şekilde yapılandır.

Agentın erişeceği araçlar:
- generate_image — ComfyUI ile görsel oluşturma
- list_assets — oluşturulan veya içeri alınan assetleri listeleme
- import_local_asset — mevcut lisanslı yerel dosyayı kütüphaneye ekleme

Örnek agent talimatı: "MCP içindeki generate_image aracıyla fantastik orman arka planı oluştur. Kaydedilen dosyanın yolunu doğrula. Sonra bunu web/oyun projemde kullan. Araç çalışmazsa başarılı olduğunu iddia etme."

Bu sistemin kodu MIT lisanslıdır. Üçüncü taraf modellerin ve assetlerin lisansları ayrıdır.
