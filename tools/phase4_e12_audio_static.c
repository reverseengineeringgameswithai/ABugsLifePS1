#define _POSIX_C_SOURCE 200809L

/*
 * Phase 4 E12 audio static evidence guard.
 *
 * This deliberately uses only the pristine extracted retail files. It checks
 * the resident/overlay call frontier, selected voice-lifecycle instructions,
 * XA sector/channel inventories, and VAB header inventories without launching
 * DuckStation.
 *
 * Build:
 *   cc -std=c11 -O2 -Wall -Wextra -Werror \
 *      -o /tmp/phase4_e12_audio_static tools/phase4_e12_audio_static.c
 * Run from the repository root:
 *   /tmp/phase4_e12_audio_static
 */

#include <dirent.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define ARRAY_LEN(a) (sizeof(a) / sizeof((a)[0]))
#define PATH_CAP 4096

struct blob {
    uint8_t *data;
    size_t size;
};

struct scan_totals {
    unsigned overlay_files;
    unsigned dispatch_calls;
    unsigned play_sound_calls;
    unsigned vh_files;
};

struct xa_inventory {
    unsigned sectors;
    unsigned audio[8];
    unsigned eof[8];
};

static const char *g_root = ".";
static struct scan_totals g_totals;
static struct xa_inventory g_xa[5];
static unsigned g_xa_seen[5];

static uint16_t read_le16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t read_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int ends_with(const char *s, const char *suffix)
{
    size_t ns = strlen(s);
    size_t nx = strlen(suffix);
    return ns >= nx && strcmp(s + ns - nx, suffix) == 0;
}

static const char *base_name(const char *path)
{
    const char *slash = strrchr(path, '/');
    return slash != NULL ? slash + 1 : path;
}

static void fail(const char *what)
{
    fprintf(stderr, "E12 static guard failed: %s\n", what);
    exit(1);
}

static struct blob load_file(const char *path)
{
    struct blob out = {0};
    FILE *fp = fopen(path, "rb");
    long length;

