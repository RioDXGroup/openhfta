// Comprehensive differential test harness for the legacy core artifact vs OpenYTWCore
// - Loads both DLLs
// - Seeds COMMON blocks by calling YTWCore1 once (both sides) with a deterministic profile
// - Exercises internal routines with curated inputs that hit corner cases
// - Compares results with tolerances and reports mismatches
//
// Build flags are provided by your Makefile (CALLCONV_ORIG/CALLCONV_NEW, etc.)

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <float.h>
#include <ctype.h>
#include <dirent.h>
#include <sys/stat.h>
#include "ytw_addrs.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Sizes inferred from Fortran sources (be consistent with YTWCore1 interfaces)
#define YTW_N_DIST     151
#define YTW_N_ANT      4
#define YTW_N_OUT      140
#define YTW_N_COMPLEX  182  // 0..181 inclusive

typedef struct { float r, i; } complex8;

// Fortran INTEGER*2 is 16-bit
typedef int16_t ftn_i2;
typedef int32_t ftn_i4;

// Prototypes (ORIG by fixed VA, NEW by GetProcAddress)
typedef float  (CALLCONV_ORIG *ATN4_o_t)(float*, float*);
typedef void   (CALLCONV_ORIG *ANGHORIZ_o_t)(float*, float*, float*);
typedef void   (CALLCONV_ORIG *ANGIN_o_t)(float*, float*, float*, float*, float*, float*, ftn_i4*);
typedef void   (CALLCONV_ORIG *YUTD_o_t)(float*, float*, float*, float*, float*, float*, float*);
typedef void   (CALLCONV_ORIG *WD_o_t)(complex8*, float*, float*, float*, float*, float*);
// Original FFCT likely returns complex via sret (hidden pointer first)
typedef void   (CALLCONV_ORIG *FFCT_o_sret_t)(complex8*, float*);
typedef void   (CALLCONV_ORIG *FRESNEL_o_t)(float*, float*, float*, float*, float*);
typedef void   (CALLCONV_ORIG *DIFFDIFF_o_t)(ftn_i4*, ftn_i4*, ftn_i4*, ftn_i4*, ftn_i4*, float*, ftn_i2*, complex8*);
typedef void   (CALLCONV_ORIG *DRD_o_t)(ftn_i4*, ftn_i4*, ftn_i4*, ftn_i4*, ftn_i4*, float*, ftn_i2*, complex8*);
typedef void   (CALLCONV_ORIG *REFL_o_t)(ftn_i2*, ftn_i2*, float*, float*, float*, float*, float*, float*, float*, float*, BOOL*, BOOL*);
typedef void   (CALLCONV_ORIG *YTWCore1_o_t)(
  float*, float*, float*, float*, float*, float*, ftn_i2*, ftn_i2*, ftn_i2*, float*, float*, ftn_i2*
);

typedef float  (CALLCONV_NEW *ATN4_n_t)(float*, float*);
typedef void   (CALLCONV_NEW  *ANGHORIZ_n_t)(float*, float*, float*);
typedef void   (CALLCONV_NEW  *ANGIN_n_t)(float*, float*, float*, float*, float*, float*, ftn_i4*);
typedef void   (CALLCONV_NEW  *YUTD_n_t)(float*, float*, float*, float*, float*, float*, float*);
typedef void   (CALLCONV_NEW  *WD_n_t)(complex8*, float*, float*, float*, float*, float*);
// New FFCT from gfortran returns complex directly on this toolchain
typedef complex8 (CALLCONV_NEW *FFCT_n_t)(float*);
typedef void   (CALLCONV_NEW  *FRESNEL_n_t)(float*, float*, float*, float*, float*);
typedef void   (CALLCONV_NEW  *DIFFDIFF_n_t)(ftn_i4*, ftn_i4*, ftn_i4*, ftn_i4*, ftn_i4*, float*, ftn_i2*, complex8*);
typedef void   (CALLCONV_NEW  *DRD_n_t)(ftn_i4*, ftn_i4*, ftn_i4*, ftn_i4*, ftn_i4*, float*, ftn_i2*, complex8*);
typedef void   (CALLCONV_NEW  *REFL_n_t)(ftn_i2*, ftn_i2*, float*, float*, float*, float*, float*, float*, float*, float*, BOOL*, BOOL*);
typedef void   (CALLCONV_NEW  *YTWCore1_n_t)(
  float*, float*, float*, float*, float*, float*, ftn_i2*, ftn_i2*, ftn_i2*, float*, float*, ftn_i2*
);

typedef struct {
  HMODULE      mod;
  ATN4_o_t     ATN4;
  ANGHORIZ_o_t ANGHORIZ;
  ANGIN_o_t    ANGIN;
  YUTD_o_t     YUTD;
  WD_o_t       WD;
  FFCT_o_sret_t FFCT;   // sret variant
  FRESNEL_o_t  FRESNEL;
  DIFFDIFF_o_t DIFFDIFF;
  DRD_o_t      DRD;
  REFL_o_t     REFL;
  YTWCore1_o_t YTWCore1;
} YTWFnsOrig;

typedef struct {
  HMODULE      mod;
  ATN4_n_t     ATN4;
  ANGHORIZ_n_t ANGHORIZ;
  ANGIN_n_t    ANGIN;
  YUTD_n_t     YUTD;
  WD_n_t       WD;
  FFCT_n_t     FFCT;    // direct return
  FRESNEL_n_t  FRESNEL;
  DIFFDIFF_n_t DIFFDIFF;
  DRD_n_t      DRD;
  REFL_n_t     REFL;
  YTWCore1_n_t YTWCore1;
} YTWFnsNew;

// Resolve helpers
static void* must_resolve_va(HMODULE mod, uintptr_t va, const char* name) {
  void* p = get_fn_by_disasm_va(mod, va);
  if (!p) {
    fprintf(stderr, "Failed to resolve (VA) %s at 0x%08lX\n", name, (unsigned long)va);
    ExitProcess(2);
  }
  return p;
}
static void* must_get_ptr(HMODULE mod, const char* name) {
  FARPROC p = GetProcAddress(mod, name);
  if (!p) {
    fprintf(stderr, "GetProcAddress failed for '%s' (error %lu)\n", name, GetLastError());
    ExitProcess(3);
  }
  return (void*)p;
}
static YTWFnsOrig load_original(const char* dll_path) {
  YTWFnsOrig f;
  memset(&f, 0, sizeof(f));
  f.mod = LoadLibraryA(dll_path);
  if (!f.mod) { fprintf(stderr, "LoadLibrary('%s') failed (%lu)\n", dll_path, GetLastError()); ExitProcess(1); }
  f.ATN4      = (ATN4_o_t)       must_resolve_va(f.mod, VA_ATN4,     "ATN4");
  f.ANGHORIZ  = (ANGHORIZ_o_t)   must_resolve_va(f.mod, VA_ANGHORIZ, "ANGHORIZ");
  f.ANGIN     = (ANGIN_o_t)      must_resolve_va(f.mod, VA_ANGIN,    "ANGIN");
  f.YUTD      = (YUTD_o_t)       must_resolve_va(f.mod, VA_YUTD,     "YUTD");
  f.WD        = (WD_o_t)         must_resolve_va(f.mod, VA_WD,       "WD");
  f.FFCT      = (FFCT_o_sret_t)  must_resolve_va(f.mod, VA_FFCT,     "FFCT");
  f.FRESNEL   = (FRESNEL_o_t)    must_resolve_va(f.mod, VA_FRESNEL,  "FRESNEL");
  f.DIFFDIFF  = (DIFFDIFF_o_t)   must_resolve_va(f.mod, VA_DIFFDIFF, "DIFFDIFF");
  f.DRD       = (DRD_o_t)        must_resolve_va(f.mod, VA_DRD,      "DRD");
  f.REFL      = (REFL_o_t)       must_resolve_va(f.mod, VA_REFL,     "REFL");
  f.YTWCore1  = (YTWCore1_o_t)   must_resolve_va(f.mod, VA_YTWCore1, "YTWCore1");
  return f;
}
static YTWFnsNew load_new(const char* dll_path) {
  YTWFnsNew f;
  memset(&f, 0, sizeof(f));
  f.mod = LoadLibraryA(dll_path);
  if (!f.mod) { fprintf(stderr, "LoadLibrary('%s') failed (%lu)\n", dll_path, GetLastError()); ExitProcess(1); }
  f.ATN4      = (ATN4_n_t)     must_get_ptr(f.mod, "ATN4");
  f.ANGHORIZ  = (ANGHORIZ_n_t) must_get_ptr(f.mod, "ANGHORIZ");
  f.ANGIN     = (ANGIN_n_t)    must_get_ptr(f.mod, "ANGIN");
  f.YUTD      = (YUTD_n_t)     must_get_ptr(f.mod, "YUTD");
  f.WD        = (WD_n_t)       must_get_ptr(f.mod, "WD");
  f.FFCT      = (FFCT_n_t)     must_get_ptr(f.mod, "FFCT");
  f.FRESNEL   = (FRESNEL_n_t)  must_get_ptr(f.mod, "FRESNEL");
  f.DIFFDIFF  = (DIFFDIFF_n_t) must_get_ptr(f.mod, "DIFFDIFF");
  f.DRD       = (DRD_n_t)      must_get_ptr(f.mod, "DRD");
  f.REFL      = (REFL_n_t)     must_get_ptr(f.mod, "REFL");
  f.YTWCore1  = (YTWCore1_n_t) must_get_ptr(f.mod, "YTWCore1");
  return f;
}

