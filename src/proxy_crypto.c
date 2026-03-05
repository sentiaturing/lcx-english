/*
 * Proxy DLL v11 - Patches + embedded speedhack
 * Translations + IAT-based timing hooks in one DLL.
 * No separate speedhack.dll needed (evades NCGuard module scan).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

static HMODULE hOrigDLL = NULL;
static FILE *logFile = NULL;
static FILE *pktLog = NULL;
static FILE *shLog = NULL;
static CRITICAL_SECTION cs;

#define MAX_PATCHES 8
typedef struct {
  unsigned char *data;
  int size;
  unsigned char fp[8];
  const char *name;
} Patch;
static Patch patches[MAX_PATCHES];
static int nPatch = 0;

#define MAX_CTX 256
typedef struct {
  void *ctx;
  unsigned char *buf;
  int cap, len, active;
  unsigned char *out0;
} Ctx;
static Ctx ctxT[MAX_CTX];

static Ctx *gc(void *c, int cr) {
  int i;
  for (i = 0; i < MAX_CTX; i++)
    if (ctxT[i].ctx == c && ctxT[i].active)
      return &ctxT[i];
  if (!cr)
    return NULL;
  for (i = 0; i < MAX_CTX; i++)
    if (!ctxT[i].active) {
      ctxT[i].ctx = c;
      ctxT[i].cap = 512 * 1024;
      ctxT[i].buf = malloc(ctxT[i].cap);
      ctxT[i].len = 0;
      ctxT[i].active = 1;
      ctxT[i].out0 = NULL;
      return &ctxT[i];
    }
  return NULL;
}

static void ac(Ctx *e, const unsigned char *d, int n) {
  if (!e || !e->buf || n <= 0)
    return;
  while (e->len + n > e->cap) {
    e->cap *= 2;
    e->buf = realloc(e->buf, e->cap);
  }
  memcpy(e->buf + e->len, d, n);
  e->len += n;
}

static void fc(Ctx *e) {
  if (e->buf)
    free(e->buf);
  memset(e, 0, sizeof(Ctx));
}

static void tp(Ctx *e) {
  int i;
  if (!e || !e->out0 || e->len < 12)
    return;
  if (e->buf[0] != 0x28 || e->buf[1] != 0xb5 || e->buf[2] != 0x2f ||
      e->buf[3] != 0xfd)
    return;
  for (i = 0; i < nPatch; i++) {
    if (patches[i].data && patches[i].size == e->len &&
        memcmp(e->buf + 4, patches[i].fp, 8) == 0) {
      memcpy(e->out0, patches[i].data, patches[i].size);
      if (logFile) {
        fprintf(logFile, "PATCHED %s (%d)\n", patches[i].name, patches[i].size);
        fflush(logFile);
      }
      return;
    }
  }
}

/* Packet hex dump logger - full packet */
static void logPkt(const char *dir, const unsigned char *data, int len) {
  int i;
  if (!pktLog || len <= 0)
    return;
  EnterCriticalSection(&cs);
  LARGE_INTEGER freq, now;
  QueryPerformanceFrequency(&freq);
  QueryPerformanceCounter(&now);
  double ts = (double)now.QuadPart / freq.QuadPart;
  fprintf(pktLog, "[%12.4f] %s len=%d ", ts, dir, len);
  for (i = 0; i < len; i++)
    fprintf(pktLog, "%02X ", data[i]);
  fprintf(pktLog, "\n");
  fflush(pktLog);
  LeaveCriticalSection(&cs);
}

typedef int (*fDI)(void *, void *, void *, const unsigned char *,
                   const unsigned char *);
typedef int (*fDU)(void *, unsigned char *, int *, const unsigned char *, int);
typedef int (*fDF)(void *, unsigned char *, int *);
typedef int (*fDI4)(void *, void *, const unsigned char *,
                    const unsigned char *);
static fDI oDI;
static fDU oDU;
static fDF oDF;

__declspec(dllexport) int EVP_DecryptInit_ex(void *c, void *t, void *i,
                                             const unsigned char *k,
                                             const unsigned char *v) {
  Ctx *e;
  if (!oDI)
    oDI = (fDI)GetProcAddress(hOrigDLL, "EVP_DecryptInit_ex");
  int r = oDI(c, t, i, k, v);
  if (r == 1) {
    e = gc(c, 1);
    if (e) {
      e->len = 0;
      e->out0 = NULL;
    }
  }
  return r;
}

