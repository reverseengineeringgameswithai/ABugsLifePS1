/* Documentation-grade semantic C for the E15 presentation-height owner.
 *
 * This is not matching source. Exact pristine opcodes, caller censuses,
 * function hashes, source statuses and the retained runtime-PC join live in
 * analysis/phase4_fmv_present_rect_height_static_ownership.json.
 */
#include <stdint.h>

struct fmv_double_buffer {
    void *block[2];
    uint32_t active_index;
};

struct fmv_rect_s16 {
    int16_t x;
    int16_t y;
    int16_t w;
    int16_t h;
};

struct fmv_player_boundary_from_abe0 {
    struct fmv_double_buffer buffers; /* 0x800CABE0 */
    void *presentation_block;
    struct fmv_rect_s16 rect[2];
    uint32_t active_rect_index;
    struct fmv_rect_s16 present;      /* 0x800CAC04 */
};

struct fmv_decode_commit_state {
    int32_t decoded_frame_index;
    int32_t previous_decoded_frame_index;
    uint8_t decode_stop_latch;
    uint8_t padding_09[3];
    uint32_t cached_frame_width;
    uint32_t cached_frame_height;     /* 0x800B9A5C */
};

#define FMV_PLAYER_BOUNDARY_BASE      0x800CABE0u
#define FMV_DECODE_COMMIT_STATE       0x800B9A4Cu
#define FMV_PRESENT_UPLOAD            0x800B6634u
#define FMV_DECODE_COMMIT_DIMENSIONS  0x800B6A7Cu
#define FMV_DECODE_ONE_RECORD         0x800B6C24u
#define FMV_PRESENT_HEIGHT_STORE      0x800B6BF0u
#define GPU_RECT_HEIGHT_CLAMP_STORE   0x80064178u
#define ST_GET_NEXT                   0x80070C9Cu
#define FMV_PLAYER_INIT_HELPER_CALL   0x800B70A0u
#define FMV_PLAYER_LOOP_HELPER_CALL   0x800B7280u
#define FMV_PLAYER_LOOP_BACK_EDGE     0x800B745Cu

/*
 * Both player calls at 0x800B70A0 and 0x800B7280 pass the same exact
 * 0x800CABE0 base. Helper 0x800B6C24 preserves that a0 into the
 * 0x800B6A7C call, whose s1 therefore owns the layout above.
 */
static void semantic_publish_decoded_dimensions(
    struct fmv_player_boundary_from_abe0 *boundary,
    const struct fmv_decode_commit_state *commit,
    int16_t display_mode)
{
    uint16_t height = (uint16_t)commit->cached_frame_height;
    int16_t width = (int16_t)(commit->cached_frame_width * display_mode / 2);

    boundary->rect[1].h = (int16_t)height; /* s1 + 0x1e, 0x800B6BE8 */
    boundary->rect[0].h = (int16_t)height; /* s1 + 0x16, 0x800B6BEC */
    boundary->present.h = (int16_t)height; /* s1 + 0x2a, 0x800B6BF0 */
    boundary->rect[1].w = width;
    boundary->rect[0].w = width;
}

/*
 * 0x800B6C24 is a single-call wrapper, not a loop. It preserves only a0 and
 * calls 0x800B6A7C once at 0x800B6C34. The player calls the wrapper once at
 * 0x800B70A0 before entering its loop, preserves the same boundary pointer in
 * s3, then calls it at 0x800B7280 once per iteration. The back edge at
 * 0x800B745C targets 0x800B70E0 and cannot return to the initialization call.
 *
 * At 0x800B6A7C only a0 is semantic on entry. The apparent a1/a2/a3 values in
 * functionTrace are caller-saved residue: a1 is replaced with &stack_record
 * in the StGetNext delay slot at 0x800B6A9C, and a2/a3 are first defined at
 * 0x800B6B8C/0x800B6B90 before the geometry call. Consequently the retained
 * 1/1/9 register classes are not three decoded-record layouts and must not be
 * added to config/record_types.yaml.
 *
 * The commit function has a conventional jr ra at 0x800B6C1C and the wrapper
 * has one at 0x800B6C9C. The first retained synthetic exit is therefore an
 * observer reconstruction fact, not evidence of a special guest return.
 */

/*
 * Presentation 0x800B6634 supplies &boundary->present to matching-C
 * LoadImage. The pristine libgpu table has driver[2] =
 * gpu_present_drawotag_vsync and driver[8] = PsyQ _dws. `_dws` clamps the
 * supplied RECT height to [0, gpu_height] and stores it at 0x80064178.
 * It is a downstream SDK normalization, not another decoder-height source.
 */