// Tolerances
typedef struct { float atol, rtol; } Tols;
static const Tols TOL_F = { 0.f, 1e-6f };
static const Tols TOL_F_INTEGRATION = { 0.2f, 0.f };
static const Tols TOL_C = { 0.f, 1e-6f };
static const Tols TOL_C_DIFFDIFF = { 0.f, 1e-2f };

static int nearly_equal(float a, float b, Tols t) {
  if (isnan(a) && isnan(b)) return 1;
  if (isinf(a) && isinf(b) && (a == b)) return 1;
  if (isinf(a) || isnan(a) || isinf(b) || isnan(b)) return 0;
  const float diff = fabsf(a - b);
  if (diff <= t.atol) return 1;
  return diff <= t.rtol * fmaxf(fabsf(a), fabsf(b));
}
static int complex_nearly_equal(complex8 a, complex8 b, Tols t) {
  return nearly_equal(a.r, b.r, t) && nearly_equal(a.i, b.i, t);
}

static void compare_float(const char* name, float a, float b, Tols t, int* mismatches) {
  if (!nearly_equal(a, b, t)) {
    printf("  [DIFF] %s: orig=%.8g new=%.8g\n", name, a, b);
    (*mismatches)++;
  }
}
static void compare_complex(const char* name, complex8 a, complex8 b, Tols t, int* mismatches) {
  if (!complex_nearly_equal(a, b, t)) {
    printf("  [DIFF] %s: orig=(%.8g,%.8g) new=(%.8g,%.8g)\n", name, a.r, a.i, b.r, b.i);
    (*mismatches)++;
  }
}

// Seed Fortran COMMONs so routines depending on them see identical state
static void seed_commons(YTWFnsOrig* o, YTWFnsNew* n, float freq, float soil2, float soil1) {
  float hant[YTW_N_ANT] = { 0.0f, 0.0f, 0.0f, 0.0f };
  ftn_i2 ant_phase[YTW_N_ANT] = {1,1,1,1};
  ftn_i2 ant_kind = 1;
  ftn_i2 diff_n = 0;
  ftn_i2 dbg_en = 0;
  float dbg_angle = 5.0f;

  float dist_o[YTW_N_DIST] = {0}, hasl_o[YTW_N_DIST] = {0};
  float dist_n[YTW_N_DIST] = {0}, hasl_n[YTW_N_DIST] = {0};
  float out_o[YTW_N_OUT] = {0};
  float out_n[YTW_N_OUT] = {0};

  o->YTWCore1(dist_o, hasl_o, hant, &freq, &soil2, &soil1,
              &ant_kind, &diff_n, &dbg_en, &dbg_angle, out_o, ant_phase);
  n->YTWCore1(dist_n, hasl_n, hant, &freq, &soil2, &soil1,
              &ant_kind, &diff_n, &dbg_en, &dbg_angle, out_n, ant_phase);
}

static void seed_commons_with_terrain(YTWFnsOrig* o, YTWFnsNew* n, 
                                      const float* dist_profile, const float* hasl_profile, int num_points) {
  float freq = 14.0f, soil2 = 13.0f, soil1 = 0.005f;
  float hant[YTW_N_ANT] = {0}, out[YTW_N_OUT] = {0};
  ftn_i2 ant_phase[YTW_N_ANT] = {1,1,1,1};
  ftn_i2 ant_kind = 1, diff_n = 0, dbg_en = 0;
  float dbg_angle = 0.0f;

  // Create temporary arrays to pass to the Fortran code
  float dist[YTW_N_DIST] = {0}, hasl[YTW_N_DIST] = {0};
  memcpy(dist, dist_profile, num_points * sizeof(float));
  memcpy(hasl, hasl_profile, num_points * sizeof(float));

  o->YTWCore1(dist, hasl, hant, &freq, &soil2, &soil1, &ant_kind, &diff_n, &dbg_en, &dbg_angle, out, ant_phase);
  n->YTWCore1(dist, hasl, hant, &freq, &soil2, &soil1, &ant_kind, &diff_n, &dbg_en, &dbg_angle, out, ant_phase);
}

// Test ATN4 on many quadrants and edge cases
static int test_ATN4(YTWFnsOrig* o, YTWFnsNew* n) {
  int mism = 0;
  struct { float x,y; const char* name; } cases[] = {
    // --- Existing test cases (excellent coverage of basic quadrants) ---
    {0.0f, 0.0f, "(0,0)"},
    {0.0f, 1.0f, "(0,1)"},       // PI/2
    {0.0f, -1.0f, "(0,-1)"},     // -PI/2
    {1.0f, 0.0f, "(1,0)"},       // 0
    {-1.0f, 0.0f, "(-1,0)"},     // PI or -PI
    {1.0f, 1.0f, "(1,1)"},       // PI/4
    {-1.0f, 1.0f, "(-1,1)"},     // 3*PI/4
    {-1.0f, -1.0f, "(-1,-1)"},   // -3*PI/4
    {1.0f, -1.0f, "(1,-1)"},     // -PI/4
    {1e-7f, 1.0f, "(~0,1)"},     // very close to PI/2
    {-1e-7f, 1.0f, "(-~0,1)"},   // very close to PI/2 from the other side
    {2.0f, 1e-7f, "(2,~0)"},     // very close to 0
    {-2.0f, 1e-7f, "(-2,~0)"},   // very close to PI

    // --- New test cases for stability and edge conditions ---

    // 1. Ratio of very large to very small numbers
    // Tests for potential overflow/underflow in the division y/x before ATAN is called.
    {1e20f, 1.0f, "(large,1)"},
    {1.0f, 1e20f, "(1,large)"},
    {-1e20f, 1.0f, "(-large,1)"},
    {1.0f, -1e20f, "(1,-large)"},

    // 2. Arguments near machine precision limits
    {FLT_MAX, 1.0f, "(FLT_MAX,1)"},
    {1.0f, FLT_MAX, "(1,FLT_MAX)"},
    {FLT_MIN, 1.0f, "(FLT_MIN,1)"}, // FLT_MIN is the smallest positive normalized number

    // 3. Arguments near zero from both sides
    // These are more extreme versions of your existing ~0 tests.
    {FLT_EPSILON, 1.0f, "(EPS,1)"},
    {-FLT_EPSILON, -1.0f, "(-EPS,-1)"},

    // 4. Test symmetry and quadrant boundaries explicitly
    // This pair should have a difference of PI/2
    {123.456f, 789.123f, "(x,y)"},
    {789.123f, -123.456f, "(y,-x)"},

    // 5. Large numbers on both axes
    // Checks that the ratio calculation remains stable.
    {1.23e30f, 4.56e30f, "(large,large)"},
    {-1.23e30f, 4.56e30f, "(-large,large)"}
  };
  for (unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
    float a1 = cases[i].x, a2 = cases[i].y;
    float ro = o->ATN4(&a1, &a2);
    float rn = n->ATN4(&a1, &a2);
    if (!nearly_equal(ro, rn, TOL_F)) {
      printf("ATN4%9s: orig=%.8g new=%.8g\n", cases[i].name, ro, rn);
      mism++;
    }
  }
  printf("ATN4: %s\n", mism ? "MISMATCHES" : "OK");
  return mism;
}

