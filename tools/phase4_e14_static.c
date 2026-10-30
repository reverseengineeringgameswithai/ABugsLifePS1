/* Phase 4 E14 static verifier.
 *
 * Usage:
 *   phase4_e14_static SCUS_942.88 BITS/MEMORY.BIN [other raw .BIN images...]
 *
 * The first argument must be the pristine PS-X EXE. The second is the
 * MEMORY.BIN overlay at 0x800B5788. Remaining images are scanned as raw blobs.
 * This tool intentionally performs no writes.
 */

#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    EXE_HEADER_SIZE = 0x800,
    MEMORY_BASE = 0x800B5788u,
    TABLE_BASE = 0x80089938u,
    TABLE_SIZE = 320u,
    GP_VALUE = 0x80081D98u
};

typedef struct Blob {
    const char *path;
    uint8_t *data;
    size_t size;
    size_t code_offset;
    size_t code_size;
    uint32_t load_base;
} Blob;

typedef struct SymbolicValue {
    bool valid;
    bool dynamic;
    uint32_t value;
} SymbolicValue;

typedef struct AccessHit {
    size_t offset;
    uint32_t opcode;
} AccessHit;

typedef struct AccessCounts {
    unsigned loads;
    unsigned stores;
} AccessCounts;

typedef struct Pin {
    uint32_t pc;
    uint32_t word;
    const char *meaning;
} Pin;

