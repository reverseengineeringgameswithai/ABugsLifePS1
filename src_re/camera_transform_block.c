/* src_re/camera_transform_block.c -- OG reverse-engineering: A Bug's Life (PS1, SCUS-94288)
 * RESIDENT camera transform state (world->view rotation + camera world position) and the exact
 * world->screen projection ABL's GTE performs.
 *
 * This is the data substrate the Tier-3 render cave (mod/caves/tier3_render.c) reads each frame to
 * project custom geometry the same way the engine projects the native world. Found 2026-06-25 by
 * capturing the GTE rotation at the world-space draw and searching RAM for it (see METHOD below);
 * the rotation turns out to be MIRRORED in main RAM, so a per-frame cave can read it without any
 * GTE access or hook-timing constraint.
 *
 * NOT a decompiled function -- this documents the data layout + the projection math. The routine
 * that recomputes R/C each frame (camera follow + GTE load via ctc2) is not yet bounded; the EXEC
 * site where R is live in the GTE as pure world->view is the terrain draw 0x80010718.
 */

#include <stdint.h>

/* ---- world->view rotation matrix R -------------------------------------------------------------
 * 3x3, row-major, 1.3.12 fixed-point (each element = value * 4096). INCLUDES the camera's baked
 * ~1.6x horizontal zoom (det ~= 1.598, so it is NOT orthonormal -- it is rotation * zoom). This is
 * exactly GTE control reg 0..4 (the rotation_matrix) at the world draw 0x80010718, where the GTE
 * rotation is the pure world->view transform (no per-object rotation loaded).
 *
 * MIRRORED IN MAIN RAM, live, updated every frame, tracks the camera:
 *   0x80090FB0  -- authoritative world->view copy (matches the GTE at 0x80010718); the Tier-3
 *                 render cave reads this.
 *   0x8009E290  -- a near-identical sibling copy (a few units off; staging/previous-frame).
 * Example (Flik at LEVEL01 spawn, looking down-forward):
 *   R = [ 4032,    0, 5160,
 *            0, 4096,    0,
 *        -3225,    0, 2520 ]   ( /4096 = [[0.984,0,1.260],[0,1.0,0],[-0.787,0,0.615]] )
 */
typedef int16_t mat3x3_q12[9];          /* row-major R11,R12,R13, R21,R22,R23, R31,R32,R33 */

#define ABL_CAM_R      ((volatile mat3x3_q12 *)0x80090FB0)   /* live world->view rotation (q12) */
#define ABL_CAM_R_ALT  ((volatile mat3x3_q12 *)0x8009E290)   /* sibling copy */

/* ---- camera world position C ------------------------------------------------------------------
 * 3x s32 world units, in the SCRATCHPAD (data-cache RAM, readable at 0x1F8003xx). Above + beside
 * Flik, a look-down follow-cam. Sibling at 0x1F8003B4 = the zoom matrix diag(1.6,1,1) (q12).
 */
typedef struct { int32_t x, y, z; } vec3_s32;

#define ABL_CAM_POS  ((volatile vec3_s32 *)0x1F800374)       /* camera world position (live) */
#define ABL_CAM_ZOOM ((volatile mat3x3_q12 *)0x1F8003B4)     /* diag(1.6,1,1) q12 */

/* ---- projection (matches the GTE's screen_xy_fifo exactly) ------------------------------------
 * For a world vertex V:
 *     view = R . (V - C) / 4096                 (R is q12, so the /4096 removes the fixed scale)
 *     sx   = H * view.x / view.z + OFX
 *     sy   = H * view.y / view.z + OFY
 * Constants from the GTE control state (getGteState): H = projection_distance = 160,
 * screen_offset = (OFX,OFY) = (256,120). +Y is DOWN, +Z is INTO the screen (cull view.z <= 0).
 *
 * The Tier-3 cave does this in pure int32: deltas are >>4 before the R-multiply so every 32x32
 * product and their sum stay inside int32 (no __muldi3), and the divide is a native 32-bit `div`
 * (no __divdi3). Reference (float, for clarity):
 */
#define ABL_PROJ_H   160
#define ABL_PROJ_OFX 256
#define ABL_PROJ_OFY 120

static inline int abl_world_to_screen(const int16_t R[9], const vec3_s32 *C,
                                      int32_t wx, int32_t wy, int32_t wz,
                                      int *sx, int *sy)
{
    int dx = wx - C->x, dy = wy - C->y, dz = wz - C->z;
    int vx = (R[0] * dx + R[1] * dy + R[2] * dz) >> 12;   /* R . d, then /4096 */
    int vy = (R[3] * dx + R[4] * dy + R[5] * dz) >> 12;
    int vz = (R[6] * dx + R[7] * dy + R[8] * dz) >> 12;
    if (vz <= 0) return 0;                                /* behind the camera */
    *sx = ABL_PROJ_H * vx / vz + ABL_PROJ_OFX;
    *sy = ABL_PROJ_H * vy / vz + ABL_PROJ_OFY;
    return 1;
}

/* ---- METHOD (evidence) ------------------------------------------------------------------------
 * 1. Breakpoint EXEC 0x80010718 (world-space terrain draw), debugger.getGteState ->
 *    control.rotation_matrix = R (decoded /4096). C = 3x s32 read at scratchpad 0x1F800374.
 * 2. Searched main RAM 0x80010000..0x80200000 for R's packed int16 bytes -> hits 0x80090FB0,
 *    0x8009E290 (and a scratchpad copy near C).
 * 3. Moved the camera (turned/walked Flik) and re-read 0x80090FB0 -> it changed to a valid new
 *    rotation, i.e. it is the LIVE per-frame world->view R (confirmed it tracks).
 * 4. Verified end-to-end: tools/tier3_render_live.py (host) and mod/caves/tier3_render.c (in-cave)
 *    project the Tier-3 mesh through R/C and it renders in-world, perspective-correct, world-locked.
 * Related earlier RE: tools/trace_camera_transform.py, tools/transform_math.py.
 */