// Test ANGHORIZ with values on both branches
static int test_ANGHORIZ(YTWFnsOrig* o, YTWFnsNew* n) {
  int mism = 0;
  const float PI = (float)M_PI;
  float vals[] = {
    // --- Existing values (good for basic, near-zero checks) ---
    -1.2f, -0.5f, -1e-6f, 0.0f, 1e-6f, 0.5f, 1.2f,

    // --- New values to test numerical stability and edge cases ---

    // 1. Values at and around PI.
    // When combined, these will create catastrophic cancellation scenarios.
    // e.g., ANGHORIZ(0.5f, PI+0.5f - 1e-6f) will test subtraction of nearly-equal numbers.
    PI,
    PI - 1e-6f,
    PI + 1e-6f,
    -PI,
    -PI + 1e-6f,

    // 2. Values at and around PI/2.
    // These are common angles in geometry and good to have for coverage.
    PI / 2.0f,
    PI / 2.0f - 1e-6f,
    -PI / 2.0f,
    -PI / 2.0f + 1e-6f,

    // 3. A large value.
    // Tests behavior with inputs that might be outside the typical [-2PI, 2PI] range.
    100.0f,

    // 4. A very small (but not near-zero) positive value.
    // Tests for issues when one value is tiny compared to others.
    1e-5f
  };
  for (unsigned i=0;i<sizeof(vals)/sizeof(vals[0]);++i) {
    for (unsigned j=0;j<sizeof(vals)/sizeof(vals[0]);++j) {
      float a1 = vals[i], a2 = vals[j];
      float ao=0, an=0;
      o->ANGHORIZ(&a1, &a2, &ao);
      n->ANGHORIZ(&a1, &a2, &an);
      if (!nearly_equal(ao, an, TOL_F)) {
        printf("ANGHORIZ(a1=%.6g,a2=%.6g): orig=%.8g new=%.8g\n", a1, a2, ao, an);
        mism++;
      }
    }
  }
  printf("ANGHORIZ: %s\n", mism ? "MISMATCHES" : "OK");
  return mism;
}

// Test ANGIN exercising branches (a1<0 vs >=0, a2>a1 vs else)
static int test_ANGIN(YTWFnsOrig* o, YTWFnsNew* n) {
  int mism = 0;
  const float PI = (float)M_PI;
  const float TWO_PI = 2.0f * PI;
  // --- Base values for a1 (angle of the preceding terrain segment) ---
  float a1s[] = {
    // Existing values
    -1.0f, -0.3f, 0.0f, 0.25f, 1.0f,
    // New values
    -1e-7f, 1e-7f,        // Values extremely close to zero to test the main branch
    PI - 1e-6f, -PI + 1e-6f, // Values near PI
    0.8f                   // Added a value to test a2 > a1 vs a2 < a1
  };
  // --- Base values for a2 (angle of the succeeding terrain segment) ---
  float a2s[] = {
    // Existing values
    -0.5f, 0.1f, 0.8f,
    // New values
    -1e-7f, 1e-7f,        // Values extremely close to zero
    PI, -PI,              // Values on PI boundary
    0.8f + 1e-6f,         // Value just slightly larger than a1=0.8
    0.8f - 1e-6f          // Value just slightly smaller than a1=0.8
  };
  // --- Base values for a3 (angle of the incident ray) ---
  float a3s[] = {
    // Existing values
    -0.8f, 0.0f, 0.7f,
    // New values
    PI / 2.0f, -PI / 2.0f,  // Cardinal directions
    PI - 1e-6f,           // Near PI
    TWO_PI - 1e-6f        // Near TWO_PI
  };
  for (unsigned i=0;i<sizeof(a1s)/sizeof(a1s[0]);++i)
  for (unsigned j=0;j<sizeof(a2s)/sizeof(a2s[0]);++j)
  for (unsigned k=0;k<sizeof(a3s)/sizeof(a3s[0]);++k) {
    float a1=a1s[i], a2=a2s[j], a3=a3s[k];
    float a4o=0, a5o=0, a6o=0; ftn_i4 a7o=0;
    float a4n=0, a5n=0, a6n=0; ftn_i4 a7n=0;
    o->ANGIN(&a1,&a2,&a3,&a4o,&a5o,&a6o,&a7o);
    n->ANGIN(&a1,&a2,&a3,&a4n,&a5n,&a6n,&a7n);
    compare_float("ANGIN.a4", a4o, a4n, TOL_F, &mism);
    compare_float("ANGIN.a5", a5o, a5n, TOL_F, &mism);
    compare_float("ANGIN.a6", a6o, a6n, TOL_F, &mism);
    if (a7o != a7n) {
      printf("  [DIFF] ANGIN.a7: orig=%d new=%d (a1=%.4g a2=%.4g a3=%.4g)\n", (int)a7o, (int)a7n, a1, a2, a3);
      mism++;
    }
  }
  printf("ANGIN: %s\n", mism ? "MISMATCHES" : "OK");
  return mism;
}

// Test FFCT across ranges and boundaries (including negative mirrored branch)
// - original called via sret pointer; new returns directly
static int test_FFCT(YTWFnsOrig* o, YTWFnsNew* n) {
  int mism = 0;
  float xs[] = {
    // --- Existing test cases (good for probing boundaries) ---
    -6.0f, -5.5f, -5.49f, -1.0f, -0.3f, -0.299f, 0.0f, 0.1f, 0.3f, 0.301f, 1.0f, 5.49f, 5.5f, 5.51f, 6.0f,

    // --- New test cases for numerical stability ---

    // 1. Extremely small POSITIVE values.
    // These test the small-argument approximation (sqrt(x) term) where it's most sensitive to precision loss.
    // This is physically plausible when a ray is almost perfectly on a shadow/reflection boundary.
    // The value 1.3e-10f is taken from the pathological case discovered during WD debugging.
    1.3085799e-10f, // From the pathological case in WD
    1e-7f,          // A very small value
    1e-20f,         // A value near the limit of single-precision float

    // 2. Extremely small NEGATIVE values.
    // Tests the same logic as above, but also verifies the final complex conjugation step.
    -1e-7f,
    -1e-20f,

    // 3. Extremely large POSITIVE values.
    // These test the asymptotic approximation for large arguments, where F(X) should approach 1.
    100.0f,
    10000.0f,

    // 4. Extremely large NEGATIVE values.
    // Tests the asymptotic approximation combined with the conjugation.
    -100.0f,
    -10000.0f,

    // 5. Values exactly ON the interpolation table knots.
    // This can catch off-by-one or boundary condition errors in the interpolation loop.
    // (Values are from the Fortran source: 0.5, 2.3)
    0.5f,
    2.3f
  };
  for (unsigned i=0;i<sizeof(xs)/sizeof(xs[0]);++i) {
    float x = xs[i];
    complex8 co={0}, cn={0};
    o->FFCT(&co, &x);      // sret call
    cn = n->FFCT(&x);      // direct return
    if (!complex_nearly_equal(co, cn, TOL_C)) {
      printf("FFCT(%.4g): orig=(%.8g,%.8g) new=(%.8g,%.8g)\n", x, co.r, co.i, cn.r, cn.i);
      mism++;
    }
  }
  printf("FFCT: %s\n", mism ? "MISMATCHES" : "OK");
  return mism;
}

