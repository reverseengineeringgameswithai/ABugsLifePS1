/* src_re/known_crash_cave_hazards.c
 *
 * Reference-only C notes for EXE cave ranges that looked free in the static SCUS
 * image but are known to crash or hang at runtime. Keep this file boring and
 * literal: it is meant to stop future agents from repeating old failures.
 */

typedef unsigned int u32;

struct AblKnownCrashRange {
    u32 lo;
    u32 hi;      /* exclusive */
    const char *name;
    const char *symptom;
    const char *avoid_reason;
};

#define ABL_DECOMP_TABLE_LO 0x8007EFE8u
#define ABL_DECOMP_TABLE_HI 0x8007F0D8u
#define ABL_FMV_BUFFER_LO   0x800814BCu
#define ABL_FMV_BUFFER_HI   0x80081530u
#define ABL_ZEROED_HELPER_LO 0x80081058u
#define ABL_ZEROED_HELPER_HI 0x800810A4u
#define ABL_RETAIL_DESC_LO  0x80082030u
#define ABL_RETAIL_DESC_HI  0x8008203Cu

static const struct AblKnownCrashRange ABL_KNOWN_CRASH_RANGES[] = {
    {
        ABL_DECOMP_TABLE_LO,
        ABL_DECOMP_TABLE_HI,
        "0x800616e0 decompressor/stream table",
        "ALLMODS gold-drop crash, 2026-07-07: DuckStation logged invalid byte "
        "write 0x910A0000, value 0x55, at PC 0x80061788; COP0_EPC was "
        "0x80061784.",
        "The table base is materialized as 0x8007EFE8 and walked with a 0x30 "
        "stride. Code bytes here corrupt destination/source pointers used while "
        "streaming level/enemy data."
    },
    {
        0x8007F130u,
        0x8007F170u,
        "Training/streaming runtime state near 0x800616xx",
        "Earlier helper/table placement here caused an invalid read/write crash "
        "around the 0x800616C0..0x80061788 path.",
        "This range may look static-zero or mostly inert, but live Training and "
        "streaming code owns it."
    },
    {
        0x8007FDC0u,
        0x80080BE0u,
        "level-load workspace",
        "EXE-baked cave code disappears or turns into zeros during level load.",
        "The loader memsets this workspace; gameplay zero reads are evidence of "
        "runtime clearing, not free executable storage."
    },
    {
        ABL_FMV_BUFFER_LO,
        ABL_FMV_BUFFER_HI,
        "intro-FMV boot work buffer",
        "Cave overlap hung the disc at the PlayStation logo.",
        "The FMV boot player expects this zero-initialized buffer to remain zero "
        "until it writes its own cells."
    },
    {
        ABL_ZEROED_HELPER_LO,
        ABL_ZEROED_HELPER_HI,
        "live-zeroed golddrop helper range",
        "A 2026-07-07 ALLMODS boot showed helper code at 0x80081058..0x800810A4 "
        "had been zeroed while the surrounding 0x800810C0+ caves survived.",
        "Do not branch from a pickup/contact hook into this range. Inline compact "
        "helpers in a proven resident gap instead, such as 0x80078D84..0x80078E04 "
        "for the gold-drop pickup path."
    },
    {
        ABL_RETAIL_DESC_LO,
        ABL_RETAIL_DESC_HI,
        "native berry/seed descriptor at 0x80082030",
        "A bad Blackberry descriptor reuse made seed colours stop being purple and "
        "made mega homing appear brownish gold.",
        "This is native descriptor data, not scratch space. Use a private descriptor "
        "such as 0x80081234 and repair object_pointer_list[0x25] at runtime."
    },
};

static int ranges_overlap(u32 a_lo, u32 a_hi, u32 b_lo, u32 b_hi)
{
    return a_lo < b_hi && a_hi > b_lo;
}

int abl_known_crash_range_index(u32 lo, u32 hi)
{
    unsigned i;
    for (i = 0; i < sizeof(ABL_KNOWN_CRASH_RANGES) / sizeof(ABL_KNOWN_CRASH_RANGES[0]); i++) {
        const struct AblKnownCrashRange *r = &ABL_KNOWN_CRASH_RANGES[i];
        if (ranges_overlap(lo, hi, r->lo, r->hi))
            return (int)i;
    }
    return -1;
}
