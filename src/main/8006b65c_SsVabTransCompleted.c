/* SsVabTransCompleted @ 0x8006b65c - poll VAB transfer completion (16-bit id). */
extern int sub_8006cd98(int vabId);
short SsVabTransCompleted(int vabId) { return (short)sub_8006cd98((short)vabId); }