// Test WD with cases that cover both main branches and special-case path
static int test_WD(YTWFnsOrig* o, YTWFnsNew* n) {
  int mism = 0;
  const float PI = (float)M_PI;
  struct { float a2,a3,a4,a5,a6; const char* name; } cases[] = {
    // --- Basic Test Cases ---
    // a6 <= 0.5 -> all zeros expected
    {1.0f, 0.3f, 0.2f, 1.0f, 0.49f, "low-a6-zero"},
    // a6 > 0.5 typical case
    {1.0f, 0.5f, 0.1f, 1.0f, 1.0f, "typical"},
    // Force FLOAT_10011f24 ~ 0 via a2=0 (so FLOAT_10011f48=0)
    {0.0f, 0.7f, 0.2f, 1.0f, 1.2f, "a2-zero-special"},
    // The original pathological case that exposed the precision bug.
    {38.4297752f, 3.32071829f, 0.248937070f, 1.0f, 1.06812835f, "pathological-1"},

    // --- New Test Cases for Numerical Instability ---

    // Test 1: Shadow Boundary (phi ~ pi + phi')
    // The term beta = phi - phi' approaches pi. This causes the cot( (pi - beta) / 2n ) term in the UTD
    // formula to approach its pole, testing the transition function's ability to handle the singularity.
    {50.0f, PI + 0.2f + 1e-6f, 0.2f, 1.0f, 1.5f, "shadow-boundary-1"},

    // Test 2: Reflection Boundary (phi ~ pi - phi')
    // The term beta = phi + phi' approaches pi. This tests the singularity handling for the other
    // pair of cotangent terms in the formula.
    {50.0f, PI - 0.2f - 1e-6f, 0.2f, 1.0f, 1.5f, "reflection-boundary-1"},

    // Test 3: Grazing Incidence (phi' -> 0)
    // The incoming ray is nearly parallel to the wedge face. This is an important edge case.
    {200.0f, 0.5f, 1e-7f, 1.0f, 1.9f, "grazing-incidence-phi-prime"},

    // Test 4: Grazing Observation (phi -> 0)
    // The observer is located in a direction nearly parallel to the wedge face.
    {200.0f, 1e-7f, 0.5f, 1.0f, 1.9f, "grazing-observation-phi"},

    // Test 5: Source and Observer on Opposite Faces (phi+phi' ~ 2*n*pi - pi)
    // This case tests one of the other cotangent poles, which depends on the wedge parameter 'n'.
    // For n=1.8, a pole exists near beta = (phi+phi') = 2.6*pi.
    {100.0f, 1.8f * PI - 0.3f, 1.3f * PI + 0.3f + 1e-6f, 1.0f, 1.8f, "opposite-face-boundary"},

    // Test 6: Half-Plane Case (n = 2.0) near a Shadow Boundary
    // The half-plane is a canonical case in diffraction theory. n=2.0 represents a "knife-edge".
    {150.0f, PI + 0.1f + 1e-6f, 0.1f, 1.0f, 2.0f, "half-plane-shadow-boundary"},

    // Test 7: Very Sharp Terrain Peak (n is close to 2.0) with a small diffraction angle.
    // This stresses the calculations with large 'n' values.
    {300.0f, PI + 0.05f + 1e-7f, 0.05f, 1.0f, 1.99f, "sharp-peak-small-diff"},

    // Test 8: Very Smooth Hill (n is close to 1.0, almost a flat surface).
    // This tests stability with small 'n' values, where the 2n denominator approaches 2.
    {80.0f, PI - 0.1f - 1e-6f, 0.1f, 1.0f, 1.01f, "smooth-hill-refl-boundary"},

    // Test 9: Very Small Distance Parameter L.
    // This forces the argument X of the FFCT function to be very small, directly testing
    // the logic in the `else` block of WD and the small-argument approximation in FFCT.
    {0.01f, 1.5f, 1.0f, 1.0f, 1.7f, "small-L-parameter"},

    // Test 10: Very Large Distance Parameter L.
    // This tests the asymptotic path of FFCT, where F(X) should approach 1.0. This ensures
    // that the UTD formula correctly simplifies to the simpler GTD formula far from boundaries.
    {50000.0f, 1.5f, 1.0f, 1.0f, 1.6f, "large-L-parameter"},

    // Test 11: Combined Stress Case.
    // A "malicious" test combining a sharp peak with grazing incidence on one face and
    // near-boundary observation on the other, to check for unexpected compound errors.
    {250.0f, 1e-6f, 1.95f * PI - 1e-6f, 1.0f, 1.95f, "combined-stress-case"}
  };
  for (unsigned c=0;c<sizeof(cases)/sizeof(cases[0]);++c) {
    complex8 ao[4]={{0}}, an[4]={{0}};
    float a2=cases[c].a2, a3=cases[c].a3, a4=cases[c].a4, a5=cases[c].a5, a6=cases[c].a6;
    o->WD(ao, &a2,&a3,&a4,&a5,&a6);
    n->WD(an, &a2,&a3,&a4,&a5,&a6);
    for (int i=0;i<4;++i) {
      char lbl[64]; _snprintf(lbl,sizeof(lbl),"WD[%s].a1[%d]", cases[c].name, i+1);
      compare_complex(lbl, ao[i], an[i], TOL_C, &mism);
    }
  }
  printf("WD: %s\n", mism ? "MISMATCHES" : "OK");
  return mism;
}

