/* sfx_voice_manager.c  --  RE reconstruction of FUNC_80044D28 (0x80044D28, 2384 B).
 *
 * The SPU voice scheduler for A Bug's Life sound effects: the single point that
 * turns a decoded SFX request (descriptor + optional 3D position) into a keyed-on
 * libspu voice, managing an 8-slot voice pool with reuse/pre-emption. Called by
 * sfx_dispatch, contact_pickup_sfx, ambient_sfx_sequence_update, and the
 * sfx_voice_manager_glue_* / sfx_nearest_pickup_f_glue wrappers.
 *
 * Scope: this is a BEHAVIORAL reconstruction (not byte-exact) -- the function is a
 * 2384 B giant whose exact register allocation the compiler would not reproduce
 * from readable source. Addresses, table strides, and the arithmetic shape are
 * transcribed from asm/hand_written/80044d28_sfx_voice_manager.s; the *semantics*
 * of the listener-transform rows and the secondary voice table are inferred and
 * flagged inline. Confirmed callees: SquareRoot0, EnterCriticalSection,
 * ExitCriticalSection, SsUtKeyOn (0x80068634), SsUtKeyOnV (0x80068b24).
 *
 * Vault: [[SYS_sfx_system]] . [[EXP_2026-07-09_audio_engine_probe]].
 */

/* ---- confirmed layout ---------------------------------------------------- */

/* The 8-slot voice pool (0x80089860, stride 8). free slot => voice_id == -1. */
struct sfx_voice_slot {
    void  *descriptor;   /* +0: the SFX descriptor pointer currently owning the slot */
    short  voice_id;     /* +4: libspu voice handle from SsUtKeyOn, or -1 when free   */
    short  _pad;         /* +6: (stride is 8)                                         */
};
extern struct sfx_voice_slot g_sfx_voice_pool[8];        /* 0x80089860 */

/* Audio listener transform in scratchpad (s0 = 0x1f800374). Confirmed offsets;
 * row semantics INFERRED (a listener position + two projection axes used to turn a
 * world-space source delta into a stereo pan + distance). */
struct audio_listener {
    int   pos[3];        /* +0/+4/+8: listener (camera) world position (>>9 fixed)   */
    short _r0[12];       /* +12..                                                    */
    short axis_a[3];     /* +32/+34/+36: projection axis A (lateral / right)  [infer]*/
    short _r1[3];        /* +38/+40/+42                                              */
    short axis_b[3];     /* +44/+46/+48: projection axis B (forward / depth)  [infer]*/
};
#define G_LISTENER  ((volatile struct audio_listener *)0x1f800374)

extern unsigned short g_sfx_vab_id;      /* gp+1040 (0x800821A8): VAB id passed to SsUtKeyOn      */
extern short          g_sfx_master_vol;  /* 0x8008247E: master SFX volume scalar (mult, >>7)      */
extern short          g_sfx_muted;       /* gp+1284: nonzero => default-bank SFX suppressed       */
extern void          *g_sfx_default_bank;/* 0x800A6500 sentinel: the "no object" default bank ptr */

/* Secondary companion-voice table (0x8009FB56, stride 20, 8 entries up to
 * 0x8009FBF6). Each row that references the just-keyed voice_id is re-keyed with
 * its own stored pan/vol -- INFERRED to be linked/echo companion voices. */
struct sfx_companion {
    short voice_id;      /* +0  (rel -1194): the primary voice this row shadows      */
    short pan_l, pan_r;  /* +10/+12 (rel -1204/-1202)                                */
    short vol_l, vol_r;  /* +22/+24 (rel -1192/-1190)                                */
};
extern struct sfx_companion g_sfx_companions[8];         /* 0x8009FB56 */

extern int  SquareRoot0(int);
extern void EnterCriticalSection(void);
extern void ExitCriticalSection(void);
extern int  SsUtKeyOn(int vabId, int prog, int tone, int note,
                      int fine, int vol_l, int vol_r);   /* -> voice id */
extern int  SsUtKeyOnV(int vabId, int prog, int tone, int note,
                       int fine, int vol_l, int vol_r);

/* Split a packed pitch/vol param into coarse (>>7, rounded toward +inf for
 * negatives) and fine (&0x7f) halves, matching the asm's `addiu +127; sra 7`. */
static int coarse(int v) { return (v < 0 ? v + 127 : v) >> 7; }

/* ---- the scheduler ------------------------------------------------------- */

