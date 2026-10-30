/* Phase 4 D19 Molt static-ASM and Interpreter-trace reducer. */
#include <ctype.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define OVERLAY_BASE 0x800B39A0u
#define MOLT_BASE    0x8009FF90u
#define MOLT_HP      0x8009FFFEu

typedef struct {
    unsigned char *data;
    size_t size;
    uint32_t base;
} Image;

static uint16_t le16(const unsigned char *p)
{
    return (uint16_t)p[0] | (uint16_t)p[1] << 8;
}

static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static void fail(const char *message)
{
    fprintf(stderr, "phase4_d19_molt: %s\n", message);
    exit(2);
}

static unsigned char *load_bytes(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    long end;
    unsigned char *data;

    if (!f || fseek(f, 0, SEEK_END) != 0 || (end = ftell(f)) < 0 ||
        fseek(f, 0, SEEK_SET) != 0)
        fail(path);
    data = malloc((size_t)end + 1);
    if (!data || fread(data, 1, (size_t)end, f) != (size_t)end)
        fail("short read");
    fclose(f);
    data[end] = 0;
    *size = (size_t)end;
    return data;
}

static Image raw_image(const char *path, uint32_t base)
{
    Image image;
    image.data = load_bytes(path, &image.size);
    image.base = base;
    return image;
}

static Image exe_image(const char *path)
{
    size_t file_size;
    unsigned char *file = load_bytes(path, &file_size);
    Image image;

    if (file_size < 0x800 || memcmp(file, "PS-X EXE", 8) != 0)
        fail("bad PS-X EXE");
    image.base = le32(file + 0x18);
    image.size = le32(file + 0x1c);
    if (image.size > file_size - 0x800)
        fail("PS-X EXE text exceeds file");
    image.data = malloc(image.size);
    if (!image.data)
        fail("out of memory");
    memcpy(image.data, file + 0x800, image.size);
    free(file);
    return image;
}

static uint32_t word_at(const Image *image, uint32_t address)
{
    size_t offset;
    if (address < image->base ||
        (offset = (size_t)(address - image->base)) + 4 > image->size)
        fail("address outside image");
    return le32(image->data + offset);
}

static uint16_t half_at(const Image *image, uint32_t address)
{
    size_t offset;
    if (address < image->base ||
        (offset = (size_t)(address - image->base)) + 2 > image->size)
        fail("halfword outside image");
    return le16(image->data + offset);
}

static void verify_static(const Image *overlay, const Image *wrong_overlay,
                          const Image *exe)
{
    static const struct {
        uint32_t pc;
        uint32_t word;
        const char *role;
    } expected[] = {
        {0x800B3BBCu, 0x2610FF90u, "materialize Molt base"},
        {0x800B3C7Cu, 0x2631FFFEu, "materialize Molt HP"},
        {0x800B3C80u, 0x86220000u, "read current HP"},
        {0x800B3C88u, 0x8C6345F4u, "read accepted HP snapshot"},
        {0x800B3C9Cu, 0x8C42FFD4u, "read actor +0x44 gate"},
        {0x800B3CA4u, 0x10520006u, "gate value one branch"},
        {0x800B3CB0u, 0x844223A0u, "read goal latch"},
        {0x800B3CC4u, 0xA6230000u, "restore accepted HP"},
        {0x800B3DECu, 0x2A020015u, "accepted HP below 21"},
        {0x800B3E70u, 0xA42223A0u, "set goal latch"},
        {0x800B3E7Cu, 0xA4222470u, "set 150 tick transition"},
        {0x800B3F04u, 0x8442FFFEu, "read post-hit HP"},
        {0x800B3F0Cu, 0xAC2245F4u, "commit accepted HP snapshot"},
        {0x800B43E0u, 0x24020047u, "crowd contact type 71"},
        {0x800B43F8u, 0x0C016838u, "call contact allocator"},
        {0x800B4468u, 0xAC224604u, "crowd SFX cooldown"}
    };
    size_t i;

    for (i = 0; i < sizeof(expected) / sizeof(expected[0]); i++) {
        uint32_t actual = word_at(overlay, expected[i].pc);
        if (actual != expected[i].word) {
            fprintf(stderr, "word mismatch at 0x%08" PRIX32 " (%s)\n",
                    expected[i].pc, expected[i].role);
            exit(2);
        }
    }
    if (word_at(wrong_overlay, 0x800B3CC4u) == 0xA6230000u)
        fail("LEVEL09/LEVEL.BIN unexpectedly contains the live restore writer");
    if (word_at(exe, 0x80049CA0u) != 0xA502006Eu)
        fail("Molt initial HP writer changed");
    if (word_at(exe, 0x800590E4u) != 0xA642006Eu)
        fail("shared damage writer changed");
    if ((int16_t)half_at(exe, 0x80077688u) != 5)
        fail("Molt VM instruction is not park_seek opcode 6");

    printf("STATIC words=%zu live_overlay=LEVEL03/LEVEL1.BIN "
           "wrong_overlay_excluded=yes\n",
           sizeof(expected) / sizeof(expected[0]));
    puts("STATIC actor=0x8009FF90 hp=0x8009FFFE init=50 "
         "damage_writer=0x800590E4 restore_writer=0x800B3CC4");
    puts("STATIC accepted_threshold=HP<21 goal_latch=0x800823A0 "
         "transition_ticks=150");
    puts("STATIC crowd_allocator=0x800B43F8 contact_type=71 "
         "return_address=0x800B4400 vm_0x80077688=park_seek");
}