// Test YUTD with parameter sets (including a3<=10deg path)
static int test_YUTD(YTWFnsOrig* o, YTWFnsNew* n) {
  int mism = 0;
  const float PI = (float)M_PI;
  struct { float a1,a2,a3,a4,a5; const char* name; } cases[] = {
    // --- Existing Basic Test Cases ---
    {14.0f, 0.25f,       0.0f, 45.0f*PI/180.0f,  20.0f*PI/180.0f, "a3=0deg-halves"},
    {14.0f, 0.25f,       15.0f*PI/180.0f, 45.0f*PI/180.0f,  25.0f*PI/180.0f, "typical-1"},
    {7.0f,  0.75f,       12.0f*PI/180.0f, 20.0f*PI/180.0f, -10.0f*PI/180.0f, "typical-2"},
    {10.1f, 38.4297752f, 0.24893707f,     2.92756128f,       3.32071829f,    "pathological-1"},

    // --- New Test Cases for Numerical Instability ---

    // Test 1: Shadow Boundary. phi is very close to pi + phi'. This is a primary UTD transition region.
    // (freq=14MHz, L=100ft, wedge_angle=36deg, phi'=30deg)
    {14.0f, 100.0f, 30.0f*PI/180.f, (2.0f-0.2f)*PI, PI + 30.0f*PI/180.f + 1e-6f, "shadow-boundary-close"},

    // Test 2: Reflection Boundary. phi is very close to pi - phi'. The other primary UTD transition region.
    // (freq=14MHz, L=100ft, wedge_angle=36deg, phi'=30deg)
    {14.0f, 100.0f, 30.0f*PI/180.f, (2.0f-0.2f)*PI, PI - 30.0f*PI/180.f - 1e-6f, "reflection-boundary-close"},

    // Test 3: Grazing Incidence. The incoming ray is almost parallel to the wedge face (phi' -> 0).
    // (freq=28MHz, L=500ft, wedge_angle=9deg, phi'=0.001deg)
    {28.0f, 500.0f, 0.001f*PI/180.f, (2.0f-0.05f)*PI, 90.0f*PI/180.f, "grazing-incidence"},

    // Test 4: Grazing Observation. The outgoing ray is almost parallel to the wedge face (phi -> 0).
    // (freq=28MHz, L=500ft, wedge_angle=9deg, phi=0.001deg)
    {28.0f, 500.0f, 90.0f*PI/180.f, (2.0f-0.05f)*PI, 0.001f*PI/180.f, "grazing-observation"},

    // Test 5: Knife-Edge (Half-Plane) Case. A canonical case where n=2.0 (internal angle = 0).
    // We test it near the reflection boundary.
    {7.0f, 200.0f, 45.0f*PI/180.f, 2.0f*PI, PI - 45.0f*PI/180.f - 1e-6f, "knife-edge-boundary"},

    // Test 6: Almost Flat Ground Case. n is very close to 1.0 (internal angle ~ 180 deg).
    // This tests for numerical issues when n is small.
    {3.5f, 100.0f, 10.0f*PI/180.f, 1.001f*PI, 20.0f*PI/180.f, "almost-flat-ground"},

    // Test 7: Low Frequency, Short Distance. Forces a very small argument 'X' for FFCT.
    // This directly tests the small-argument approximation path that caused the original bug.
    {3.5f, 1.0f, 70.0f*PI/180.f, 1.5f*PI, 120.0f*PI/180.f, "low-freq-short-dist"},

    // Test 8: High Frequency, Large Distance. Forces a large argument 'X' for FFCT.
    // This tests the asymptotic behavior where F(X) should approach 1.
    {29.0f, 20000.0f, 60.0f*PI/180.f, 1.8f*PI, 150.0f*PI/180.f, "high-freq-large-dist"},

    // Test 9: Plus-Term Boundary. Tests one of the other two UTD terms involving (phi + phi').
    // Here, phi + phi' approaches pi.
    {21.0f, 300.0f, 60.0f*PI/180.f, 1.7f*PI, PI - 60.0f*PI/180.f - 1e-6f, "plus-term-boundary"},

    // Test 10: Pathological Case 2. Engineered to have an argument to TAN() be very close to a pole,
    // similar to the original bug but with different parameters.
    {18.0f, 150.0f, 0.1f*PI, 1.1f*PI, 1.3f*PI + 1e-6f, "pathological-2-engineered"},

    // Test 11: Combined Stress Case. A "malicious" test combining a sharp peak (n~2)
    // with grazing incidence to see if the combination breaks the logic.
    {24.0f, 400.0f, 1e-7f, 1.98f*PI, 170.0f*PI/180.f, "combined-stress"}
  };
  for (unsigned c=0;c<sizeof(cases)/sizeof(cases[0]);++c) {
    float a1=cases[c].a1, a2=cases[c].a2, a3=cases[c].a3, a4=cases[c].a4, a5=cases[c].a5;
    float a6o=0, a7o=0, a6n=0, a7n=0;
    o->YUTD(&a1,&a2,&a3,&a4,&a5,&a6o,&a7o);
    n->YUTD(&a1,&a2,&a3,&a4,&a5,&a6n,&a7n);
    char l1[64], l2[64];
    _snprintf(l1,sizeof(l1),"YUTD[%s].a6",cases[c].name);
    _snprintf(l2,sizeof(l2),"YUTD[%s].a7",cases[c].name);
    compare_float(l1, a6o, a6n, TOL_F, &mism);
    compare_float(l2, a7o, a7n, TOL_F, &mism);
  }
  printf("YUTD: %s\n", mism ? "MISMATCHES" : "OK");
  return mism;
}

// Test FRESNEL
static int test_FRESNEL(YTWFnsOrig* o, YTWFnsNew* n) {
  int mism = 0;
  const float PI = (float)M_PI;
  const float TWO_PI = 2.0f * PI;

  // Structure to hold environmental parameters for seeding the common blocks
  struct { float freq; float soil2; float soil1; const char* name; } env_cases[] = {
    // 1. Average Ground, Mid-Band (Your baseline case)
    {14.0f, 13.0f, 0.005f, "AvgGround-MidBand"},
    // 2. Poor Ground, Low-Band (e.g., rocky soil on 80m)
    {3.5f, 4.0f, 0.001f, "PoorGround-LowBand"},
    // 3. Good Ground, High-Band (e.g., rich pasture on 10m)
    {28.0f, 20.0f, 0.030f, "GoodGround-HighBand"},
    // 4. Seawater Reflection (extreme case, high loss and high permittivity)
    {21.0f, 81.0f, 5.0f, "Seawater-HighBand"}
  };

  // --- Test values for a1 (grazing angle of incidence, in radians) ---
  float a1s[] = {
    // Existing values
    -0.9f, -0.3f, 0.0f, 0.4f, 0.9f,
    // New values
    1e-7f, -1e-7f,             // Extremely close to grazing incidence (0 degrees)
    PI/2.0f - 1e-6f,          // Near perpendicular incidence (90 degrees)
    -PI/2.0f + 1e-6f,         // Near perpendicular from the other side
    0.2f,                     // A typical low angle (~11.5 degrees), near Brewster's angle for average soil
    PI/4.0f                   // 45 degrees
  };

  // --- Test values for a3 (initial phase of the ray) ---
  float a3s[] = {0.0f, 0.25f, 1.0f, 3.0f, PI, TWO_PI}; // Added PI and 2*PI

  float a2 = 1.0f; // a2 is the incident magnitude, keep it at 1.0 for simplicity

  // Outer loop iterates through different environments
  for (unsigned e=0; e<sizeof(env_cases)/sizeof(env_cases[0]); ++e) {
    // Seed the common blocks with the current environment's parameters
    seed_commons(o, n, env_cases[e].freq, env_cases[e].soil2, env_cases[e].soil1);

    // Inner loops iterate through geometric test cases
    for (unsigned i=0; i<sizeof(a1s)/sizeof(a1s[0]); ++i) {
      for (unsigned j=0; j<sizeof(a3s)/sizeof(a3s[0]); ++j) {
        float a1=a1s[i], a3=a3s[j];
        float a4o=0, a5o=0, a4n=0, a5n=0;
        o->FRESNEL(&a1, &a2, &a3, &a4o, &a5o);
        n->FRESNEL(&a1, &a2, &a3, &a4n, &a5n);

        // Create a detailed label for error messages
        char lbl4[128], lbl5[128];
        _snprintf(lbl4, sizeof(lbl4), "FRESNEL[%s].a4(a1=%.3g,a3=%.3g)", env_cases[e].name, a1, a3);
        _snprintf(lbl5, sizeof(lbl5), "FRESNEL[%s].a5(a1=%.3g,a3=%.3g)", env_cases[e].name, a1, a3);

        compare_float(lbl4, a4o, a4n, TOL_F, &mism);
        compare_float(lbl5, a5o, a5n, TOL_F, &mism);
      }
    }
  }

  printf("FRESNEL: %s\n", mism ? "MISMATCHES" : "OK");
  return mism;
}