int sfx_voice_manager(void *descriptor, int p_pitch, int p_pan, int base_vol,
                      /* stack */ int *source_pos, int pan_enable)
{
    int slot = -1;
    int i;

    /* (1) pick a slot: prefer one already owned by this descriptor, else a free
     * one (voice_id == -1). Last match wins for the free-slot case. */
    for (i = 0; i < 8; i++) {
        if (g_sfx_voice_pool[i].descriptor == descriptor) { slot = i; break; }
        if (g_sfx_voice_pool[i].voice_id == -1)             slot = i;
    }
    if (slot == -1)
        return -1;                                   /* pool full -> drop the SFX */

    /* (2) if we're re-taking a slot that is still actively playing this same
     * descriptor, stop the old voice first (a "note off" at note 44). */
    if (g_sfx_voice_pool[slot].descriptor == descriptor &&
        g_sfx_voice_pool[slot].voice_id != -1) {
        SsUtKeyOnV(g_sfx_vab_id, 0, 1, 44, 0, 0, 0);
    }

    /* (3) global suppression of default-bank SFX. */
    if (g_sfx_muted && descriptor == g_sfx_default_bank)
        return -1;

    int vol_l, vol_r;
    if (source_pos != 0) {
        /* (4) POSITIONAL: project (source - listener) onto the two listener axes
         * to get a stereo balance, and onto distance for attenuation. The deltas
         * are taken in >>9 fixed point; SquareRoot0 / helper 0x80060154 turn the
         * squared sums into a magnitude. base_vol scales the result. */
        int dx = (source_pos[0] >> 9) - (G_LISTENER->pos[0] >> 9);
        int dy = (source_pos[1] >> 9) - (G_LISTENER->pos[1] >> 9);
        int dz = (source_pos[2] >> 9) - (G_LISTENER->pos[2] >> 9);

        int lateral = dx * G_LISTENER->axis_a[0] + dy * G_LISTENER->axis_a[1]
                    + dz * G_LISTENER->axis_a[2];
        int depth   = dx * G_LISTENER->axis_b[0] + dy * G_LISTENER->axis_b[1]
                    + dz * G_LISTENER->axis_b[2];

        /* magnitudes (asm: >>12 with round-up, square, sqrt via 0x80060154). */
        int lat_m   = SquareRoot0((lateral >> 12) * (lateral >> 12));
        int dep_m   = SquareRoot0((depth   >> 12) * (depth   >> 12));

        /* stereo split scaled by the caller's base volume (asm uses a /3
         * reciprocal-multiply balance around a 3072 reference and the div/break
         * overflow guards; reproduced here in intent, not bit-for-bit). */
        int falloff = 3072 - (lat_m << 4);
        vol_l = ((falloff * base_vol) / 3072);
        vol_r = ((( 3072 - (dep_m << 4)) * base_vol) / 3072);
        if (pan_enable) {                            /* stack arg: rebalance to the nearer side */
            if (vol_r < vol_l) vol_r = (vol_r * base_vol >> 7);
            else               vol_l = (vol_l * base_vol >> 7);
        }
        if (vol_l < 0) vol_l = 0; if (vol_l > 150) vol_l = 150;   /* clamp [0,150] */
        if (vol_r < 0) vol_r = 0; if (vol_r > 150) vol_r = 150;
    } else {
        /* (5) NON-POSITIONAL: a flat 2D SFX -- volume straight from base_vol. */
        vol_l = vol_r = base_vol;
    }

    EnterCriticalSection();

    /* (6) scale by master volume and clamp to the SsUtKeyOn ceiling [0,160]. */
    int kl = (vol_l * g_sfx_master_vol) >> 7; if (kl > 160) kl = 160;
    int kr = (vol_r * g_sfx_master_vol) >> 7; if (kr > 160) kr = 160;

    int voice = SsUtKeyOn(g_sfx_vab_id, coarse(p_pitch), p_pitch & 0x7f,
                          coarse(p_pan),  p_pan  & 0x7f, kl, kr);

    /* (7) dedup: no other slot may reference this voice id, then claim our slot. */
    for (i = 0; i < 8; i++)
        if (g_sfx_voice_pool[i].voice_id == voice)
            g_sfx_voice_pool[i].voice_id = -1;
    g_sfx_voice_pool[slot].descriptor = descriptor;
    g_sfx_voice_pool[slot].voice_id   = voice;

    /* (8) companion voices: re-key any table row shadowing this voice with its own
     * stored pan/vol (INFERRED: echo / duplicate positional voices). */
    if (voice != -1) {
        int j;
        for (j = 0; j < 8; j++) {
            if (g_sfx_companions[j].voice_id != voice) continue;
            int cl = (g_sfx_companions[j].vol_l * g_sfx_master_vol) >> 7; if (cl > 160) cl = 160;
            int cr = (g_sfx_companions[j].vol_r * g_sfx_master_vol) >> 7; if (cr > 160) cr = 160;
            int cv = SsUtKeyOn(g_sfx_vab_id,
                               coarse(g_sfx_companions[j].pan_l), g_sfx_companions[j].pan_l & 0x7f,
                               coarse(g_sfx_companions[j].pan_r), g_sfx_companions[j].pan_r & 0x7f,
                               cl, cr);
            for (i = 0; i < 8; i++)
                if (g_sfx_voice_pool[i].voice_id == cv)
                    g_sfx_voice_pool[i].voice_id = -1;
            g_sfx_companions[j].voice_id = cv;
        }
    }

    ExitCriticalSection();

    /* (9) return the average L/R loudness actually played (callers use it to pick
     * the loudest nearby pickup), or -1 when nothing was keyed. */
    if (voice == -1)
        return -1;
    return (vol_l + vol_r) / 2;
}