static void corpus_restore_census(void)
{
    static const char *paths[] = {
        "REBUILD/files/LEVEL01/LEVEL.BIN", "REBUILD/files/LEVEL01/LEVEL1.BIN",
        "REBUILD/files/LEVEL02/LEVEL.BIN", "REBUILD/files/LEVEL02/LEVEL1.BIN",
        "REBUILD/files/LEVEL03/LEVEL.BIN", "REBUILD/files/LEVEL03/LEVEL1.BIN",
        "REBUILD/files/LEVEL04/LEVEL.BIN", "REBUILD/files/LEVEL04/LEVEL1.BIN",
        "REBUILD/files/LEVEL05/LEVEL.BIN", "REBUILD/files/LEVEL05/LEVEL1.BIN",
        "REBUILD/files/LEVEL06/LEVEL.BIN", "REBUILD/files/LEVEL06/LEVEL1.BIN",
        "REBUILD/files/LEVEL07/LEVEL.BIN", "REBUILD/files/LEVEL07/LEVEL1.BIN",
        "REBUILD/files/LEVEL08/LEVEL.BIN", "REBUILD/files/LEVEL08/LEVEL1.BIN",
        "REBUILD/files/LEVEL09/LEVEL.BIN", "REBUILD/files/LEVEL09/LEVEL1.BIN",
        "REBUILD/files/LEVEL10/LEVEL.BIN"
    };
    unsigned hits = 0;
    size_t p;

    for (p = 0; p < sizeof(paths) / sizeof(paths[0]); p++) {
        size_t size, offset;
        unsigned char *data = load_bytes(paths[p], &size);
        for (offset = 0; offset + 4 <= size; offset += 4) {
            if (le32(data + offset) != 0xA6230000u)
                continue;
            hits++;
            printf("CORPUS restore_word path=%s offset=0x%zX pc=0x%08X\n",
                   paths[p], offset, OVERLAY_BASE + (unsigned)offset);
            if (strcmp(paths[p], "REBUILD/files/LEVEL03/LEVEL1.BIN") != 0 ||
                offset != 0x324)
                fail("unexpected restore-word corpus occurrence");
        }
        free(data);
    }
    if (hits != 1)
        fail("restore-word corpus is not singular");
    printf("CORPUS restore_word_hits=%u files=%zu\n", hits,
           sizeof(paths) / sizeof(paths[0]));
}

static const char *json_key(const char *p, const char *name)
{
    char needle[80];
    snprintf(needle, sizeof(needle), "\"%s\":", name);
    p = strstr(p, needle);
    if (!p)
        return NULL;
    p += strlen(needle);
    while (isspace((unsigned char)*p))
        p++;
    return p;
}

static long long json_number(const char *p, const char *name)
{
    p = json_key(p, name);
    return p ? strtoll(p, NULL, 0) : 0;
}

static uint32_t json_hex(const char *p, const char *name)
{
    p = json_key(p, name);
    if (!p)
        return 0;
    while (*p == '"' || isspace((unsigned char)*p))
        p++;
    return (uint32_t)strtoul(p, NULL, 0);
}

static int json_hex_blob(const char *p, const char *name,
                         unsigned char *out, size_t capacity)
{
    size_t count = 0;
    p = json_key(p, name);
    if (!p || *p++ != '"')
        return 0;
    while (*p && *p != '"' && count < capacity) {
        unsigned value;
        if (sscanf(p, "%2x", &value) != 1)
            return 0;
        out[count++] = (unsigned char)value;
        p += 2;
    }
    return (int)count;
}