// Test REFL
static int test_REFL(YTWFnsOrig* o, YTWFnsNew* n) {
  int mism = 0;
  const float PI = (float)M_PI;

  // --- Define a set of diverse terrain profiles ---
  const float dist_flat[] = {0, 100000.f};
  const float hasl_flat[] = {0, 0};

  const float dist_hill[] = {0, 2000.f, 3000.f, 4000.f, 100000.f};
  const float hasl_hill[] = {0, 0,    100.f,  0,    0};

  const float dist_valley[] = {0, 1000.f, 3000.f, 5000.f, 100000.f};
  const float hasl_valley[] = {0, 100.f,  0,    100.f,  100.f};

  struct { const char* name; const float* dist; const float* hasl; int n_pts; } terrains[] = {
      {"FlatGround", dist_flat, hasl_flat, 2},
      {"SingleHill", dist_hill, hasl_hill, 5},
      {"Valley",     dist_valley, hasl_valley, 5}
  };

  // --- Define Geometric Test Cases for the Ray ---
  // The goal is to create diverse scenarios to check for any divergence
  // between the original and new implementations.
  struct { const char* name; ftn_i2 a1, a2; float a3; float a4; } cases[] = {
    {"Straight Path",       1, 2, 0.0f,               10.f},
    {"Downward Reflecting", 1, 2, -1.0f*PI/180.f,     10.f},
    {"Upward Path",         1, 2, 1.0f*PI/180.f,      10.f},
    {"Blocked Path",        1, 4, 2.0f*PI/180.f,      10.f},
    {"Grazing Path",        1, 3, 2.8624f*PI/180.f,   10.f},
    {"High Clear Path",     1, 4, 5.0f*PI/180.f,      10.f},
    {"Multi-Reflection",    2, 4, 0.0f,               0.f},
    {"Steep Downward",      1, 4, -15.0f*PI/180.f,    100.f}
  };

  // Outer loop iterates through terrain profiles
  for (unsigned t=0; t<sizeof(terrains)/sizeof(terrains[0]); ++t) {
    seed_commons_with_terrain(o, n, terrains[t].dist, terrains[t].hasl, terrains[t].n_pts);

    // Inner loop iterates through geometric ray tests
    for (unsigned c=0; c<sizeof(cases)/sizeof(cases[0]); ++c) {
      // Skip tests that don't make sense for the current terrain
      if (cases[c].a2 > terrains[t].n_pts) continue;

      ftn_i2 a1=cases[c].a1, a2=cases[c].a2;
      float a3=cases[c].a3, a4=cases[c].a4, a5=0.f; // a5 is phase, unused in logic

      float a6o=0,a7o=0,a8o=0,a9o=0,a10o=0;
      float a6n=0,a7n=0,a8n=0,a9n=0,a10n=0;
      BOOL b11o=FALSE,b12o=FALSE, b11n=FALSE,b12n=FALSE;

      o->REFL(&a1,&a2,&a3,&a4,&a5,&a6o,&a7o,&a8o,&a9o,&a10o,&b11o,&b12o);
      n->REFL(&a1,&a2,&a3,&a4,&a5,&a6n,&a7n,&a8n,&a9n,&a10n,&b11n,&b12n);

      char lbl_base[128];
      _snprintf(lbl_base, sizeof(lbl_base), "REFL[%s][%s]", terrains[t].name, cases[c].name);

      // The primary test: do the new and original implementations agree?
      if (b11o!=b11n || b12o!=b12n) {
        printf("  [DIFF] %s.flags: madeOut orig=%d new=%d, madeHit orig=%d new=%d\n",
          lbl_base, (int)b11o,(int)b11n, (int)b12o,(int)b12n);
        mism++;
      }

      // Compare floating point values only if the path was not completely blocked
      if (b11o || b11n) {
          char lbl[160];
          _snprintf(lbl, sizeof(lbl), "%s.a6", lbl_base);
          compare_float(lbl, a6o, a6n, TOL_F, &mism);
          _snprintf(lbl, sizeof(lbl), "%s.a9", lbl_base);
          compare_float(lbl, a9o, a9n, TOL_F, &mism);
          _snprintf(lbl, sizeof(lbl), "%s.a8", lbl_base);
          compare_float(lbl, a8o, a8n, TOL_F, &mism);
      }
    }
  }
  printf("REFL: %s\n", mism ? "MISMATCHES" : "OK");
  return mism;
}

// Read memory from original module at absolute VA (rebasing-safe), no SEH, using VirtualQuery
static int is_readable_prot(DWORD prot) {
  DWORD p = prot & 0xFF;
  return p == PAGE_READONLY || p == PAGE_READWRITE || p == PAGE_WRITECOPY ||
         p == PAGE_EXECUTE_READ || p == PAGE_EXECUTE_READWRITE || p == PAGE_EXECUTE_WRITECOPY;
}
static int read_abs_from_orig(YTWFnsOrig* o, uintptr_t abs_va, void* out, size_t size) {
  uintptr_t base = (uintptr_t)o->mod;
  uintptr_t off  = abs_va - (uintptr_t)0x10000000u;
  uintptr_t addr = base + off;
  MEMORY_BASIC_INFORMATION mbi;
  SIZE_T q = VirtualQuery((LPCVOID)addr, &mbi, sizeof(mbi));
  if (!q) return 0;
  if (mbi.State != MEM_COMMIT || (mbi.Protect & PAGE_GUARD) || !is_readable_prot(mbi.Protect))
    return 0;
  uintptr_t region_end = (uintptr_t)mbi.BaseAddress + (uintptr_t)mbi.RegionSize;
  if (addr + size > region_end) return 0;
  memcpy(out, (const void*)addr, size);
  return 1;
}
static int read_from_orig_i32(YTWFnsOrig* o, uintptr_t abs_va, int32_t* out) {
  return read_abs_from_orig(o, abs_va, out, sizeof(*out));
}
static int read_from_orig_i16(YTWFnsOrig* o, uintptr_t abs_va, int16_t* out) {
  return read_abs_from_orig(o, abs_va, out, sizeof(*out));
}

