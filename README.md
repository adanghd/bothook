# Rate Card Bot

Telegram bot untuk content creator Indonesia yang otomatis generate rate card, kalkulasi harga endorsement/affiliate, dan buat proposal PDF profesional.

**Tidak butuh API key AI apapun** — semua kalkulasi pakai formula matematika (CPM x Engagement Rate x Content Factor).

## Features

- Auto-calculate endorsement rates berdasarkan stats platform (IG, TikTok, YouTube, Twitter, LinkedIn, Facebook)
- 3 tier paket: Bronze / Silver / Gold
- Affiliate commission rates (TikTok Shop, Shopee Affiliate)
- Generate PDF rate card profesional (Bahasa Indonesia & English)
- English mode otomatis convert harga ke USD ($)
- Custom add-ons management via Telegram
- Proposal PDF untuk klien
- Export Excel
- Web dashboard (localhost)
- Semua fitur diakses dari 1 command: `/start`

## Requirements

- Python 3.10+
- Telegram Bot Token (gratis dari [@BotFather](https://t.me/BotFather))

---

## Setup Option 1: Install di PC Lokal

### Step 1 — Clone repo

```bash
git clone https://github.com/adanghd/bothook.git
cd bothook
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Buat Telegram Bot Token

1. Buka Telegram, cari **@BotFather**
2. Ketik `/newbot`, ikuti instruksi
3. Copy token yang dikasih (contoh: `123456:ABC-DEF...`)

### Step 4 — Set token

**Opsi A** — Environment variable:

```bash
# Linux/Mac
export TELEGRAM_TOKEN="123456:ABC-DEF..."

# Windows (cmd)
set TELEGRAM_TOKEN=123456:ABC-DEF...

# Windows (PowerShell)
$env:TELEGRAM_TOKEN = "123456:ABC-DEF..."
```

**Opsi B** — Config file:

Buat file `~/.kalopilot/telegram.json`:
```json
{
  "bot_token": "123456:ABC-DEF..."
}
```

### Step 5 — Jalankan bot

```bash
python main.py
```

Bot jalan! Buka Telegram, ketik `/start` ke bot kamu.

> **Note:** Bot hanya aktif selama terminal terbuka. Tutup terminal = bot mati.

---

## Setup Option 2: Deploy ke Railway (24/7, Gratis)

Bot jalan terus tanpa buka terminal. Railway punya free tier yang cukup untuk bot Telegram.

### Step 1 — Push ke GitHub

Pastikan kode sudah di-push ke GitHub repository kamu.

### Step 2 — Buat akun Railway

1. Buka [railway.app](https://railway.app)
2. Sign up dengan GitHub

### Step 3 — Deploy

1. Klik **"New Project"**
2. Pilih **"Deploy from GitHub repo"**
3. Pilih repo `bothook`
4. Railway akan auto-detect `Procfile` dan mulai build

### Step 4 — Set environment variable

1. Di Railway dashboard, klik service kamu
2. Pergi ke tab **"Variables"**
3. Tambah variable:
   ```
   TELEGRAM_TOKEN = 123456:ABC-DEF...
   ```
4. Klik **"Deploy"** — bot jalan 24/7!

### Step 5 — Verifikasi

Buka Telegram, ketik `/start` ke bot. Kalau ada reply, berarti sudah jalan.

---

## Cara Pakai

Semua fitur diakses dari command `/start`:

| Menu | Fungsi |
|---|---|
| Rate Card | Generate rate card (pilih tier, bahasa, format text/PDF) |
| Buat Proposal | Wizard buat proposal klien |
| Update Stats | Update followers, views, engagement rate per platform |
| History | 10 proposal terakhir |
| Add-ons | Kelola custom add-on (tambah, toggle, hapus) |
| Export Excel | Download spreadsheet |

### Output PDF

- **Bahasa Indonesia** — harga dalam Rupiah (Rp)
- **English** — harga otomatis convert ke USD ($)

---

## Konfigurasi

### Branding & Template

Edit file `ratecard/assets/rate_card_template.json`:

```json
{
  "brand_color_hex": "#E91E8C",
  "font_name": "Helvetica",
  "payment_terms": "50% DP, 50% setelah konten tayang",
  "revision_policy": "Maks 2x revisi termasuk dalam paket",
  "additional_notes": "Harga belum termasuk PPN."
}
```

### CPM Baselines

Edit file `ratecard/assets/platform_defaults.json` untuk adjust CPM rate per platform.

### Exchange Rate (IDR to USD)

Edit `ratecard/core/pricing.py`, variable `IDR_TO_USD_RATE` (default: 16500).

---

## Tech Stack

- Python 3.10+
- python-telegram-bot 13.15
- ReportLab (PDF generation)
- Flask (web dashboard)
- SQLite (database, auto-created)
- openpyxl (Excel export)

**No AI API keys needed.** Semua kalkulasi rule-based.

---

## License

MIT
