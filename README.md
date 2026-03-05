# 🏰 Lineage Classic — English Translation Patch

A runtime translation patch for **Lineage Classic TW** that replaces Chinese/Korean game text with English — no file modification, no repacking, fully reversible.

## 📊 Current Coverage

| Category | Translated | Total | Coverage |
|----------|-----------|-------|----------|
| UI Strings | 443 | 1,541 | 29% |
| Item Names | 1,201 | 1,882 | 64% |
| **Total** | **1,644** | **3,423** | **48%** |

> Spells, NPC dialogue, and more are in progress.

---

## 🚀 Installation

### Quick Install

1. Download or clone this repo
2. Right-click `install\install.bat` → **Run as administrator**
3. Launch the game — you'll see English text!

### Manual Install

If the installer doesn't work, you can do it manually:

**Step 1 — Backup the original DLL** (in the game folder):
```
cd "C:\Program Files (x86)\NCSOFT\Lineage Classic"
rename libcrypto-3-x64.dll libcrypto_orig.dll
```

**Step 2 — Install the proxy DLL:**
```
copy install\lcx_english.dll "C:\Program Files (x86)\NCSOFT\Lineage Classic\libcrypto-3-x64.dll"
```

**Step 3 — Install patch files:**
```
mkdir "%USERPROFILE%\lcx_final"
copy install\string_en_padded.zst "%USERPROFILE%\lcx_final\"
copy install\items_en_padded.zst "%USERPROFILE%\lcx_final\"
```

**Step 4 — Install fingerprint files:**
```
mkdir "%USERPROFILE%\lcx_decrypted"
copy install\file_00083.bin "%USERPROFILE%\lcx_decrypted\"
copy install\file_00084.bin "%USERPROFILE%\lcx_decrypted\"
```

### Uninstall

Run `install\uninstall.bat` as administrator, or simply:
```
cd "C:\Program Files (x86)\NCSOFT\Lineage Classic"
copy /Y libcrypto_orig.dll libcrypto-3-x64.dll
del libcrypto_orig.dll
```

---

## ✨ How It Works

The game encrypts all assets inside `.lcx` archives using per-file AES keys via OpenSSL. This patch uses a **proxy DLL** to intercept decryption at runtime:

```
LC.exe → libcrypto-3-x64.dll (our proxy) → libcrypto_orig.dll (real OpenSSL)
                  │
                  ├─ Intercepts EVP_DecryptInit / Update / Final
                  ├─ Reassembles decrypted zstd-compressed CSV blobs
                  ├─ Matches blobs by SIZE + FINGERPRINT (first 8 bytes after zstd magic)
                  └─ Swaps matched blobs with pre-translated English versions
```

**Key design:**
- **No game files are modified** — the original DLL is preserved as `libcrypto_orig.dll`
- **Size + fingerprint matching** ensures patches only apply to the exact blobs they target
- **Zstd skippable frame padding** keeps replacement blobs byte-identical in size to originals

## 📖 Translation Sources

| Source | Type | Used For |
|--------|------|----------|
| [L1J-Wanted](https://github.com/baboqoo/L1J-Wanted) | KR→EN TBL files (EUC-KR) | Primary string + item translations |
| [l1j-en/classic](https://github.com/l1j-en/classic) | SQL database | Item names via `desc_id` mapping |
| `desc-c.tbl` / `desc-e.tbl` | CN→EN TBL files | Fallback from TW/CN client |
| Manual dictionary | Hardcoded map | Classes, alignments, stats, NPCs |

## 🔧 Building from Source

**Prerequisites:** MSYS2 MinGW-w64 GCC, Python 3 with `zstandard`

```bash
# Compile the proxy DLL
gcc -shared -o install/lcx_english.dll src/proxy_crypto.c src/proxy_crypto.def -lkernel32 -O2

# Generate translation patches (requires decrypted originals in %USERPROFILE%\lcx_decrypted\)
python scripts/translate_all.py
```

## 📁 Project Structure

```
├── src/
│   ├── proxy_crypto.c        # Proxy DLL source (~90 lines of C)
│   └── proxy_crypto.def      # DLL export definitions (forwards OpenSSL symbols)
├── scripts/
│   └── translate_all.py      # Translation pipeline (KR/CN/SQL → English)
├── install/                  # ★ Everything needed to install
│   ├── install.bat           # One-click installer (run as admin)
│   ├── uninstall.bat         # One-click uninstaller
│   ├── lcx_english.dll       # Proxy DLL
│   ├── string_en_padded.zst  # English strings patch
│   ├── items_en_padded.zst   # English items patch
│   ├── file_00083.bin        # Original strings fingerprint
│   └── file_00084.bin        # Original items fingerprint
└── README.md
```

## ⚖️ License

For **personal and educational use only**. All game assets and trademarks belong to NCSOFT Corporation. Community translation data is credited to its respective authors.
