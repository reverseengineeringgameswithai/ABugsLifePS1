/*
 * Phase 4 A06 static guard, corrected after Interpreter route attribution.
 *
 * This deliberately analyzes retained pristine ASM text. It does not launch an
 * emulator, mutate media, or inspect a derivative executable.
 *
 * Build/run from the repository root:
 *   cc -O2 -Wall -Wextra -o /tmp/phase4_a06_static tools/phase4_a06_static.c
 *   /tmp/phase4_a06_static
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct text {
    char *data;
    size_t size;
};

static struct text read_all(const char *path)
{
    struct text out = {0};
    FILE *fp = fopen(path, "rb");
    long end;

    if (fp == NULL) {
        perror(path);
        exit(2);
    }
    if (fseek(fp, 0, SEEK_END) != 0 || (end = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0) {
        perror(path);
        exit(2);
    }
    out.size = (size_t)end;
    out.data = malloc(out.size + 1);
    if (out.data == NULL) {
        fputs("allocation failure\n", stderr);
        exit(2);
    }
    if (fread(out.data, 1, out.size, fp) != out.size) {
        perror(path);
        exit(2);
    }
    out.data[out.size] = '\0';
    fclose(fp);
    return out;
}

static int require(const struct text *source, const char *needle,
                   const char *fact)
{
    int present = strstr(source->data, needle) != NULL;
    printf("    {\"fact\":\"%s\",\"present\":%s}", fact,
           present ? "true" : "false");
    return present;
}

int main(void)
{
    const char *player_path = "asm/nonmatchings/resident/80048138.s";
    const char *terrain_path = "asm/nonmatchings/resident/80041ac4.s";
    const char *animation_path = "asm/nonmatchings/resident/800563d4.s";
    struct text player = read_all(player_path);
    struct text terrain = read_all(terrain_path);
    struct text animation = read_all(animation_path);
    int ok = 1;

    puts("{");
    puts("  \"schema\":\"abl.phase4.a06.static_guard.v3\",");
    puts("  \"inputs\":[\"asm/nonmatchings/resident/80048138.s\",\"asm/nonmatchings/resident/80041ac4.s\",\"asm/nonmatchings/resident/800563d4.s\"],");
    puts("  \"checks\":[");
    ok &= require(&terrain, "0x80041cf8", "separate terrain helper can publish player+0x8c");
    puts(",");
    ok &= require(&player, "0x800488d8", "player update tests the separate contact fast path");
    puts(",");
    ok &= require(&player, "0x80048b6c", "ordinary route branches when Cross is not held");
    puts(",");
    ok &= require(&player, "0x80048ce0", "ordinary grounded held route selects state five");
    puts(",");
    ok &= require(&player, "0x80048d64", "ordinary route commits the selected action state");
    puts(",");
    ok &= require(&player, "0x80048d10", "grounded Cross-release route clears action state");
    puts(",");
    ok &= require(&player, "0x800490d0", "ordinary steering subtracts from target heading");
    puts(",");
    ok &= require(&player, "0x80049100", "ordinary steering adds to target heading");
    puts(",");
    ok &= require(&player, "0x80049298", "shared convergence stores current heading");
    puts(",");
    ok &= require(&player, "0x800481b4", "ordinary heading cap defaults to 0x400");
    puts(",");
    ok &= require(&player, "0x8004895c", "separate fast path replaces cap with 0x80");
    puts(",");
    ok &= require(&player, "0x80048f00", "slide maintenance requires Cross at timer eleven");
    puts(",");
    ok &= require(&player, "0x80048f10", "projected component threshold is 0x300");
    puts(",");
    ok &= require(&player, "0x80048f3c", "qualifying projected motion rearms timer to twelve");
    puts(",");
    ok &= require(&animation, "0x80056860", "timer twelve selects slide animation 0x1c");
    puts(",");
    ok &= require(&animation, "0x800569ac", "desired animation is copied into the latched selector");
    puts("\n  ],");
    printf("  \"all_checks_pass\":%s\n", ok ? "true" : "false");
    puts("}");

    free(player.data);
    free(terrain.data);
    free(animation.data);
    return ok ? 0 : 1;
}
