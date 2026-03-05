/*
 * Lineage Classic English Translation Patch - Proxy DLL v11
 * Created by Sentia Turing (sentiaturingllc@gmail.com)
 * https://github.com/sentiaturing/lcx-english
 *
 * Runtime translation via OpenSSL proxy DLL interception.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

static HMODULE hOrigDLL = NULL;
static FILE *logFile = NULL;
static FILE *pktLog = NULL;

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
