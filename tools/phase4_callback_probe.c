#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Multi-image function-pointer materialization probe.
 *
 * Two receipts come out of one decoder pass, and they are DIFFERENT UNIVERSES.
 * They are emitted separately and must never be substituted for one another.
 *
 *   1. `fnptr` rows -- a POSITIVE-ONLY census of code addresses materialised by
 *      an adjacent lui/addiu or lui/ori pair, each classified by how the value
 *      leaves the materialising site (stored to a slot, passed in an argument
 *      register at a jal, called immediately through jalr, or unclassified).
 *      This finds registration sites; its SILENCE IS NOT EVIDENCE.  A pointer
 *      built across a basic block, loaded from data, or copied through another
 *      register is not reported, and the consumer of this receipt must keep the
 *      resulting callback groups incomplete.
 *
 *   2. `gapref` rows -- EVERY load and store in every byte of the image that no
 *      typed extent claims, with its base provenance stated.  This one is a
 *      census over its universe: a memory reference in a gap is reported
 *      whether or not its base could be resolved, so an unresolved base leaves
 *      the gap UNDECIDED instead of silently absent.
 *
 * Neither receipt claims that a decoded word is executed.  Bytes in a gap may
 * be data that happens to decode; a `gapref` row with `unresolved` provenance
 * is a demand for evidence, not a finding.
 *
 * Input manifest (TSV, order-independent except that an extent must follow the
 * image it belongs to):
 *
 *   image    <id>  <path>  <base_hex>  <size>
 *   resident <id>  <start_hex>  <end_hex>      (optional; defaults to the file)
 *   extent   <id>  <start_hex>  <end_hex>  <range_type>
 *   window <start_hex>  <end_hex>
 *   gp     <value_hex>
 */

#define MAX_IMAGES 64
#define MAX_WINDOWS 32

typedef struct {
    uint32_t start;
    uint32_t end;
    char type[16];
} Extent;

typedef struct {
    char id[64];
    char path[512];
    uint32_t base;
    uint32_t size;
    /* The RESIDENT sub-range of the file. A PS-X EXE carries a 2,048-byte
     * header and every level overlay a 4-byte one; those bytes are file
     * metadata that is never loaded as code or data, so they belong to the file
     * universe and not to the resident one. Sweeping them as an unclassified
     * gap conflates the two. Defaults to the whole file when no `resident` row
     * is supplied. */
    uint32_t resident_start;
    uint32_t resident_end;
    unsigned char *bytes;
    Extent *extents;
    size_t extent_count;
    size_t extent_capacity;
} Image;

typedef struct {
    uint32_t start;
    uint32_t end;
} Window;

static Image g_images[MAX_IMAGES];
static size_t g_image_count;
static Window g_windows[MAX_WINDOWS];
static size_t g_window_count;
static uint32_t g_gp = 0x80081D98u;

static void die(const char *message)
{
    fprintf(stderr, "phase4_callback_probe: %s\n", message);
    exit(2);
}

static void die_errno(const char *message)
{
    fprintf(stderr, "phase4_callback_probe: %s: %s\n", message, strerror(errno));
    exit(2);
}

static void *xrealloc(void *ptr, size_t size)
{
    void *next = realloc(ptr, size);
    if (next == NULL)
        die_errno("realloc");
    return next;
}

