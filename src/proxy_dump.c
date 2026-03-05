/*
 * Lineage Classic English Translation Patch - Blob Capture DLL
 * Created by Sentia Turing (sentiaturingllc@gmail.com)
 * https://github.com/sentiaturing/lcx-english
 *
 * Captures all decrypted zstd blobs to files for analysis.
 * Used to recapture blobs after game updates.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

static HMODULE hOrigDLL = NULL;
static FILE *logFile = NULL;
static CRITICAL_SECTION cs;
static int blobCount = 0;

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

static void dumpBlob(Ctx *e) {
  if (!e || e->len < 12)
    return;
  /* Only dump zstd frames */
  if (e->buf[0] != 0x28 || e->buf[1] != 0xb5 || e->buf[2] != 0x2f ||
      e->buf[3] != 0xfd)
    return;

  char ud[MAX_PATH], path[MAX_PATH];
  GetEnvironmentVariableA("USERPROFILE", ud, MAX_PATH);
  snprintf(path, MAX_PATH, "%s\\lcx_decrypted\\new_%05d.bin", ud, blobCount);

  FILE *f = fopen(path, "wb");
  if (f) {
    fwrite(e->buf, 1, e->len, f);
    fclose(f);
  }

  if (logFile) {
    fprintf(logFile,
            "DUMP new_%05d.bin size=%d fp:%02x%02x%02x%02x%02x%02x%02x%02x\n",
            blobCount, e->len, e->buf[4], e->buf[5], e->buf[6], e->buf[7],
            e->buf[8], e->buf[9], e->buf[10], e->buf[11]);
    fflush(logFile);
  }
  blobCount++;
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
    dumpBlob(e);
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
    dumpBlob(e);
    fc(e);
  }
  return r;
}

typedef int (*fCTRL)(void *, int, int, void *);
__declspec(dllexport) int EVP_CIPHER_CTX_ctrl(void *ctx, int type, int arg,
                                              void *ptr) {
  static fCTRL oCtrl = NULL;
  if (!oCtrl)
    oCtrl = (fCTRL)GetProcAddress(hOrigDLL, "EVP_CIPHER_CTX_ctrl");
  return oCtrl(ctx, type, arg, ptr);
}

BOOL WINAPI DllMain(HINSTANCE hDll, DWORD reason, LPVOID r) {
  if (reason == DLL_PROCESS_ATTACH) {
    char my[MAX_PATH], lg[MAX_PATH], ud[MAX_PATH], *s;
    InitializeCriticalSection(&cs);
    GetEnvironmentVariableA("USERPROFILE", ud, MAX_PATH);
    snprintf(lg, MAX_PATH, "%s\\lcx_decrypted\\decrypt_log.txt", ud);
    logFile = fopen(lg, "a");
    if (logFile) {
      fprintf(logFile, "=== DUMP MODE ===\n");
      fflush(logFile);
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
      fprintf(logFile, "OK - dumping blobs\n");
      fflush(logFile);
    }
  } else if (reason == DLL_PROCESS_DETACH) {
    if (logFile) {
      fprintf(logFile, "Dumped %d blobs\nbye\n", blobCount);
      fclose(logFile);
    }
    if (hOrigDLL)
      FreeLibrary(hOrigDLL);
    DeleteCriticalSection(&cs);
  }
  return TRUE;
}