__declspec(dllexport) int EVP_DecryptUpdate(void *c, unsigned char *o, int *ol,
                                            const unsigned char *in, int il) {
  if (!oDU)
    oDU = (fDU)GetProcAddress(hOrigDLL, "EVP_DecryptUpdate");
  int r = oDU(c, o, ol, in, il);
  if (r == 1 && *ol > 0) {
    Ctx *e = gc(c, 1);
    if (e) {
      if (!e->out0)
        e->out0 = o;
      ac(e, o, *ol);
    }
    logPkt("S->C", o, *ol);
  }
  return r;
}

__declspec(dllexport) int EVP_DecryptFinal_ex(void *c, unsigned char *o,
                                              int *ol) {
  Ctx *e;
  if (!oDF)
    oDF = (fDF)GetProcAddress(hOrigDLL, "EVP_DecryptFinal_ex");
  int r = oDF(c, o, ol);
  e = gc(c, 0);
  if (e) {
    if (r == 1 && ol && *ol > 0)
      ac(e, o, *ol);
    tp(e);
    fc(e);
  }
  return r;
}

__declspec(dllexport) int EVP_DecryptInit(void *c, void *t,
                                          const unsigned char *k,
                                          const unsigned char *v) {
  fDI4 fn = (fDI4)GetProcAddress(hOrigDLL, "EVP_DecryptInit");
  int r = fn(c, t, k, v);
  if (r == 1) {
    Ctx *e = gc(c, 1);
    if (e) {
      e->len = 0;
      e->out0 = NULL;
    }
  }
  return r;
}

__declspec(dllexport) int EVP_DecryptFinal(void *c, unsigned char *o, int *ol) {
  fDF fn = (fDF)GetProcAddress(hOrigDLL, "EVP_DecryptFinal");
  int r = fn(c, o, ol);
  Ctx *e = gc(c, 0);
  if (e) {
    if (r == 1 && ol && *ol > 0)
      ac(e, o, *ol);
    tp(e);
    fc(e);
  }
  return r;
}

/* Forwarded export - required by NCGuard integrity check */
typedef int (*fCTRL)(void *, int, int, void *);
__declspec(dllexport) int EVP_CIPHER_CTX_ctrl(void *ctx, int type, int arg,
                                              void *ptr) {
  static fCTRL oCtrl = NULL;
  if (!oCtrl)
    oCtrl = (fCTRL)GetProcAddress(hOrigDLL, "EVP_CIPHER_CTX_ctrl");
  return oCtrl(ctx, type, arg, ptr);
}

/* ============================================================
 * EMBEDDED SPEEDHACK ENGINE
 * ============================================================ */
static double sh_speed = 1.0;
static int sh_enabled = 0;
static int sh_pulse = 0; /* 0=off, 1=pulse mode */
static DWORD sh_base32 = 0;
static ULONGLONG sh_base64 = 0;
static DWORD sh_basemm = 0;
static LARGE_INTEGER sh_baseqpc = {0};

typedef DWORD(WINAPI *fn_GTC)(void);
typedef ULONGLONG(WINAPI *fn_GTC64)(void);
typedef DWORD(WINAPI *fn_TGT)(void);
typedef BOOL(WINAPI *fn_QPC)(LARGE_INTEGER *);
static fn_GTC r_GTC = NULL;
static fn_GTC64 r_GTC64 = NULL;
static fn_TGT r_TGT = NULL;
static fn_QPC r_QPC = NULL;

static void shlog(const char *fmt, ...) {
  if (!shLog)
    return;
  va_list a;
  va_start(a, fmt);
  vfprintf(shLog, fmt, a);
  va_end(a);
  fflush(shLog);
}