// “Real” DIFFDIFF & DRD using parameters read from the original DLL’s data
static int test_DIFFDIFF_DRD(YTWFnsOrig* o, YTWFnsNew* n) {
  // Addresses deduced from original variable names:
  const uintptr_t VA_INT_100121e0  = 0x100121e0u; // int32_t
  const uintptr_t VA_SHORT_10012238= 0x10012238u; // int16_t (count of diffraction pts)
  const uintptr_t VA_INT_100121dc  = 0x100121dcu; // int32_t (number of antenna paths)

  int32_t int_e0 = 0, int_dc = 0;
  int16_t short_238 = 0;
  if (!read_from_orig_i32(o, VA_INT_100121e0, &int_e0) ||
      !read_from_orig_i16(o, VA_SHORT_10012238, &short_238) ||
      !read_from_orig_i32(o, VA_INT_100121dc, &int_dc)) {
    fprintf(stderr, "DIFFDIFF/DRD: could not read control parameters from original\n");
    exit(3);
  }

  // Sanity and clamping
  ftn_i4 a1 = int_e0;                      // end index
  ftn_i4 a2 = (ftn_i4)(uint16_t)short_238; // number of diffraction points (zero-extend)
  ftn_i4 a3 = int_dc;                      // antenna path count
  if (a1 < 1 || a1 > 200 || a2 < 0 || a2 > 200 || a3 < 0 || a3 > 4) {
    fprintf(stderr, "DIFFDIFF/DRD: parameters out of expected range (a1=%d,a2=%d,a3=%d)\n", (int)a1,(int)a2,(int)a3);
    exit(3);
  }

  ftn_i4 dbg = 0, dbg_aux = 0;
  float  dbg_exit = 0.0f;
  ftn_i2 ant_phase[YTW_N_ANT] = {1,1,1,1};

  complex8 out_o[YTW_N_COMPLEX]; memset(out_o, 0, sizeof(out_o));
  complex8 out_n[YTW_N_COMPLEX]; memset(out_n, 0, sizeof(out_n));

  printf("DIFFDIFF/DRD: using a1=%d, a2=%d, a3=%d\n", (int)a1,(int)a2,(int)a3);

  // DIFFDIFF
  int mism = 0, local = 0;
  o->DIFFDIFF(&a1,&a2,&a3,&dbg,&dbg_aux,&dbg_exit, ant_phase, out_o);
  n->DIFFDIFF(&a1,&a2,&a3,&dbg,&dbg_aux,&dbg_exit, ant_phase, out_n);
  for (int i=0;i<YTW_N_COMPLEX;i++) {
    char lbl[64]; _snprintf(lbl,sizeof(lbl),"DIFFDIFF.a8[%d]", i);
    compare_complex(lbl, out_o[i], out_n[i], TOL_C_DIFFDIFF, &local);
  }
  mism += local;
  printf("DIFFDIFF: %s (%d sampled diffs)\n", local ? "MISMATCHES" : "OK", local);

  // DRD
  memset(out_o, 0, sizeof(out_o));
  memset(out_n, 0, sizeof(out_n));
  local = 0;
  o->DRD(&a1,&a2,&a3,&dbg,&dbg_aux,&dbg_exit, ant_phase, out_o);
  n->DRD(&a1,&a2,&a3,&dbg,&dbg_aux,&dbg_exit, ant_phase, out_n);
  for (int i=0;i<YTW_N_COMPLEX;i++) {
    char lbl[64]; _snprintf(lbl,sizeof(lbl),"DRD.a8[%d]", i);
    compare_complex(lbl, out_o[i], out_n[i], TOL_C_DIFFDIFF, &local);
  }
  mism += local;
  printf("DRD: %s (%d sampled diffs)\n", local ? "MISMATCHES" : "OK", local);

  return mism;
}

static int test_DIFFDIFF_DRD_harness(YTWFnsOrig* o, YTWFnsNew* n) {
  int total_mismatches = 0;

  // --- Define a diverse set of 10+ challenging terrain profiles ---
  // Each profile is an array of {distance, height} pairs.

  // 1. Double Hill: Creates many D-D paths.
  const float dist_dhill[] = {0, 2000, 3000, 4000, 6000, 7000, 8000, 100000};
  const float hasl_dhill[] = {0, 0,    100,  0,    0,    120,  0,    0};

  // 2. Deep Valley: Ideal for D-R-D paths.
  const float dist_valley[] = {0, 1000, 4000, 5000, 100000};
  const float hasl_valley[] = {0, 150,  0,    150,  150};

  // 3. Jagged Peaks: Generates a large number of diffraction points.
  const float dist_jagged[] = {0, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 100000};
  const float hasl_jagged[] = {0, 0,    50,   20,   60,   30,   70,   40,   80,   80};

  // 4. Coastal Cliff: A sharp drop-off to a low plain (or sea level).
  const float dist_cliff[] = {0, 1000, 1001, 100000};
  const float hasl_cliff[] = {0, 200,  0,    0};

  // 5. Stepped Terrain / Terraces: Multiple parallel edges.
  const float dist_steps[] = {0, 1000, 2000, 2001, 3000, 3001, 100000};
  const float hasl_steps[] = {0, 0,    100,  100,  200,  200,  200};

  // 6. Bowl: A concave profile, excellent for trapping rays and multiple reflections.
  const float dist_bowl[] = {0, 1000, 2000, 3000, 4000, 5000, 100000};
  const float hasl_bowl[] = {0, 200,  50,   0,    50,   200,  200};

  // 7. Obstructed Valley ("Keyhole"): A hill in front of a valley.
  const float dist_keyhole[] = {0, 1000, 1500, 2000, 4000, 5000, 6000, 100000};
  const float hasl_keyhole[] = {0, 0,    80,   0,    150,  50,   150,  150};

  // 8. Single, very sharp peak: Focuses on diffraction from a single dominant feature.
  const float dist_peak[] = {0, 4999, 5000, 5001, 100000};
  const float hasl_peak[] = {0, 0,    300,  0,    0};

  // 9. Ramp Up: A long, continuous slope.
  const float dist_ramp[] = {0, 10000, 100000};
  const float hasl_ramp[] = {0, 500,   500};

  // 10. Flat ground with a small obstruction: Tests sensitivity.
  const float dist_bump[] = {0, 4000, 4010, 4020, 100000};
  const float hasl_bump[] = {0, 0,    5,    0,    0};

  // 11. Your original profile that caused the bug, for regression testing.
  // (Using a simplified representation here)
  const float dist_pr1t[] = {0, 1000, 2000, 2500, 3000, 4000, 5000, 100000};
  const float hasl_pr1t[] = {0, 50,   150,  120,  250,  180,  190,  190};

  struct { const float* dist; const float* hasl; int n_pts; const char* name; } terrains[] = {
      {dist_dhill,   hasl_dhill,   8, "DoubleHill"},
      {dist_valley,  hasl_valley,  5, "DeepValley"},
      {dist_jagged,  hasl_jagged, 10, "JaggedPeaks"},
      {dist_cliff,   hasl_cliff,   4, "CoastalCliff"},
      {dist_steps,   hasl_steps,   7, "SteppedTerrain"},
      {dist_bowl,    hasl_bowl,    7, "Bowl"},
      {dist_keyhole, hasl_keyhole, 8, "ObstructedValley"},
      {dist_peak,    hasl_peak,    5, "SharpPeak"},
      {dist_ramp,    hasl_ramp,    3, "RampUp"},
      {dist_bump,    hasl_bump,    5, "SmallBump"},
      {dist_pr1t,    hasl_pr1t,    8, "Regression-PR1T"}
  };

  // Loop through each terrain, seed the commons, and run the DIFFDIFF/DRD test.
  for (unsigned t=0; t<sizeof(terrains)/sizeof(terrains[0]); ++t) {
    printf("\n--- Testing Terrain Profile: %s ---\n", terrains[t].name);
    seed_commons_with_terrain(o, n, terrains[t].dist, terrains[t].hasl, terrains[t].n_pts);
    total_mismatches += test_DIFFDIFF_DRD(o, n);
  }

  printf("\n============================================\n");
  printf("DIFFDIFF/DRD HARNESS COMPLETE: %s\n", total_mismatches ? "MISMATCHES FOUND" : "ALL OK");
  printf("============================================\n\n");
  return total_mismatches;
}

// Helper: load .PRO profile
static void trim_line(char* s) {
  char* p = s;
  while (*p && isspace((unsigned char)*p)) p++;
  size_t len = strlen(p);
  while (len > 0 && isspace((unsigned char)p[len-1])) len--;
  memmove(s, p, len);
  s[len] = '\0';
}
static int load_profile_from_PRO(const char* filename, float dist[], float hasl[]) {
  FILE* f = fopen(filename, "r");
  if (!f) {
    perror("YTWCore1: could not open profile");
    return 0;
  }
  // Initialize arrays and load entries starting at index 1
  memset(dist, 0, sizeof(float)*YTW_N_DIST);
  memset(hasl, 0, sizeof(float)*YTW_N_DIST);
  int i = 1;
  float fac = 1.0f;
  char buf[256];
  while (fgets(buf, sizeof(buf), f)) {
    trim_line(buf);
    if (!buf[0]) continue;
    if (strcmp(buf, "meters") == 0) {
      fac = 3.281f; // convert meters to feet
      continue;
    }
    float d=0.0f, h=0.0f;
    if (sscanf(buf, "%f %f", &d, &h) == 2) {
      if (i >= YTW_N_DIST) break;
      dist[i] = d * fac;
      hasl[i] = h * fac;
      i++;
    }
  }
  fclose(f);
  // Terminator zero already ensured by initial memset; explicitly keep a zero after last used
  if (i < YTW_N_DIST) {
    dist[i] = 0.0f;
    hasl[i] = 0.0f;
  }
  return 1;
}