    if (fp == NULL) {
        fprintf(stderr, "cannot open %s: %s\n", path, strerror(errno));
        exit(1);
    }
    if (fseek(fp, 0, SEEK_END) != 0 || (length = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0) {
        fclose(fp);
        fail("file length query");
    }
    out.size = (size_t)length;
    out.data = malloc(out.size != 0 ? out.size : 1);
    if (out.data == NULL) {
        fclose(fp);
        fail("allocation");
    }
    if (out.size != 0 && fread(out.data, 1, out.size, fp) != out.size) {
        fclose(fp);
        free(out.data);
        fail("short read");
    }
    fclose(fp);
    return out;
}

static void free_blob(struct blob *blob)
{
    free(blob->data);
    blob->data = NULL;
    blob->size = 0;
}

static unsigned count_word(const uint8_t *data, size_t size, uint32_t word)
{
    unsigned count = 0;
    size_t offset;

    for (offset = 0; offset + 4 <= size; offset += 4) {
        if (read_le32(data + offset) == word) {
            ++count;
        }
    }
    return count;
}

static uint32_t exe_word(const struct blob *exe, uint32_t address)
{
    uint32_t load_address;
    uint32_t load_size;
    uint64_t offset;

    if (exe->size < 0x800 || memcmp(exe->data, "PS-X EXE", 8) != 0) {
        fail("invalid PS-X EXE header");
    }
    load_address = read_le32(exe->data + 0x18);
    load_size = read_le32(exe->data + 0x1c);
    if (address < load_address || address - load_address >= load_size) {
        fail("resident address outside PS-X EXE payload");
    }
    offset = 0x800u + (uint64_t)(address - load_address);
    if (offset + 4 > exe->size) {
        fail("resident address outside file");
    }
    return read_le32(exe->data + (size_t)offset);
}

static void expect_exe_word(const struct blob *exe, uint32_t address,
                            uint32_t expected, const char *label)
{
    uint32_t actual = exe_word(exe, address);
    if (actual != expected) {
        fprintf(stderr,
                "%s mismatch at %08x: expected %08x, found %08x\n",
                label, address, expected, actual);
        exit(1);
    }
}

static void inspect_overlay(const char *path)
{
    const char *name = base_name(path);
    struct blob blob;

    if (strcmp(name, "LEVEL.BIN") != 0 && strcmp(name, "LEVEL1.BIN") != 0) {
        return;
    }
    blob = load_file(path);
    ++g_totals.overlay_files;
    g_totals.dispatch_calls += count_word(blob.data, blob.size, 0x0c014265u);
    g_totals.play_sound_calls += count_word(blob.data, blob.size, 0x0c014113u);
    free_blob(&blob);
}

static void inspect_vh(const char *path)
{
    struct blob blob;
    unsigned programs;
    unsigned tones;
    unsigned vags;

    if (!ends_with(path, ".VH")) {
        return;
    }
    blob = load_file(path);
    if (blob.size < 0x20 || memcmp(blob.data, "pBAV", 4) != 0 ||
        read_le32(blob.data + 4) != 6) {
        fprintf(stderr, "invalid VAB header: %s\n", path);
        exit(1);
    }
    programs = read_le16(blob.data + 18);
    tones = read_le16(blob.data + 20);
    vags = read_le16(blob.data + 22);
    printf("VAB %-24s programs=%u tones=%u vags=%u\n",
           base_name(path), programs, tones, vags);
    ++g_totals.vh_files;
    free_blob(&blob);
}

static void inspect_xa(const char *path)
{
    const char *name = base_name(path);
    unsigned index;
    struct blob blob;
    struct xa_inventory inventory = {0};
    size_t sector;

    if (strlen(name) != 9 || strncmp(name, "AUDIO", 5) != 0 ||
        name[5] < '1' || name[5] > '5' || strcmp(name + 6, ".XA") != 0) {
        return;
    }
    index = (unsigned)(name[5] - '1');
    blob = load_file(path);
    if (blob.size % 2336 != 0) {
        fprintf(stderr, "XA size is not sector aligned: %s\n", path);
        exit(1);
    }
    inventory.sectors = (unsigned)(blob.size / 2336);
    for (sector = 0; sector < inventory.sectors; ++sector) {
        const uint8_t *subheader = blob.data + sector * 2336;
        unsigned channel = subheader[1] & 31u;
        unsigned submode = subheader[2];
        if (channel < 8 && (submode & 0x04u) != 0) {
            ++inventory.audio[channel];
            if ((submode & 0x80u) != 0) {
                ++inventory.eof[channel];
            }
        }
    }
    g_xa[index] = inventory;
    g_xa_seen[index] = 1;
    free_blob(&blob);
}

static void walk_tree(const char *path)
{
    struct stat st;
    DIR *dir;
    struct dirent *entry;

    if (lstat(path, &st) != 0) {
        fprintf(stderr, "cannot stat %s: %s\n", path, strerror(errno));
        exit(1);
    }
    if (S_ISREG(st.st_mode)) {
        inspect_overlay(path);
        inspect_vh(path);
        inspect_xa(path);
        return;
    }
    if (!S_ISDIR(st.st_mode)) {
        return;
    }
    dir = opendir(path);
    if (dir == NULL) {
        fprintf(stderr, "cannot open directory %s: %s\n", path,
                strerror(errno));
        exit(1);
    }
    while ((entry = readdir(dir)) != NULL) {
        char child[PATH_CAP];
        int written;
        if (strcmp(entry->d_name, ".") == 0 ||
            strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        written = snprintf(child, sizeof(child), "%s/%s", path,
                           entry->d_name);
        if (written < 0 || (size_t)written >= sizeof(child)) {
            closedir(dir);
            fail("path too long");
        }
        walk_tree(child);
    }
    closedir(dir);
}

static void check_xa(void)
{
    static const unsigned expected_sectors[5] = {
        38992, 41872, 19248, 3600, 4264
    };
    static const unsigned expected_audio[5][8] = {
        {4842, 4375, 4723, 4442, 4664, 4520, 4762, 4595},
        {4476, 4683, 4520, 4477, 5202, 4572, 4518, 204},
        {204, 202, 227, 2353, 2282, 2374, 204, 204},
        {284, 217, 194, 418, 191, 137, 312, 93},
        {44, 66, 186, 134, 381, 501, 501, 501}
    };
    unsigned file;
    unsigned channel;

    for (file = 0; file < 5; ++file) {
        if (!g_xa_seen[file] || g_xa[file].sectors != expected_sectors[file]) {
            fail("XA file inventory mismatch");
        }
        printf("AUDIO%u.XA sectors=%u", file + 1, g_xa[file].sectors);
        for (channel = 0; channel < 8; ++channel) {
            if (g_xa[file].audio[channel] != expected_audio[file][channel] ||
                g_xa[file].eof[channel] != 1) {
                fail("XA channel/EOF inventory mismatch");
            }
            printf(" ch%u=%u", channel, g_xa[file].audio[channel]);
        }
        putchar('\n');
    }
}

static void print_music_map(void)
{
    unsigned scene;
    puts("music map (packed id = scene - 1):");
    for (scene = 1; scene <= 15; ++scene) {
        unsigned packed = scene - 1;
        printf("  scene %2u -> AUDIO%u.XA channel %u (0x%02x)\n",
               scene, packed / 8 + 1, packed & 7, packed);
    }
    puts("  special override -> AUDIO3.XA channel 5 (packed 0x15)");
}

int main(int argc, char **argv)
{
    char exe_path[PATH_CAP];
    char files_path[PATH_CAP];
    struct blob exe;
    unsigned resident_dispatch;
    unsigned resident_play_sound;

    if (argc > 2) {
        fprintf(stderr, "usage: %s [repository-root]\n", argv[0]);
        return 2;
    }
    if (argc == 2) {
        g_root = argv[1];
    }
    if (snprintf(exe_path, sizeof(exe_path), "%s/REBUILD/files/SCUS_942.88",
                 g_root) >= (int)sizeof(exe_path) ||
        snprintf(files_path, sizeof(files_path), "%s/REBUILD/files", g_root) >=
                 (int)sizeof(files_path)) {
        fail("root path too long");
    }

    exe = load_file(exe_path);
    resident_dispatch = count_word(exe.data + 0x800, exe.size - 0x800,
                                   0x0c014265u);
    resident_play_sound = count_word(exe.data + 0x800, exe.size - 0x800,
                                     0x0c014113u);
    if (resident_dispatch != 22 || resident_play_sound != 92) {
        fail("resident SFX call frontier changed");
    }

    /* Scene-to-looping-XA selection. */
    expect_exe_word(&exe, 0x8005bb90u, 0x84a5245cu,
                    "scene music selector load");
    expect_exe_word(&exe, 0x8005bc30u, 0x24040015u,
                    "special music override");
    expect_exe_word(&exe, 0x8005bc34u, 0x24a4ffffu,
                    "scene to packed music id");
    expect_exe_word(&exe, 0x8005bc38u, 0x0c011abau,
                    "looping music call");

    /* Eight-entry primary/companion ownership initialization and tick hook. */
    expect_exe_word(&exe, 0x80044c70u, 0x240200b4u,
                    "primary voice-pool end");
    expect_exe_word(&exe, 0x80044c7cu, 0xa423165au,
                    "primary voice-pool clear");
    expect_exe_word(&exe, 0x80044c90u, 0x2402008cu,
                    "companion voice-pool end");
    expect_exe_word(&exe, 0x80044c9cu, 0xa423fb56u,
                    "companion voice-pool clear");
    expect_exe_word(&exe, 0x80044cb8u, 0x24843284u,
                    "voice lifecycle callback pointer");
    expect_exe_word(&exe, 0x80044cbcu, 0x0c01a0fcu,
                    "voice lifecycle callback registration");
    expect_exe_word(&exe, 0x800432ecu, 0x0c01a2c9u,
                    "expired voice key-off");
    expect_exe_word(&exe, 0x800434dcu, 0x0c01b4bau,
                    "SPU all-keys status poll");

    walk_tree(files_path);
    if (g_totals.overlay_files != 20 || g_totals.dispatch_calls != 9 ||
        g_totals.play_sound_calls != 17) {
        fprintf(stderr,
                "overlay census: files=%u dispatch=%u play_sound=%u\n",
                g_totals.overlay_files, g_totals.dispatch_calls,
                g_totals.play_sound_calls);
        fail("overlay SFX call frontier changed");
    }
    if (g_totals.vh_files != 21) {
        fail("VAB bank inventory changed");
    }
    check_xa();
    print_music_map();
    printf("SFX calls: dispatch resident=%u overlay=%u total=%u; "
           "play_sound resident=%u overlay=%u total=%u\n",
           resident_dispatch, g_totals.dispatch_calls,
           resident_dispatch + g_totals.dispatch_calls,
           resident_play_sound, g_totals.play_sound_calls,
           resident_play_sound + g_totals.play_sound_calls);
    printf("VAB banks=%u overlay binaries=%u\n", g_totals.vh_files,
           g_totals.overlay_files);

    free_blob(&exe);
    return 0;
}