static uint32_t read_le32(const unsigned char *bytes)
{
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static int extent_compare(const void *left, const void *right)
{
    const Extent *a = left;
    const Extent *b = right;
    if (a->start < b->start)
        return -1;
    if (a->start > b->start)
        return 1;
    return 0;
}

static Image *find_image(const char *id)
{
    for (size_t i = 0; i < g_image_count; ++i) {
        if (strcmp(g_images[i].id, id) == 0)
            return &g_images[i];
    }
    return NULL;
}

static int extent_of(const Image *image, uint32_t address,
                     const Extent **extent_out)
{
    for (size_t j = 0; j < image->extent_count; ++j) {
        const Extent *extent = &image->extents[j];
        if (strcmp(extent->type, "code") != 0 &&
            strcmp(extent->type, "thunk") != 0)
            continue;
        if (address >= extent->start && address < extent->end) {
            *extent_out = extent;
            return 1;
        }
    }
    return 0;
}

static int image_contains(const Image *image, uint32_t address)
{
    return address >= image->base && address < image->base + image->size;
}

/*
 * Is `address` inside a code or thunk extent, and whose?
 *
 * EVERY level overlay loads at the same virtual address, so an address in the
 * overlay window is claimed by twenty different images and a first-match search
 * attributes it to whichever image the manifest happened to list first.
 *
 * ⚠️ Preferring the materialising image's code EXTENTS is not enough.  Two
 * overlays type their first words as `data` while others type the same words as
 * `code`, so a pointer materialised inside LEVEL02_LEVEL1 fell through and was
 * reported as a LEVEL01_LEVEL function -- an address attributed to an image
 * that is not even resident at the same time.  Containment in the materialising
 * image's ADDRESS RANGE therefore decides ownership first; only an address
 * outside that range may be searched for elsewhere.  An address the owning
 * image does not type as code is reported as no function at all, which is the
 * conservative answer, not a foreign image's function.
 */
static int owning_extent(const Image *prefer, uint32_t address,
                         const Image **image_out, const Extent **extent_out)
{
    if (prefer != NULL && image_contains(prefer, address)) {
        if (extent_of(prefer, address, extent_out)) {
            *image_out = prefer;
            return 1;
        }
        return 0;
    }
    /* Outside the materialising image, ownership is only decidable if exactly
     * one image claims the address.  Two overlays claiming it means the owner
     * depends on which one is resident, which no static receipt may guess. */
    size_t matches = 0;
    for (size_t i = 0; i < g_image_count; ++i) {
        const Image *image = &g_images[i];
        if (image == prefer)
            continue;
        const Extent *candidate = NULL;
        if (extent_of(image, address, &candidate)) {
            ++matches;
            *image_out = image;
            *extent_out = candidate;
        }
    }
    if (matches == 1)
        return 1;
    if (matches > 1) {
        *image_out = NULL;
        *extent_out = NULL;
        return -1;   /* claimed by several images at once: undecidable */
    }
    return 0;
}

static const char *owner_label(int outcome, const Image *owner)
{
    if (outcome > 0)
        return owner->id;
    if (outcome < 0)
        return "*ambiguous*";
    return "-";
}

static int hits_window(uint32_t address, uint32_t width)
{
    for (size_t i = 0; i < g_window_count; ++i) {
        if (address < g_windows[i].end && address + width > g_windows[i].start)
            return 1;
    }
    return 0;
}

static void add_extent(Image *image, uint32_t start, uint32_t end,
                       const char *type)
{
    if (image->extent_count == image->extent_capacity) {
        image->extent_capacity = image->extent_capacity ? image->extent_capacity * 2 : 64;
        image->extents = xrealloc(image->extents,
                                  image->extent_capacity * sizeof(Extent));
    }
    Extent *extent = &image->extents[image->extent_count++];
    extent->start = start;
    extent->end = end;
    snprintf(extent->type, sizeof(extent->type), "%s", type);
}

static void load_manifest(const char *path)
{
    FILE *handle = fopen(path, "r");
    if (handle == NULL)
        die_errno("open manifest");
    char line[1024];
    while (fgets(line, sizeof(line), handle) != NULL) {
        size_t length = strlen(line);
        while (length > 0 && (line[length - 1] == '\n' || line[length - 1] == '\r'))
            line[--length] = '\0';
        if (length == 0)
            continue;
        char *tag = strtok(line, "\t");
        if (tag == NULL)
            continue;
        if (strcmp(tag, "image") == 0) {
            if (g_image_count == MAX_IMAGES)
                die("too many images");
            char *id = strtok(NULL, "\t");
            char *file = strtok(NULL, "\t");
            char *base = strtok(NULL, "\t");
            char *size = strtok(NULL, "\t");
            if (id == NULL || file == NULL || base == NULL || size == NULL)
                die("malformed image row");
            Image *image = &g_images[g_image_count++];
            memset(image, 0, sizeof(*image));
            snprintf(image->id, sizeof(image->id), "%s", id);
            snprintf(image->path, sizeof(image->path), "%s", file);
            image->base = (uint32_t)strtoul(base, NULL, 16);
            image->size = (uint32_t)strtoul(size, NULL, 10);
            image->resident_start = image->base;
            image->resident_end = image->base + image->size;
        } else if (strcmp(tag, "extent") == 0) {
            char *id = strtok(NULL, "\t");
            char *start = strtok(NULL, "\t");
            char *end = strtok(NULL, "\t");
            char *type = strtok(NULL, "\t");
            if (id == NULL || start == NULL || end == NULL || type == NULL)
                die("malformed extent row");
            Image *image = find_image(id);
            if (image == NULL)
                die("extent names an unknown image");
            add_extent(image, (uint32_t)strtoul(start, NULL, 16),
                       (uint32_t)strtoul(end, NULL, 16), type);
        } else if (strcmp(tag, "resident") == 0) {
            char *id = strtok(NULL, "\t");
            char *start = strtok(NULL, "\t");
            char *end = strtok(NULL, "\t");
            if (id == NULL || start == NULL || end == NULL)
                die("malformed resident row");
            Image *image = find_image(id);
            if (image == NULL)
                die("resident row names an unknown image");
            image->resident_start = (uint32_t)strtoul(start, NULL, 16);
            image->resident_end = (uint32_t)strtoul(end, NULL, 16);
            if (image->resident_start < image->base ||
                image->resident_end > image->base + image->size ||
                image->resident_end <= image->resident_start)
                die("resident range is not inside the image");
        } else if (strcmp(tag, "window") == 0) {
            if (g_window_count == MAX_WINDOWS)
                die("too many windows");
            char *start = strtok(NULL, "\t");
            char *end = strtok(NULL, "\t");
            if (start == NULL || end == NULL)
                die("malformed window row");
            g_windows[g_window_count].start = (uint32_t)strtoul(start, NULL, 16);
            g_windows[g_window_count].end = (uint32_t)strtoul(end, NULL, 16);
            ++g_window_count;
        } else if (strcmp(tag, "gp") == 0) {
            char *value = strtok(NULL, "\t");
            if (value == NULL)
                die("malformed gp row");
            g_gp = (uint32_t)strtoul(value, NULL, 16);
        } else {
            die("unknown manifest row");
        }
    }
    if (ferror(handle))
        die_errno("read manifest");
    fclose(handle);
}

static void load_bytes(Image *image)
{
    FILE *handle = fopen(image->path, "rb");
    if (handle == NULL)
        die_errno("open image");
    image->bytes = xrealloc(NULL, image->size);
    size_t read = fread(image->bytes, 1, image->size, handle);
    if (read != image->size)
        die("image is shorter than its declared size");
    int extra = fgetc(handle);
    if (extra != EOF)
        die("image is longer than its declared size");
    fclose(handle);
}

enum {
    OP_SPECIAL = 0x00,
    OP_J = 0x02,
    OP_JAL = 0x03,
    OP_ADDI = 0x08,
    OP_ADDIU = 0x09,
    OP_SLTI = 0x0A,
    OP_SLTIU = 0x0B,
    OP_ANDI = 0x0C,
    OP_ORI = 0x0D,
    OP_XORI = 0x0E,
    OP_LUI = 0x0F
};

static int is_load(uint32_t op, uint32_t *width)
{
    switch (op) {
    case 0x20: case 0x24: *width = 1; return 1;   /* lb  lbu */
    case 0x21: case 0x25: *width = 2; return 1;   /* lh  lhu */
    case 0x23: case 0x22: case 0x26: *width = 4; return 1;  /* lw lwl lwr */
    default: return 0;
    }
}

static int is_store(uint32_t op, uint32_t *width)
{
    switch (op) {
    case 0x28: *width = 1; return 1;   /* sb */
    case 0x29: *width = 2; return 1;   /* sh */
    case 0x2B: case 0x2A: case 0x2E: *width = 4; return 1;  /* sw swl swr */
    default: return 0;
    }
}

static const char *mnemonic_of(uint32_t op)
{
    switch (op) {
    case 0x20: return "lb";
    case 0x21: return "lh";
    case 0x22: return "lwl";
    case 0x23: return "lw";
    case 0x24: return "lbu";
    case 0x25: return "lhu";
    case 0x26: return "lwr";
    case 0x28: return "sb";
    case 0x29: return "sh";
    case 0x2A: return "swl";
    case 0x2B: return "sw";
    case 0x2E: return "swr";
    default: return "?";
    }
}

/* A `jal`/`j` target is formed from the delay-slot PC, not the branch PC. */
static uint32_t jump_target(uint32_t pc, uint32_t word)
{
    return ((pc + 4) & 0xF0000000u) | ((word & 0x03FFFFFFu) << 2);
}

/* Is this word a control transfer, and what does it do to register state?
 *   0  not a transfer
 *   1  jal / jalr        -- returns here; clobbers the caller-saved set
 *   2  j / jr            -- does not return; the next word starts a new block
 *   3  conditional branch -- falls through, so state survives to the next word
 */
static int transfer_kind(uint32_t word)
{
    uint32_t op = word >> 26;
    if (op == OP_JAL)
        return 1;
    if (op == OP_J)
        return 2;
    if (op == OP_SPECIAL) {
        uint32_t funct = word & 0x3F;
        if (funct == 0x09)
            return 1;   /* jalr */
        if (funct == 0x08)
            return 2;   /* jr */
        return 0;
    }
    if (op == 0x01 || op == 0x04 || op == 0x05 || op == 0x06 || op == 0x07)
        return 3;
    return 0;
}

/*
 * Mark every word that some branch or jump can enter.
 *
 * Linear tracking through a fall-through is sound; arriving at a word some
 * OTHER path also enters is not, because that path may hold a different value
 * in the register.  Rather than assume, every branch target in the image is
 * marked and all tracked state is dropped on entry to one.  A `jr` target is
 * not marked -- it is unknown -- which is why the resulting census is
 * positive-only and its silence carries no weight.
 */
static void mark_block_entries(const Image *image, unsigned char *entry)
{
    size_t first = (image->resident_start - image->base) / 4;
    size_t last = (image->resident_end - image->base) / 4;
    for (size_t i = first; i < last; ++i) {
        uint32_t pc = image->base + (uint32_t)(i * 4);
        uint32_t word = read_le32(image->bytes + i * 4);
        uint32_t op = word >> 26;
        uint32_t target = 0;
        if (op == 0x01 || op == 0x04 || op == 0x05 || op == 0x06 || op == 0x07)
            target = pc + 4 + ((uint32_t)(int32_t)(int16_t)(word & 0xFFFF) << 2);
        else if (op == OP_J || op == OP_JAL)
            target = jump_target(pc, word);
        else
            continue;
        if (target >= image->resident_start && target < image->resident_end &&
            (target & 3) == 0)
            entry[(target - image->base) / 4] = 1;
    }
}

/*
 * Pass 1: function-pointer materialization census.
 *
 * `hi[reg]` holds a pending lui and the pc that set it; adjacency to the
 * completing addiu/ori is REQUIRED, exactly as in the frontier extractor's
 * binary supplement, because tracking a half-materialised value across a gap
 * means modelling every GPR write.  `val[reg]` holds a completed code address
 * and is killed the moment anything can redefine the register, so a stale value
 * can never be attributed to a later store.
 *
 * ⚠️ THE DELAY SLOT IS WHERE THE REGISTRATION HAPPENS.  MIPS executes the word
 * after a jump BEFORE control transfers, and this game's compiler fills those
 * slots with exactly the stores this census is looking for:
 *
 *     8004a56c: j     0x8004a620
 *     8004a570: sw    v0, 116(s1)     <- runs FIRST; v0 is the handler pointer
 *
 * Applying the jump's effect at the jump and then decoding the delay slot loses
 * every one of them -- eight actor-handler registrations at 0x8004A570..0x8004A618
 * in this image alone.  The transfer's effect is therefore DEFERRED until after
 * its delay slot, and a `jal`'s argument registers are read at the same point,
 * for the same reason.
 */
static void scan_function_pointers(const Image *image)
{
    uint32_t hi_value[32] = {0};
    uint32_t hi_pc[32] = {0};
    int hi_live[32] = {0};
    uint32_t val_value[32] = {0};
    uint32_t val_pc[32] = {0};
    int val_live[32] = {0};

    size_t words = image->size / 4;
    unsigned char *entry = xrealloc(NULL, words ? words : 1);
    memset(entry, 0, words ? words : 1);
    mark_block_entries(image, entry);

    int pending = 0;
    uint32_t pending_word = 0;
    uint32_t pending_pc = 0;

    size_t first = (image->resident_start - image->base) / 4;
    size_t last = (image->resident_end - image->base) / 4;
    for (size_t i = first; i < last; ++i) {
        uint32_t pc = image->base + (uint32_t)(i * 4);
        uint32_t word = read_le32(image->bytes + i * 4);
        uint32_t op = word >> 26;
        uint32_t rs = (word >> 21) & 31;
        uint32_t rt = (word >> 16) & 31;
        uint32_t rd = (word >> 11) & 31;
        int32_t simm = (int32_t)(int16_t)(word & 0xFFFF);
        uint32_t uimm = word & 0xFFFF;
        int in_delay_slot = pending != 0;

        if (!in_delay_slot && entry[i]) {
            memset(hi_live, 0, sizeof(hi_live));
            memset(val_live, 0, sizeof(val_live));
        }

        if (op == OP_LUI) {
            hi_value[rt] = uimm << 16;
            hi_pc[rt] = pc;
            hi_live[rt] = 1;
            val_live[rt] = 0;
        } else if ((op == OP_ADDIU || op == OP_ORI) && hi_live[rs] &&
                   hi_pc[rs] == pc - 4) {
            uint32_t value = op == OP_ADDIU ? hi_value[rs] + (uint32_t)simm
                                            : hi_value[rs] | uimm;
            hi_live[rs] = 0;
            hi_live[rt] = 0;
            const Image *owner = NULL;
            const Extent *extent = NULL;
            if (owning_extent(image, value, &owner, &extent) != 0) {
                val_value[rt] = value;
                val_pc[rt] = pc;
                val_live[rt] = 1;
            } else {
                val_live[rt] = 0;
            }
        } else {
            uint32_t width = 0;
            if (op == 0x2B && val_live[rt]) {
                const Image *owner = NULL;
                const Extent *extent = NULL;
                int own = owning_extent(image, val_value[rt], &owner, &extent);
                printf("fnptr\t%s\t0x%08X\t0x%08X\t%s\t0x%08X\tstore\t%u\t%d\t%s\t0x%08X\t%d\n",
                       image->id, val_pc[rt], val_value[rt],
                       owner_label(own, owner), own > 0 ? extent->start : 0u,
                       rs, (int)simm, "-", pc,
                       own > 0 && extent->start == val_value[rt] ? 1 : 0);
                val_live[rt] = 0;
            }
            /* Kill AFTER the access is evaluated: `sw v0, ofs(v0)` and
             * `lui v0,X / lw v0,ofs(v0)` both reuse the register being defined. */
            if (op == OP_ADDI || op == OP_ADDIU || op == OP_SLTI ||
                op == OP_SLTIU || op == OP_ANDI || op == OP_ORI ||
                op == OP_XORI || is_load(op, &width)) {
                hi_live[rt] = 0;
                val_live[rt] = 0;
            } else if (op == OP_SPECIAL && transfer_kind(word) == 0) {
                hi_live[rd] = 0;
                val_live[rd] = 0;
            }
        }

        if (in_delay_slot) {
            /* The transfer takes effect now, with the delay slot already run. */
            uint32_t pending_op = pending_word >> 26;
            uint32_t pending_rs = (pending_word >> 21) & 31;
            if (pending_op == OP_JAL) {
                for (uint32_t reg = 4; reg <= 7; ++reg) {
                    if (!val_live[reg])
                        continue;
                    const Image *owner = NULL;
                    const Extent *extent = NULL;
                    int own = owning_extent(image, val_value[reg], &owner, &extent);
                    printf("fnptr\t%s\t0x%08X\t0x%08X\t%s\t0x%08X\targument\t%u\t%d\t0x%08X\t0x%08X\t%d\n",
                           image->id, val_pc[reg], val_value[reg],
                           owner_label(own, owner), own > 0 ? extent->start : 0u,
                           reg, 0, jump_target(pending_pc, pending_word), pending_pc,
                           own > 0 && extent->start == val_value[reg] ? 1 : 0);
                }
            } else if (pending_op == OP_SPECIAL && (pending_word & 0x3F) == 0x09 &&
                       val_live[pending_rs]) {
                /* jalr rs -- the pointer is called through the register here,
                 * which is a call, not a registration. */
                const Image *owner = NULL;
                const Extent *extent = NULL;
                int own = owning_extent(image, val_value[pending_rs], &owner, &extent);
                printf("fnptr\t%s\t0x%08X\t0x%08X\t%s\t0x%08X\tjalr\t%u\t%d\t-\t0x%08X\t%d\n",
                       image->id, val_pc[pending_rs], val_value[pending_rs],
                       owner_label(own, owner), own > 0 ? extent->start : 0u,
                       pending_rs, 0, pending_pc,
                       own > 0 && extent->start == val_value[pending_rs] ? 1 : 0);
            }
            if (pending == 1) {
                for (uint32_t reg = 0; reg < 32; ++reg) {
                    if (reg == 1 || reg == 2 || reg == 3 ||
                        (reg >= 4 && reg <= 15) || reg == 24 || reg == 25 ||
                        reg == 31) {
                        hi_live[reg] = 0;
                        val_live[reg] = 0;
                    }
                }
            } else if (pending == 2) {
                memset(hi_live, 0, sizeof(hi_live));
                memset(val_live, 0, sizeof(val_live));
            }
            pending = 0;
        } else {
            int kind = transfer_kind(word);
            if (kind == 1 || kind == 2) {
                pending = kind;
                pending_word = word;
                pending_pc = pc;
            }
        }
    }
    free(entry);
}

/*
 * Pass 2: every memory reference in every unclaimed byte of the image.
 *
 * The complement of the typed extents is walked word by word.  Unlike pass 1
 * this is not positive-only: a load or store whose base cannot be proved is
 * emitted with provenance `unresolved`, so the consumer can refuse to call the
 * gap decided.
 */
static void scan_gaps(const Image *image)
{
    size_t count = image->extent_count;
    Extent *sorted = xrealloc(NULL, (count ? count : 1) * sizeof(Extent));
    memcpy(sorted, image->extents, count * sizeof(Extent));
    qsort(sorted, count, sizeof(Extent), extent_compare);

    uint32_t cursor = image->resident_start;
    uint32_t limit = image->resident_end;
    for (size_t i = 0; i <= count; ++i) {
        uint32_t next = i < count ? sorted[i].start : limit;
        if (next < cursor)
            next = cursor;
        if (next > limit)
            next = limit;
        if (next > cursor) {
            uint32_t gap_start = cursor;
            uint32_t gap_end = next < limit ? next : limit;
            if (gap_end > gap_start) {
                printf("gap\t%s\t0x%08X\t0x%08X\t%u\n", image->id, gap_start,
                       gap_end, gap_end - gap_start);
                uint32_t hi_value[32] = {0};
                uint32_t hi_pc[32] = {0};
                int hi_live[32] = {0};
                for (uint32_t pc = gap_start; pc + 4 <= gap_end; pc += 4) {
                    uint32_t word = read_le32(image->bytes + (pc - image->base));
                    uint32_t op = word >> 26;
                    uint32_t rs = (word >> 21) & 31;
                    uint32_t rt = (word >> 16) & 31;
                    uint32_t rd = (word >> 11) & 31;
                    int32_t simm = (int32_t)(int16_t)(word & 0xFFFF);
                    uint32_t width = 0;
                    if (op == OP_LUI) {
                        hi_value[rt] = (word & 0xFFFF) << 16;
                        hi_pc[rt] = pc;
                        hi_live[rt] = 1;
                        continue;
                    }
                    int load = is_load(op, &width);
                    int store = load ? 0 : is_store(op, &width);
                    if (load || store) {
                        const char *provenance = "unresolved";
                        uint32_t effective = 0;
                        int resolved = 0;
                        if (rs == 28) {
                            effective = g_gp + (uint32_t)simm;
                            provenance = "gp_relative";
                            resolved = 1;
                        } else if (hi_live[rs] && hi_pc[rs] == pc - 4) {
                            effective = hi_value[rs] + (uint32_t)simm;
                            provenance = "adjacent_lui";
                            resolved = 1;
                        }
                        printf("gapref\t%s\t0x%08X\t%s\t%u\t%s\t%u\t%d\t%s\t0x%08X\t%d\n",
                               image->id, pc, mnemonic_of(op), width,
                               load ? "read" : "write", rs, (int)simm,
                               provenance, effective,
                               resolved && hits_window(effective, width) ? 1 : 0);
                    }
                    if (op == OP_ADDI || op == OP_ADDIU || op == OP_SLTI ||
                        op == OP_SLTIU || op == OP_ANDI || op == OP_ORI ||
                        op == OP_XORI || load) {
                        hi_live[rt] = 0;
                    } else if (op == OP_SPECIAL) {
                        hi_live[rd] = 0;
                    } else if (op == OP_JAL || op == OP_J) {
                        memset(hi_live, 0, sizeof(hi_live));
                    }
                }
            }
        }
        if (i < count && sorted[i].end > cursor)
            cursor = sorted[i].end;
        if (cursor >= limit)
            break;
    }
    free(sorted);
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s MANIFEST\n", argv[0]);
        return 2;
    }
    load_manifest(argv[1]);
    if (g_image_count == 0)
        die("manifest declares no image");
    for (size_t i = 0; i < g_image_count; ++i)
        load_bytes(&g_images[i]);
    for (size_t i = 0; i < g_image_count; ++i) {
        Image *image = &g_images[i];
        printf("image\t%s\t%u\t0x%08X\t%zu\t0x%08X\t0x%08X\n", image->id,
               image->size, image->base, image->extent_count,
               image->resident_start, image->resident_end);
        scan_function_pointers(image);
        scan_gaps(image);
    }
    for (size_t i = 0; i < g_image_count; ++i) {
        free(g_images[i].bytes);
        free(g_images[i].extents);
    }
    return 0;
}