// YTWCore1 end-to-end test
static int test_YTWCore1(YTWFnsOrig* o, YTWFnsNew* n) {
  int mism = 0;

  // --- Test Parameters ---
  float hant[YTW_N_ANT] = { 5.0f * 3.281f, 0.0f, 0.0f, 0.0f };
  ftn_i2 ant_phase[YTW_N_ANT] = {1,1,1,1};
  ftn_i2 ant_kind = 1;
  float freqs[] = { 7.0f, 10.1f, 14.0f, 18.068f, 21.0f, 24.89f, 28.0f }; // MHz
  float soil2 = 13.0f;
  float soil1 = 0.005f;
  ftn_i2 diff_n = 0;
  ftn_i2 dbg_en = 0;
  float dbg_angle = 5.0f;

  // --- Dynamic Profile File Listing ---
  const char* pro_dir = "pro";
  char** files = NULL; // We will use a dynamic array of strings
  int file_count = 0;

  DIR *d = opendir(pro_dir);
  if (!d) {
    perror("Could not open 'pro' directory");
    return 1; // Return an error if the directory cannot be opened
  }

  printf("Scanning for .PRO files in '%s' directory...\n", pro_dir);
  struct dirent *dir;
  while ((dir = readdir(d)) != NULL) {
    const char* fname = dir->d_name;
    // Check if the filename ends with ".PRO" (case-insensitive)
    const char* ext = strrchr(fname, '.');
    if (ext && (stricmp(ext, ".PRO") == 0)) {
      // Allocate space for the new full path string (e.g., "pro/filename.PRO")
      char* full_path = malloc(strlen(pro_dir) + 1 + strlen(fname) + 1);
      sprintf(full_path, "%s/%s", pro_dir, fname);

      // Grow our dynamic array of files
      files = realloc(files, (file_count + 1) * sizeof(char*));
      if (!files) {
          perror("Failed to reallocate memory for file list");
          closedir(d);
          return 1;
      }
      files[file_count] = full_path;
      file_count++;
    }
  }
  closedir(d);

  printf("Found %d profile files to test.\n", file_count);
  if (file_count == 0) {
      printf("Warning: No .PRO files found. Aborting integration test.\n");
      return 0; // Not an error, just nothing to test
  }

  // --- Worst-Case Mismatch Tracking ---
  const char *worst_file = "<none>";
  float worst_freq = -1.0f, worst_diff = 0.0f;
  unsigned worst_h = 0;
  unsigned total_tests = 0, mismatched_tests = 0;

  // --- Main Test Loops ---
  for (unsigned fi=0;fi<sizeof(freqs)/sizeof(freqs[0]);++fi) {
    float freq = freqs[fi];
    printf("\n--- Testing Frequency: %.3f MHz ---\n", freq);

    for (int fidx = 0; fidx < file_count; ++fidx) {
      float dist_base[YTW_N_DIST] = {0}, hasl_base[YTW_N_DIST] = {0};
      if (!load_profile_from_PRO(files[fidx], dist_base, hasl_base)) {
        exit(3);
      }

      printf("%s\n", files[fidx]);
      fflush(stdout);

      for (unsigned h = 5; h <= 25; h++) {
        hant[0] = h * 3.281f; // vary antenna height from 5m to 25m

        // Make copies for each side (the original may mutate inputs)
        float dist_o[YTW_N_DIST], hasl_o[YTW_N_DIST];
        float dist_n[YTW_N_DIST], hasl_n[YTW_N_DIST];
        memcpy(dist_o, dist_base, sizeof(dist_o));
        memcpy(hasl_o, hasl_base, sizeof(hasl_o));
        memcpy(dist_n, dist_base, sizeof(dist_n));
        memcpy(hasl_n, hasl_base, sizeof(hasl_n));

        float out_o[YTW_N_OUT] = {0};
        float out_n[YTW_N_OUT] = {0};

        o->YTWCore1(dist_o, hasl_o, hant, &freq, &soil2, &soil1,
                    &ant_kind, &diff_n, &dbg_en, &dbg_angle, out_o, ant_phase);
        n->YTWCore1(dist_n, hasl_n, hant, &freq, &soil2, &soil1,
                    &ant_kind, &diff_n, &dbg_en, &dbg_angle, out_n, ant_phase);

        total_tests++;

        int local = 0;
        for (int i=0;i<YTW_N_OUT;i++) {
          if (!nearly_equal(out_o[i], out_n[i], TOL_F_INTEGRATION)) {
            printf("    YTWCore1(h=%u, f=%.3f, %s): out[%d] orig=%.6g new=%.6g\n", h, freq, files[fidx], i, out_o[i], out_n[i]);
            if (!isnan(out_o[i])) {
              // We know some of our testcases produce orig=NaN and new=valid.
              // Report them but don't count as mismatch.
              local++;
            }
          }
          const float diff = fabsf(out_o[i] - out_n[i]);
          if (diff > worst_diff) {
            worst_diff = diff;
            worst_file = files[fidx];
            worst_freq = freq;
            worst_h = h;
          }
        }
        if (local) {
          mismatched_tests++;
          mism += local;
          printf("  YTWCore1(h=%u, f=%.3f, %s): %s (%d mismatches)\n", h, freq, files[fidx], local? "MISMATCHES":"OK", local);
        }
      }

    }

  }

  printf("\n============================================================\n");
  printf("YTWCore1: completed %u tests, %u with mismatches\n", total_tests, mismatched_tests);
  printf("YTWCore1: worst mismatch was %.6g (h=%u, f=%.3f, %s)\n", worst_diff, worst_h, worst_freq, worst_file);
  printf("\n============================================================\n");

  // --- Memory Cleanup ---
  for (int i = 0; i < file_count; ++i) {
    free(files[i]);
  }
  free(files);

  return mism;
}

int main(int argc, char** argv) {
  const char* orig_path = (argc > 1) ? argv[1] : "YTWCore.dll";
  const char* new_path  = (argc > 2) ? argv[2] : "OpenYTWCore.dll";

  YTWFnsOrig orig = load_original(orig_path);
  YTWFnsNew  news = load_new(new_path);

  int total_mismatches = 0;

  // Seed Fortran COMMONs so routines depending on them see identical state
  seed_commons(&orig, &news, 7.0f, 13.0f, 0.005f);

  // Execute suites
  total_mismatches += test_ATN4(&orig, &news);
  total_mismatches += test_ANGHORIZ(&orig, &news);
  total_mismatches += test_ANGIN(&orig, &news);
  total_mismatches += test_FFCT(&orig, &news);
  total_mismatches += test_WD(&orig, &news);
  total_mismatches += test_YUTD(&orig, &news);
  total_mismatches += test_FRESNEL(&orig, &news);
  total_mismatches += test_REFL(&orig, &news);

  // “Real” DIFFDIFF/DRD using control parameters from original
  total_mismatches += test_DIFFDIFF_DRD_harness(&orig, &news);

  if (total_mismatches == 0) {  // skip slow test if previous tests fail
    // Integration test
    total_mismatches += test_YTWCore1(&orig, &news);
  }

  // Summary
  if (total_mismatches == 0) {
    printf("\nSUMMARY: All tests OK\n");
  } else {
    printf("\nSUMMARY: Found %d mismatches (see details above)\n", total_mismatches);
  }

  if (orig.mod) FreeLibrary(orig.mod);
  if (news.mod) FreeLibrary(news.mod);
  return total_mismatches ? 1 : 0;
}