static void *sh_iat_hook(HMODULE mod, const char *dll, const char *fn,
                         void *hook) {
  if (IsBadReadPtr(mod, sizeof(IMAGE_DOS_HEADER)))
    return NULL;
  PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)mod;
  if (dos->e_magic != 0x5A4D)
    return NULL;
  PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)((BYTE *)mod + dos->e_lfanew);
  if (IsBadReadPtr(nt, sizeof(IMAGE_NT_HEADERS)))
    return NULL;
  DWORD rva = nt->OptionalHeader.DataDirectory[1].VirtualAddress;
  if (!rva)
    return NULL;
  PIMAGE_IMPORT_DESCRIPTOR imp = (PIMAGE_IMPORT_DESCRIPTOR)((BYTE *)mod + rva);
  for (; imp->Name; imp++) {
    if (_stricmp((char *)mod + imp->Name, dll) != 0)
      continue;
    PIMAGE_THUNK_DATA ot =
        (PIMAGE_THUNK_DATA)((BYTE *)mod + imp->OriginalFirstThunk);
    PIMAGE_THUNK_DATA t = (PIMAGE_THUNK_DATA)((BYTE *)mod + imp->FirstThunk);
    for (; ot->u1.AddressOfData; ot++, t++) {
      if (ot->u1.Ordinal & IMAGE_ORDINAL_FLAG)
        continue;
      PIMAGE_IMPORT_BY_NAME n =
          (PIMAGE_IMPORT_BY_NAME)((BYTE *)mod + ot->u1.AddressOfData);
      if (strcmp(n->Name, fn) == 0) {
        void *orig = (void *)t->u1.Function;
        DWORD old;
        VirtualProtect(&t->u1.Function, sizeof(void *), PAGE_READWRITE, &old);
        t->u1.Function = (ULONG_PTR)hook;
        VirtualProtect(&t->u1.Function, sizeof(void *), old, &old);
        return orig;
      }
    }
  }
  return NULL;
}

typedef BOOL(WINAPI *fn_EPM)(HANDLE, HMODULE *, DWORD, LPDWORD);
static int sh_hook_all(const char *dll, const char *fn, void *hook) {
  HMODULE mods[512];
  DWORD needed;
  int count = 0;
  fn_EPM epm = (fn_EPM)GetProcAddress(GetModuleHandleA("kernel32.dll"),
                                      "K32EnumProcessModules");
  if (!epm)
    epm =
        (fn_EPM)GetProcAddress(LoadLibraryA("psapi.dll"), "EnumProcessModules");
  if (!epm) {
    if (sh_iat_hook(GetModuleHandle(NULL), dll, fn, hook))
      count++;
    return count;
  }
  if (!epm(GetCurrentProcess(), mods, sizeof(mods), &needed))
    return 0;
  int n = needed / sizeof(HMODULE);
  for (int i = 0; i < n && i < 512; i++) {
    if (sh_iat_hook(mods[i], dll, fn, hook))
      count++;
  }
  return count;
}

static void sh_reset_base(void) {
  if (r_GTC)
    sh_base32 = r_GTC();
  if (r_GTC64)
    sh_base64 = r_GTC64();
  if (r_TGT)
    sh_basemm = r_TGT();
  if (r_QPC)
    r_QPC(&sh_baseqpc);
}

static DWORD WINAPI sh_h_GTC(void) {
  DWORD v = r_GTC();
  if (!sh_enabled)
    return v;
  return sh_base32 + (DWORD)((v - sh_base32) * sh_speed);
}
static ULONGLONG WINAPI sh_h_GTC64(void) {
  ULONGLONG v = r_GTC64();
  if (!sh_enabled)
    return v;
  return sh_base64 + (ULONGLONG)((v - sh_base64) * sh_speed);
}
static DWORD WINAPI sh_h_TGT(void) {
  DWORD v = r_TGT();
  if (!sh_enabled)
    return v;
  return sh_basemm + (DWORD)((v - sh_basemm) * sh_speed);
}
static BOOL WINAPI sh_h_QPC(LARGE_INTEGER *c) {
  BOOL r = r_QPC(c);
  if (!sh_enabled || !r)
    return r;
  c->QuadPart = sh_baseqpc.QuadPart +
                (LONGLONG)((c->QuadPart - sh_baseqpc.QuadPart) * sh_speed);
  return TRUE;
}

