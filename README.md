# 🏰 Lineage Classic — English Translation Patch

A runtime translation patch for **Lineage Classic TW** that replaces Chinese/Korean game text with English — no file modification, no repacking, fully reversible.

## 🛡️ Is This Safe?

**Yes.** Here's why in plain English:

- **No game files are changed.** The original game DLL is simply renamed (backed up), and our translation DLL sits in its place. The game itself is untouched.
- **Nothing is sent to the server.** The patch works 100% locally on your computer. It only changes what text *you* see on your screen — the game still talks to the server in exactly the same way as normal.
- **The server can't tell the difference.** Your game client sends and receives the same network packets as every other player. The translation only happens *after* the game has already decrypted its own files, right before it shows text on your screen. Think of it like reading subtitles — the movie doesn't know you're reading them.
- **Fully reversible.** Run `uninstall.bat` and the original DLL is restored. Or just reinstall the game. No traces left.
- **Open source.** All the code is right here — you can read every line yourself. The proxy DLL is ~90 lines of C. No obfuscation, no hidden behavior.

> **TL;DR:** This is like putting a transparent overlay on your screen that translates text. The game doesn't know, the server doesn't know, and you can remove it anytime.

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

### After a Game Update

Game updates can affect the patch in **two ways:**

1. **The DLL gets replaced.** The launcher overwrites `libcrypto-3-x64.dll` with the original every update. **Fix:** Just re-run `install.bat` as administrator.

2. **The game data changes.** This is the trickier one. The patch works by matching decrypted data blobs by their exact **size and fingerprint** (the first 8 bytes of each blob). When the game adds or changes items, strings, or other data, those blobs change size — and our patches no longer match. When this happens, the DLL loads fine but the translations silently don't apply (the game stays in Chinese).

   **Fix:** The patches and fingerprint files in this repo need to be regenerated for the new game version. Check for updates to this repo, or use `src/proxy_dump.c` to recapture the new blobs and regenerate patches yourself (see Building from Source).

> **In short:** After every update, first try re-running `install.bat`. If the game is still in Chinese, the patch files need to be updated — check this repo for a new release.

---

## ❓ Troubleshooting

**Game is still in Chinese after installing**
- Make sure you ran `install.bat` as **administrator** (right-click → Run as administrator). The game is installed in `Program Files`, which requires admin access to modify. If you didn't run as admin, the script fails silently — just run it again as admin.

**How do I know the patch is installed?**
- Check the file size of `libcrypto-3-x64.dll` in the game folder. The original is ~4.7 MB. Our proxy is ~912 KB. If it's still 4.7 MB, the install didn't work — run `install.bat` as admin.

**Game crashes on startup**
- Make sure `libcrypto_orig.dll` exists in the game folder alongside `libcrypto-3-x64.dll`. The proxy needs the original DLL to forward OpenSSL calls. If it's missing, reinstall the game and run `install.bat` again.

**Game updated and patch stopped working**
- First, re-run `install.bat` as admin (the update replaced the DLL). If it's still in Chinese after that, the game data changed and the patches need to be regenerated — check this repo for an updated release.

**I want to completely remove all traces**
1. Run `uninstall.bat` as admin (restores original DLL)
2. Delete `%USERPROFILE%\lcx_final\` and `%USERPROFILE%\lcx_decrypted\`

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
