/* Phase 4 A03 jump-law reducer.
 *
 * This is deliberately C-only. It anchors the shipping ASM state-machine
 * regions, then evaluates the exact signed velocity recurrence recovered from
 * those instructions. It does not read or mutate emulator state.
 *
 * Build:
 *   cc -O2 -std=c11 -Wall -Wextra tools/phase4_a03_static.c -o /tmp/phase4_a03_static
 * Run:
 *   /tmp/phase4_a03_static
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *read_file(const char *path, size_t *size_out)
{
    FILE *fp = fopen(path, "rb");
    long n;
    char *data;

    if (!fp) {
        perror(path);
        return NULL;
    }
    if (fseek(fp, 0, SEEK_END) != 0 || (n = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0) {
        fclose(fp);
        return NULL;
    }
    data = malloc((size_t)n + 1);
    if (!data) {
        fclose(fp);
        return NULL;
    }
    if (fread(data, 1, (size_t)n, fp) != (size_t)n) {
        free(data);
        fclose(fp);
        return NULL;
    }
    fclose(fp);
    data[n] = '\0';
    *size_out = (size_t)n;
    return data;
}

static unsigned count_text(const char *text, const char *needle)
{
    unsigned count = 0;
    size_t n = strlen(needle);
    while ((text = strstr(text, needle)) != NULL) {
        count++;
        text += n;
    }
    return count;
}

static int check_order(const char *text)
{
    static const char *const anchors[] = {
        ".L_80048b5c", /* Cross read/test */
        ".L_80048bc8", /* admitted takeoff */
        ".L_80048cd8", /* held/state dispatch */
        ".L_80048d00", /* released-Cross path */
        ".L_80048d68"  /* common gravity/cap/store tail */
    };
    const char *cursor = text;

    for (size_t i = 0; i < sizeof(anchors) / sizeof(anchors[0]); i++) {
        const char *hit = strstr(cursor, anchors[i]);
        if (!hit) {
            fprintf(stderr, "missing_or_out_of_order=%s\n", anchors[i]);
            return 0;
        }
        printf("asm_anchor\t%s\toffset=%zu\n", anchors[i],
               (size_t)(hit - text));
        cursor = hit + strlen(anchors[i]);
    }
    return 1;
}

/* Arithmetic shift right by one, expressed without relying on a host's signed
 * right-shift convention. All observed operands are even, but this is exact for
 * odd negative values too. */
static int32_t mips_sra1(int32_t value)
{
    return value >= 0 ? value / 2 : -(((-value) + 1) / 2);
}

static int32_t apex_gain(int32_t impulse, int held_ticks)
{
    int32_t velocity = impulse;
    int32_t y = 0;
    int32_t apex = 0;
    int state = 1;

    for (int tick = 1; tick < 128; tick++) {
        if (state == 1 && tick > held_ticks) {
            if (velocity < 0) {
                if (velocity < -800)
                    velocity += 384;
                velocity = mips_sra1(velocity);
                velocity -= 256;
            }
            state = 2;
        }

        velocity += 256;
        if (velocity > 4096)
            velocity = 4096;
        y += velocity;
        if (y < apex)
            apex = y;
        if (y >= 0 && tick > held_ticks + 1)
            break;
    }
    return -apex;
}

static void print_curve(const char *name, int32_t impulse, int max_hold)
{
    int32_t best_apex = -1;
    int best_hold = -1;

    printf("curve\t%s\timpulse=%d\n", name, impulse);
    for (int hold = 1; hold <= max_hold; hold++) {
        int32_t apex = apex_gain(impulse, hold);
        if (apex > best_apex) {
            best_apex = apex;
            best_hold = hold;
        }
        printf("hold\t%s\tticks=%d\tapex_gain=%d\n", name, hold, apex);
    }
    printf("best\t%s\tticks=%d\tapex_gain=%d\n", name, best_hold,
           best_apex);
}

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] :
        "asm/hand_written/80048138_player_vertical_update.s";
    size_t source_size = 0;
    char *source = read_file(path, &source_size);

    if (!source)
        return 1;
    printf("source\t%s\tbytes=%zu\n", path, source_size);
    if (!check_order(source)) {
        free(source);
        return 2;
    }
    printf("cross_mask\t0x4000\ttext_occurrences=%u\n",
           count_text(source, "0x4000"));

    /* Decoded instruction constants and PCs:
     * 0x80048B60: Cross mask 0x4000
     * 0x80048BAC: signed floor-Y admission comparison, threshold 1024
     * 0x80048D24/40/50: release adjustment, sra, and -256 stage
     * 0x80048D68/8C: common +256 gravity and velocity store
     * Prologue: -3072 normal and -3776 when player+0x90 bit 0x20 is set.
     */
    printf("law\tnormal_impulse=-3072\tpower_impulse=-3776\tgravity=256"
           "\trelease_cutoff=-800\trelease_bias=384\tfall_cap=4096\n");
    print_curve("normal", -3072, 18);
    print_curve("power", -3776, 20);
    free(source);
    return 0;
}