static DWORD WINAPI sh_hotkey_thread(LPVOID p) {
  DWORD pulse_timer = 0;
  int pulse_phase = 0; /* 0=fast, 1=normal */
  while (1) {
    Sleep(50);
    /* Pulse mode: auto-toggle every 2 seconds */
    if (sh_pulse) {
      pulse_timer += 50;
      if (pulse_timer >= (pulse_phase ? 4000 : 500)) { /* 0.5s fast, 4s rest */
        pulse_timer = 0;
        pulse_phase = !pulse_phase;
        sh_enabled = !pulse_phase; /* phase 0=fast, phase 1=normal */
        if (sh_enabled)
          sh_reset_base();
        shlog("[SH] PULSE %s (%.2fx)\n", sh_enabled ? "FAST" : "REST",
              sh_speed);
      }
    }
    if (GetAsyncKeyState(VK_INSERT) & 1) {
      sh_pulse = 0; /* disable pulse when manually toggling */
      sh_enabled = !sh_enabled;
      if (sh_enabled)
        sh_reset_base();
      shlog("[SH] %s (%.2fx)\n", sh_enabled ? "ON" : "OFF", sh_speed);
    }
    if (GetAsyncKeyState(VK_PRIOR) & 1) { /* PageUp = pulse mode */
      sh_pulse = !sh_pulse;
      pulse_timer = 0;
      pulse_phase = 0;
      if (sh_pulse) {
        sh_enabled = 1;
        sh_reset_base();
      } else {
        sh_enabled = 0;
      }
      shlog("[SH] PULSE %s (%.2fx)\n", sh_pulse ? "ON" : "OFF", sh_speed);
    }
    if (GetAsyncKeyState(VK_END) & 1) {
      if (sh_speed > 0.5) {
        sh_speed -= 0.25;
        if (sh_enabled)
          sh_reset_base();
      }
      shlog("[SH] Speed: %.2fx\n", sh_speed);
    }
    if (GetAsyncKeyState(VK_HOME) & 1) {
      if (sh_speed < 5.0) {
        sh_speed += 0.25;
        if (sh_enabled)
          sh_reset_base();
      }
      shlog("[SH] Speed: %.2fx\n", sh_speed);
    }
    if (GetAsyncKeyState(VK_DELETE) & 1) {
      sh_speed = 1.0;
      sh_pulse = 0;
      if (sh_enabled)
        sh_reset_base();
      shlog("[SH] RESET 1.0x\n");
    }
  }
  return 0;
}

static DWORD WINAPI sh_init_thread(LPVOID p) {
  Sleep(2000);
  char path[MAX_PATH];
  GetTempPathA(MAX_PATH, path);
  strcat(path, "speedhack.log");
  shLog = fopen(path, "w");
  shlog("=== SpeedHack v4 (embedded) ===\n");
  shlog("PID: %d\n\n", GetCurrentProcessId());
  HMODULE k32 = GetModuleHandleA("kernel32.dll");
  r_GTC = (fn_GTC)GetProcAddress(k32, "GetTickCount");
  r_GTC64 = (fn_GTC64)GetProcAddress(k32, "GetTickCount64");
  r_QPC = (fn_QPC)GetProcAddress(k32, "QueryPerformanceCounter");
  HMODULE wmm = GetModuleHandleA("winmm.dll");
  r_TGT = wmm ? (fn_TGT)GetProcAddress(wmm, "timeGetTime") : NULL;
  sh_reset_base();
  int n1 = sh_hook_all("kernel32.dll", "GetTickCount", sh_h_GTC);
  int n2 = sh_hook_all("kernel32.dll", "GetTickCount64", sh_h_GTC64);
  int n3 = sh_hook_all("kernel32.dll", "QueryPerformanceCounter", sh_h_QPC);
  int n4 = r_TGT ? sh_hook_all("winmm.dll", "timeGetTime", sh_h_TGT) : 0;
  shlog("Hooks: GTC=%d GTC64=%d QPC=%d TGT=%d TOTAL=%d\n", n1, n2, n3, n4,
        n1 + n2 + n3 + n4);
  shlog("INS=toggle HOME=faster END=slower DEL=reset PGUP=pulse\n");
  CreateThread(NULL, 0, sh_hotkey_thread, NULL, 0, NULL);
  return 0;
}

