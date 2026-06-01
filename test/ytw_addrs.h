#pragma once
#include <stdint.h>
#include <windows.h>

// Calling conventions (can be overridden with -D)
#ifndef CALLCONV_ORIG
#define CALLCONV_ORIG __stdcall
#endif
#ifndef CALLCONV_NEW
#define CALLCONV_NEW  __cdecl
#endif

// VAs from the original DLL disassembly
enum {
    VA_DIFFDIFF  = 0x10001000,
    VA_YUTD      = 0x10002697,
    VA_WD        = 0x10002861,
    VA_FFCT      = 0x10002E8C,
    VA_ATN4      = 0x10003186,
    VA_FRESNEL   = 0x100032A7,
    VA_ANGIN     = 0x10003594,
    VA_ANGHORIZ  = 0x100036CA,
    VA_DRD       = 0x10003728,
    VA_YTWCore1  = 0x100062C0,
    VA_REFL      = 0x1000F192
};

// Helper: gets the preferred ImageBase (for VA->RVA under ASLR)
static inline uintptr_t get_preferred_image_base(HMODULE hmod) {
    uint8_t* base = (uint8_t*)hmod;
    IMAGE_DOS_HEADER* dos = (IMAGE_DOS_HEADER*)base;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return 0;
    IMAGE_NT_HEADERS* nt = (IMAGE_NT_HEADERS*)(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return 0;
    return (uintptr_t)nt->OptionalHeader.ImageBase;
}

// Converts a disassembly VA into a callable pointer at runtime
static inline void* get_fn_by_disasm_va(HMODULE hmod, uintptr_t disasm_va) {
    uintptr_t preferred = get_preferred_image_base(hmod);
    if (!preferred) return NULL;
    uintptr_t rva = disasm_va - preferred;
    return (void*)((uintptr_t)hmod + rva);
}