static uint32_t read_u32le(const uint8_t *p)
{
    return (uint32_t)p[0] |
           (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 |
           (uint32_t)p[3] << 24;
}

static int16_t signed_imm(uint32_t word)
{
    return (int16_t)(word & 0xFFFFu);
}

static Blob load_blob(const char *path, bool expect_exe, uint32_t raw_base)
{
    Blob blob = {0};
    FILE *fp = fopen(path, "rb");
    long length;

    if (fp == NULL || fseek(fp, 0, SEEK_END) != 0 ||
        (length = ftell(fp)) < 0 || fseek(fp, 0, SEEK_SET) != 0) {
        fprintf(stderr, "cannot open %s\n", path);
        exit(2);
    }

    blob.path = path;
    blob.size = (size_t)length;
    blob.data = malloc(blob.size == 0 ? 1 : blob.size);
    if (blob.data == NULL || fread(blob.data, 1, blob.size, fp) != blob.size) {
        fprintf(stderr, "cannot read %s\n", path);
        fclose(fp);
        exit(2);
    }
    fclose(fp);

    if (expect_exe) {
        if (blob.size < EXE_HEADER_SIZE ||
            memcmp(blob.data, "PS-X EXE", 8) != 0) {
            fprintf(stderr, "%s is not a PS-X EXE\n", path);
            exit(2);
        }
        blob.load_base = read_u32le(blob.data + 0x18);
        blob.code_size = read_u32le(blob.data + 0x1C);
        blob.code_offset = EXE_HEADER_SIZE;
        if (blob.code_offset + blob.code_size > blob.size) {
            fprintf(stderr, "%s has an invalid text extent\n", path);
            exit(2);
        }
    } else {
        blob.load_base = raw_base;
        blob.code_offset = 0;
        blob.code_size = blob.size;
    }
    return blob;
}

static void free_blob(Blob *blob)
{
    free(blob->data);
    blob->data = NULL;
}

static uint32_t word_at_pc(const Blob *blob, uint32_t pc)
{
    size_t offset;

    if (blob->load_base == 0 || pc < blob->load_base) {
        fprintf(stderr, "invalid PC 0x%08" PRIX32 " for %s\n", pc, blob->path);
        exit(2);
    }
    offset = blob->code_offset + (size_t)(pc - blob->load_base);
    if (offset + 4 > blob->code_offset + blob->code_size) {
        fprintf(stderr, "PC 0x%08" PRIX32 " outside %s\n", pc, blob->path);
        exit(2);
    }
    return read_u32le(blob->data + offset);
}

static void verify_pins(const Blob *blob, const Pin *pins, size_t count)
{
    size_t i;

    for (i = 0; i < count; i++) {
        uint32_t actual = word_at_pc(blob, pins[i].pc);
        if (actual != pins[i].word) {
            fprintf(stderr,
                    "pin mismatch at 0x%08" PRIX32
                    ": got 0x%08" PRIX32 ", expected 0x%08" PRIX32
                    " (%s)\n",
                    pins[i].pc, actual, pins[i].word, pins[i].meaning);
            exit(1);
        }
    }
}

static bool is_memory_opcode(unsigned opcode)
{
    return opcode == 0x20 || opcode == 0x21 || opcode == 0x23 ||
           opcode == 0x24 || opcode == 0x25 || opcode == 0x28 ||
           opcode == 0x29 || opcode == 0x2B;
}

static bool is_load_opcode(unsigned opcode)
{
    return opcode >= 0x20 && opcode <= 0x26;
}

static bool writes_rt(unsigned opcode)
{
    return opcode == 0x08 || opcode == 0x09 || opcode == 0x0A ||
           opcode == 0x0B || opcode == 0x0C || opcode == 0x0D ||
           opcode == 0x0E || opcode == 0x0F || is_load_opcode(opcode);
}

static bool already_hit(const AccessHit *hits, size_t count,
                        size_t offset, uint32_t opcode)
{
    size_t i;
    for (i = 0; i < count; i++) {
        if (hits[i].offset == offset && hits[i].opcode == opcode) {
            return true;
        }
    }
    return false;
}

/* Follow every LUI 0x8009 seed for a bounded 64-instruction window. This
 * recognizes both base+index forms used by the table, including
 *   lui at,0x8009; addu at,at,index; lbu ...,0x9938(at)
 * and materialized-base forms followed by an indexed addu.
 */
static AccessCounts scan_table_accesses(const Blob *blob)
{
    AccessHit hits[256];
    size_t hit_count = 0;
    size_t begin = blob->code_offset;
    size_t end = begin + blob->code_size;
    size_t seed_offset;
    AccessCounts counts = {0};

    for (seed_offset = begin; seed_offset + 4 <= end; seed_offset += 4) {
        uint32_t seed = read_u32le(blob->data + seed_offset);
        unsigned seed_rt;
        SymbolicValue regs[32] = {{0}};
        bool stop_after_delay = false;
        size_t offset;
        unsigned steps;

        if ((seed >> 26) != 0x0F || (seed & 0xFFFFu) != 0x8009u) {
            continue;
        }
        seed_rt = (seed >> 16) & 31u;
        if (seed_rt == 0) {
            continue;
        }
        regs[seed_rt] = (SymbolicValue){true, false, 0x80090000u};

        for (offset = seed_offset + 4, steps = 0;
             offset + 4 <= end && steps < 64;
             offset += 4, steps++) {
            uint32_t word = read_u32le(blob->data + offset);
            unsigned opcode = word >> 26;
            unsigned rs = (word >> 21) & 31u;
            unsigned rt = (word >> 16) & 31u;
            unsigned rd = (word >> 11) & 31u;
            unsigned function = word & 63u;
            SymbolicValue output = {0};
            bool set_output = false;
            unsigned destination = 0;

            if (is_memory_opcode(opcode) && regs[rs].valid) {
                uint32_t effective = regs[rs].value +
                                     (int32_t)signed_imm(word);
                bool intersects = regs[rs].dynamic
                    ? effective == TABLE_BASE
                    : effective >= TABLE_BASE &&
                      effective < TABLE_BASE + TABLE_SIZE;

                if (intersects &&
                    !already_hit(hits, hit_count, offset, opcode)) {
                    if (hit_count >= sizeof(hits) / sizeof(hits[0])) {
                        fprintf(stderr, "table-hit buffer exhausted\n");
                        exit(2);
                    }
                    hits[hit_count++] = (AccessHit){offset, opcode};
                }
            }

            if (opcode == 0x0F) {
                output = (SymbolicValue){true, false,
                                         (word & 0xFFFFu) << 16};
                set_output = true;
                destination = rt;
            } else if ((opcode == 0x08 || opcode == 0x09 ||
                        opcode == 0x0D) && regs[rs].valid) {
                output = regs[rs];
                output.value = opcode == 0x0D
                    ? output.value | (word & 0xFFFFu)
                    : output.value + (int32_t)signed_imm(word);
                set_output = true;
                destination = rt;
            } else if (opcode == 0 && function == 0x21) {
                if (regs[rs].valid && regs[rt].valid) {
                    output.valid = true;
                    output.dynamic = regs[rs].dynamic || regs[rt].dynamic;
                    output.value = regs[rs].value + regs[rt].value;
                } else if (regs[rs].valid) {
                    output = regs[rs];
                    output.dynamic = true;
                } else if (regs[rt].valid) {
                    output = regs[rt];
                    output.dynamic = true;
                }
                set_output = true;
                destination = rd;
            } else if (opcode == 0 && function == 0x25) {
                if (rt == 0 && regs[rs].valid) {
                    output = regs[rs];
                } else if (rs == 0 && regs[rt].valid) {
                    output = regs[rt];
                }
                set_output = true;
                destination = rd;
            } else if (opcode == 0 &&
                       (function == 0 || function == 2 || function == 3)) {
                set_output = true;
                destination = rd;
            } else if (writes_rt(opcode)) {
                set_output = true;
                destination = rt;
            }

            if (set_output && destination != 0) {
                regs[destination] = output;
            }
            if (is_load_opcode(opcode) && rt != 0) {
                regs[rt] = (SymbolicValue){0};
            }

            if (stop_after_delay) {
                break;
            }
            if (opcode == 0x02 || opcode == 0x03 ||
                (opcode == 0 && (function == 0x08 || function == 0x09))) {
                stop_after_delay = true;
            }
        }
    }

    for (seed_offset = 0; seed_offset < hit_count; seed_offset++) {
        if (is_load_opcode(hits[seed_offset].opcode)) {
            counts.loads++;
        } else {
            counts.stores++;
        }
    }
    return counts;
}

static unsigned count_direct_gp_memory_accesses(const Blob *blob,
                                                uint32_t lo, uint32_t hi,
                                                uint32_t address)
{
    uint16_t displacement = (uint16_t)(address - GP_VALUE);
    unsigned count = 0;
    uint32_t pc;

    for (pc = lo; pc < hi; pc += 4) {
        uint32_t word = word_at_pc(blob, pc);
        unsigned opcode = word >> 26;
        unsigned rs = (word >> 21) & 31u;
        if (is_memory_opcode(opcode) && rs == 28 &&
            (word & 0xFFFFu) == displacement) {
            count++;
        }
    }
    return count;
}

int main(int argc, char **argv)
{
    static const Pin resident_pins[] = {
        {0x80049E54u, 0x90229938u, "spawn score read"},
        {0x80049E5Cu, 0x2C420064u, "spawn score threshold 100"},
        {0x80049E78u, 0x3042FFFDu, "spawn clears CHASE bit"},
        {0x8004B4E0u, 0x90830000u, "successful contact score read"},
        {0x8004B4E8u, 0x2C6200C8u, "increment guard below 200"},
        {0x8004B4F0u, 0x24620002u, "successful contact increment by two"},
        {0x8004B4F4u, 0xA0820000u, "successful contact score store"},
        {0x8005464Cu, 0x90239938u, "new berry column sentinel read"},
        {0x80054650u, 0x240200FFu, "uninitialized sentinel 255"},
        {0x80054684u, 0x90630000u, "old berry column source read"},
        {0x80054690u, 0xA0430000u, "new berry column destination store"},
        {0x80054694u, 0x2AA20040u, "64-row copy bound"},
        {0x80059108u, 0x90229938u, "landed-hit score read"},
        {0x80059110u, 0x2C420078u, "CHASE setter threshold 120"},
        {0x8005914Cu, 0x34420002u, "landed-hit sets CHASE bit"},
        {0x8005936Cu, 0x90830000u, "damage-tail score read"},
        {0x80059380u, 0x2462FFFEu, "damage-tail decrement by two"},
        {0x80059384u, 0xA0820000u, "damage-tail score store"}
    };
    static const Pin memory_pins[] = {
        {0x800B6B4Cu, 0x8C8422CCu, "screen-offset X read"},
        {0x800B6B54u, 0x8CA522D0u, "screen-offset Y read"},
        {0x800B6B58u, 0x0C00FD35u, "set_draw_env_offset call"},
        {0x800B73CCu, 0x30420020u, "option left mask"},
        {0x800B73E0u, 0x30620080u, "rumble option bit test"},
        {0x800B73E8u, 0x34620080u, "rumble option bit set"},
        {0x800B742Cu, 0x3062007Fu, "rumble option bit clear"},
        {0x800B74E4u, 0x0C00E6F6u, "pad_rumble_update call"},
        {0x800B7608u, 0x304300F0u, "screen-adjust d-pad mask"},
        {0x800B7688u, 0xAC2222D0u, "screen-offset Y store"},
        {0x800B76C0u, 0xAC2222D0u, "screen-offset Y store"},
        {0x800B7724u, 0xAC2222CCu, "screen-offset X store"},
        {0x800B7900u, 0x0C0141FEu, "reapply table-indexed CD mix"}
    };
    Blob exe;
    Blob memory;
    AccessCounts resident_counts;
    unsigned overlay_refs = 0;
    unsigned direct_sfx_volume_refs;
    int i;

    if (argc < 3) {
        fprintf(stderr,
                "usage: %s SCUS_942.88 BITS/MEMORY.BIN [raw .BIN...]\n",
                argv[0]);
        return 2;
    }

    exe = load_blob(argv[1], true, 0);
    memory = load_blob(argv[2], false, MEMORY_BASE);
    if (exe.load_base != 0x80010000u) {
        fprintf(stderr, "unexpected EXE load base 0x%08" PRIX32 "\n",
                exe.load_base);
        return 1;
    }

    verify_pins(&exe, resident_pins,
                sizeof(resident_pins) / sizeof(resident_pins[0]));
    verify_pins(&memory, memory_pins,
                sizeof(memory_pins) / sizeof(memory_pins[0]));

    resident_counts = scan_table_accesses(&exe);
    if (resident_counts.loads != 20 || resident_counts.stores != 12) {
        fprintf(stderr,
                "resident table frontier changed: loads=%u stores=%u\n",
                resident_counts.loads, resident_counts.stores);
        return 1;
    }

    for (i = 2; i < argc; i++) {
        Blob overlay = i == 2 ? memory : load_blob(argv[i], false, 0);
        AccessCounts counts = scan_table_accesses(&overlay);
        overlay_refs += counts.loads + counts.stores;
        if (i != 2) {
            free_blob(&overlay);
        }
    }
    if (overlay_refs != 0) {
        fprintf(stderr, "unexpected overlay table references: %u\n",
                overlay_refs);
        return 1;
    }

    direct_sfx_volume_refs = count_direct_gp_memory_accesses(
        &memory, 0x800B687Cu, 0x800B79C8u, 0x8008247Eu);
    if (direct_sfx_volume_refs != 0) {
        fprintf(stderr, "options path gained direct SFX-volume accesses\n");
        return 1;
    }

    printf("E14_STATIC PASS table_accesses=32 loads=20 stores=12 "
           "overlay_refs=0 resident_pins=%zu memory_pins=%zu "
           "direct_sfx_volume_refs=0\n",
           sizeof(resident_pins) / sizeof(resident_pins[0]),
           sizeof(memory_pins) / sizeof(memory_pins[0]));

    free_blob(&memory);
    free_blob(&exe);
    return 0;
}