static void loadP(const char *pp, const char *op, const char *name) {
  FILE *f;
  long sz;
  unsigned char h[12];
  f = fopen(op, "rb");
  if (!f) {
    if (logFile) {
      fprintf(logFile, "skip %s (no orig)\n", name);
      fflush(logFile);
    }
    return;
  }
  fread(h, 1, 12, f);
  fclose(f);
  f = fopen(pp, "rb");
  if (!f) {
    if (logFile) {
      fprintf(logFile, "skip %s (no patch)\n", name);
      fflush(logFile);
    }
    return;
  }
  fseek(f, 0, SEEK_END);
  sz = ftell(f);
  fseek(f, 0, SEEK_SET);
  if (nPatch < MAX_PATCHES) {
    patches[nPatch].data = malloc(sz);
    if (patches[nPatch].data) {
      fread(patches[nPatch].data, 1, sz, f);
      patches[nPatch].size = sz;
      memcpy(patches[nPatch].fp, h + 4, 8);
      patches[nPatch].name = name;
      if (logFile) {
        fprintf(logFile, "  %s %ld fp:%02x%02x%02x%02x\n", name, sz, h[4], h[5],
                h[6], h[7]);
        fflush(logFile);
      }
      nPatch++;
    }
  }
  fclose(f);
}

BOOL WINAPI DllMain(HINSTANCE hDll, DWORD reason, LPVOID r) {
  if (reason == DLL_PROCESS_ATTACH) {
    char my[MAX_PATH], lg[MAX_PATH], ud[MAX_PATH], pp[MAX_PATH], op[MAX_PATH],
        *s;
    InitializeCriticalSection(&cs);
    GetEnvironmentVariableA("USERPROFILE", ud, MAX_PATH);
    snprintf(lg, MAX_PATH, "%s\\lcx_decrypted\\decrypt_log.txt", ud);
    logFile = fopen(lg, "a");
    /* Packet log file */
    snprintf(lg, MAX_PATH, "%s\\lcx_decrypted\\packet_log.txt", ud);
    pktLog = fopen(lg, "a");
    if (logFile) {
      fprintf(logFile, "=== v10+pktlog ===\n");
      fflush(logFile);
    }
    if (pktLog) {
      fprintf(pktLog, "\n=== SESSION START ===\n");
      fflush(pktLog);
    }
    GetModuleFileNameA(hDll, my, MAX_PATH);
    s = strrchr(my, '\\');
    if (s)
      strcpy(s + 1, "libcrypto_orig.dll");
    hOrigDLL = LoadLibraryA(my);
    if (!hOrigDLL)
      hOrigDLL = LoadLibraryA("libcrypto_orig.dll");
    if (!hOrigDLL) {
      if (logFile) {
        fprintf(logFile, "FATAL\n");
        fclose(logFile);
      }
      return FALSE;
    }
    if (logFile) {
      fprintf(logFile, "OK\n");
      fflush(logFile);
    }
    snprintf(pp, MAX_PATH, "%s\\lcx_final\\string_en_padded.zst", ud);
    snprintf(op, MAX_PATH, "%s\\lcx_decrypted\\file_00083.bin", ud);
    loadP(pp, op, "strings");
    snprintf(pp, MAX_PATH, "%s\\lcx_final\\items_en_padded.zst", ud);
    snprintf(op, MAX_PATH, "%s\\lcx_decrypted\\file_00084.bin", ud);
    loadP(pp, op, "items");
    snprintf(pp, MAX_PATH, "%s\\lcx_final\\spells_en_padded.zst", ud);
    snprintf(op, MAX_PATH, "%s\\lcx_decrypted\\file_00085.bin", ud);
    loadP(pp, op, "spells");
    snprintf(pp, MAX_PATH, "%s\\lcx_final\\dialogue_en_padded.zst", ud);
    snprintf(op, MAX_PATH, "%s\\lcx_decrypted\\file_00086.bin", ud);
    loadP(pp, op, "dialogue");
    if (logFile) {
      fprintf(logFile, "%d patches loaded\n", nPatch);
      fflush(logFile);
    }
    /* Start speedhack in delayed thread */
    CreateThread(NULL, 0, sh_init_thread, NULL, 0, NULL);
  } else if (reason == DLL_PROCESS_DETACH) {
    int i;
    if (logFile) {
      fprintf(logFile, "bye\n");
      fclose(logFile);
    }
    if (pktLog) {
      fprintf(pktLog, "=== SESSION END ===\n");
      fclose(pktLog);
    }
    for (i = 0; i < nPatch; i++)
      if (patches[i].data)
        free(patches[i].data);
    if (hOrigDLL)
      FreeLibrary(hOrigDLL);
    DeleteCriticalSection(&cs);
  }
  return TRUE;
}
