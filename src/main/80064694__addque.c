/* _addque @ 0x80064694 - enqueue with priority 0. */
extern void sub_800646b8(int a, int b, int c, int d);
void _addque(int a, int b, int c) { sub_800646b8(a, b, 0, c); }