static void reduce_runtime(const char *path)
{
    size_t size;
    char *json = (char *)load_bytes(path, &size);
    char *p = strstr(json, "\n  \"events\": [");
    char *end = p ? strstr(p, "\n  ],") : NULL;
    int total = 0, molt = 0, accepted = 0, rolled_back = 0;
    int accepted_hp = 50, final_frame = -1, gate44 = 0;
    int identity_errors = 0, contact_errors = 0;
    int alloc_total = 0, crowd_allocs = 0;
    int retained_damage_writes = 0, retained_restore_writes = 0;

    if (!p || !end)
        fail("runtime JSON has no top-level event array");
    while (p < end) {
        char *object = strstr(p, "    {");
        char *object_end;
        unsigned char actor[0x84], contact[0x40];
        uint32_t s2;
        int new_hp, frame;

        if (!object || object >= end)
            break;
        object_end = strstr(object, "    }");
        if (!object_end || object_end > end)
            fail("unterminated runtime event");
        if (json_hex_blob(object, "actor_hex", actor, sizeof(actor)) != 0x84 ||
            json_hex_blob(object, "contact_hex", contact, sizeof(contact)) != 0x40)
            fail("bad runtime snapshot length");
        total++;
        s2 = json_hex(object, "s2");
        new_hp = (int)json_number(object, "v0_new_signed");
        frame = (int)json_number(object, "emulator_frame");
        if (s2 == MOLT_BASE) {
            molt++;
            if (le32(actor) != 29 || le16(actor + 0x5c) != 0x5043 ||
                le32(actor + 0x70) != 0x80077688u ||
                le32(actor + 0x7c) != 0x8004A0A0u)
                identity_errors++;
            if (contact[0x34] != 0 || le16(contact + 0x2c) != 10 ||
                contact[0x2f] != 1 || new_hp != (int16_t)le16(actor + 0x6e) - 2)
                contact_errors++;
            if (le32(actor + 0x44) == 1)
                gate44++;
            if (new_hp < accepted_hp) {
                accepted_hp = new_hp;
                accepted++;
                if (new_hp == 20)
                    final_frame = frame;
            } else {
                rolled_back++;
            }
        }
        p = object_end + 5;
    }

    p = strstr(json, "\n  \"alloc_events\":");
    end = p ? strstr(p, "\n  \"alloc_summary\":") : NULL;
    if (!p || !end)
        fail("runtime JSON has no allocation section");
    while ((p = strstr(p, "\"ra\": \"0x")) != NULL && p < end) {
        uint32_t ra = (uint32_t)strtoul(p + 7, NULL, 0);
        alloc_total++;
        if (ra == 0x800B4400u)
            crowd_allocs++;
        p += 7;
    }

    p = strstr(json, "\n  \"actor_access\":");
    end = p ? strstr(p, "\n  \"alloc_events\":") : NULL;
    if (!p || !end)
        fail("runtime JSON has no actor access section");
    while ((p = strstr(p, "\"address\": \"0x8009fffe\"")) != NULL && p < end) {
        uint32_t pc = json_hex(p, "instruction_pc");
        if (pc == 0x800590E4u)
            retained_damage_writes++;
        if (pc == 0x800B3CC4u)
            retained_restore_writes++;
        p += 12;
    }

    if (molt != 43 || accepted != 15 || rolled_back != 28 ||
        accepted_hp != 20 || final_frame != 13589 || identity_errors ||
        contact_errors || alloc_total != 141 || crowd_allocs != 31)
        fail("runtime invariants changed");

    printf("RUNTIME events=%d molt_collisions=%d accepted=%d rolled_back=%d "
           "gate44_seen=%d final_hp=%d final_accepted_frame=%d\n",
           total, molt, accepted, rolled_back, gate44, accepted_hp, final_frame);
    printf("RUNTIME actor_id=29 flags=0x5043 vm=0x80077688 "
           "callback=0x8004A0A0 contact_class=0 f24=10 f27=1\n");
    printf("RUNTIME allocations=%d crowd_ra_0x800B4400=%d "
           "retained_damage_writes=%d retained_restore_writes=%d\n",
           alloc_total, crowd_allocs, retained_damage_writes,
           retained_restore_writes);
    free(json);
}

int main(int argc, char **argv)
{
    Image overlay = raw_image("REBUILD/files/LEVEL03/LEVEL1.BIN", OVERLAY_BASE);
    Image wrong_overlay = raw_image("REBUILD/files/LEVEL09/LEVEL.BIN", OVERLAY_BASE);
    Image exe = exe_image("REBUILD/files/SCUS_942.88");

    if (argc > 2) {
        fprintf(stderr, "usage: %s [break_capture.json]\n", argv[0]);
        return 2;
    }
    verify_static(&overlay, &wrong_overlay, &exe);
    corpus_restore_census();
    if (argc == 2)
        reduce_runtime(argv[1]);
    free(overlay.data);
    free(wrong_overlay.data);
    free(exe.data);
    return 0;
}
