/*
 * phase4_e03_ot_walk.c -- independent OT linked-list walker (E03 cross-check).
 *
 * Second implementation of "what is in this frame's ordering table", from the
 * RAM side: walks the GPU DMA linked list exactly as DMA channel 2 sync-mode-2
 * would (tag = u32 at node; size = tag>>24 payload words; next = tag&0xFFFFFF),
 * decoding each payload's GP0 opcode. Diffed against gp0Trace's dispatch-time
 * stream by tools/phase4_e03_crosscheck.py -- agreement proves both readings
 * (the region_provenance.c double-implementation pattern).
 *
 * Input: a 2 MiB main-RAM dump (file offset = vaddr - 0x80000000) and the OT
 * head vaddr (the frame's first DMA source address from gp0Trace).
 *
 * Output: JSON on stdout -- node/packet totals, per-opcode counts, zero-size
 * link-node count (the ClearOTag'd depth-bucket skeleton), and the node
 * address extent, so the depth-bucket table length becomes measurable.
 *
 * Build: cc -O2 -o /tmp/ot_walk tools/phase4_e03_ot_walk.c
 * Usage: /tmp/ot_walk <ram.bin> <head_vaddr_hex>
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RAM_BASE 0x80000000u
#define RAM_SIZE 0x00200000u
#define MAX_NODES 2000000u
#define TERMINATOR 0x00FFFFFFu

static uint8_t ram[RAM_SIZE];

static uint32_t rd32(uint32_t vaddr) {
    uint32_t off = vaddr - RAM_BASE;
    if (off > RAM_SIZE - 4) { fprintf(stderr, "OOB read 0x%08x\n", vaddr); exit(3); }
    uint32_t v;
    memcpy(&v, ram + off, 4);
    return v;
}

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: %s ram.bin head_vaddr_hex\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f || fread(ram, 1, RAM_SIZE, f) != RAM_SIZE) { fprintf(stderr, "bad ram dump\n"); return 2; }
    fclose(f);
    uint32_t head = (uint32_t)strtoul(argv[2], NULL, 16);

    /* visited bitmap: one bit per word address */
    static uint8_t seen[RAM_SIZE / 32];
    uint64_t opcode_count[256] = {0};
    uint64_t nodes = 0, packets = 0, empty_nodes = 0, payload_words = 0;
    uint32_t node = head, min_node = 0xFFFFFFFF, max_node = 0;
    uint64_t empty_run_max = 0, empty_run_cur = 0;
    int cycle = 0, oob = 0;

    while (nodes < MAX_NODES) {
        uint32_t off = node - RAM_BASE;
        if (node < RAM_BASE || off > RAM_SIZE - 4 || (node & 3)) { oob = 1; break; }
        uint32_t bit = off >> 2;
        if (seen[bit >> 3] & (1u << (bit & 7))) { cycle = 1; break; }
        seen[bit >> 3] |= (1u << (bit & 7));

        uint32_t tag = rd32(node);
        uint32_t size = tag >> 24;
        uint32_t next = tag & 0x00FFFFFFu;
        nodes++;
        if (node < min_node) min_node = node;
        if (node > max_node) max_node = node;
        if (size == 0) {
            empty_nodes++;
            empty_run_cur++;
            if (empty_run_cur > empty_run_max) empty_run_max = empty_run_cur;
        } else {
            empty_run_cur = 0;
            payload_words += size;
            /* first payload word's top byte = GP0 opcode of the packet;
             * a node may hold several logical GP0 commands back-to-back, but
             * family accounting by leading opcode matches gp0Trace's
             * dispatch-time grouping closely enough to diff -- the
             * cross-check script consumes words per command length. */
            for (uint32_t w = 0; w < size; ) {
                uint32_t word = rd32(node + 4 + 4 * w);
                uint8_t op = word >> 24;
                opcode_count[op]++;
                packets++;
                /* consume this command's remaining words inside the node */
                uint32_t len = 1;
                if (op >= 0x20 && op <= 0x3F) {
                    uint32_t verts = (op & 0x08) ? 4 : 3;
                    uint32_t vwords = 1 + ((op & 0x04) ? 1 : 0);   /* xy + uv */
                    len = 1 + verts * vwords + ((op & 0x10) ? verts - 1 : 0);
                } else if (op >= 0x60 && op <= 0x7F) {
                    len = 2 + ((op & 0x04) ? 1 : 0) + (((op & 0x18) == 0) ? 1 : 0);
                } else if (op >= 0x40 && op <= 0x5F) {
                    len = 3 + ((op & 0x10) ? 1 : 0); /* simple line forms */
                } else if (op == 0x02) {
                    len = 3;
                } else if (op >= 0xA0 && op <= 0xBF) {
                    len = 3;
                } else if (op >= 0x80 && op <= 0x9F) {
                    len = 4;
                }
                if (len > size - w) len = size - w; /* clamp: trust node size */
                w += len;
            }
        }
        if (next == TERMINATOR) { node = 0; break; }
        node = RAM_BASE | next;
    }

    printf("{\n \"head\": \"0x%08x\",\n \"nodes\": %llu,\n \"empty_link_nodes\": %llu,\n"
           " \"max_empty_run\": %llu,\n \"packets\": %llu,\n \"payload_words\": %llu,\n"
           " \"min_node\": \"0x%08x\",\n \"max_node\": \"0x%08x\",\n"
           " \"terminated\": %s,\n \"cycle\": %s,\n \"oob\": %s,\n \"opcodes\": {",
           head, (unsigned long long)nodes, (unsigned long long)empty_nodes,
           (unsigned long long)empty_run_max, (unsigned long long)packets,
           (unsigned long long)payload_words, min_node, max_node,
           node == 0 ? "true" : "false", cycle ? "true" : "false", oob ? "true" : "false");
    int first = 1;
    for (int i = 0; i < 256; i++)
        if (opcode_count[i]) {
            printf("%s\n  \"0x%02x\": %llu", first ? "" : ",", i,
                   (unsigned long long)opcode_count[i]);
            first = 0;
        }
    printf("\n }\n}\n");
    return (cycle || oob) ? 1 : 0;
}
