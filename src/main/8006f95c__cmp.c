/* _cmp @ 0x8006f95c - compare 12 bytes; returns 1 when equal. */
extern int sub_8005f75c(void *a, void *b, int n);
int _cmp(void *a, void *b) { return sub_8005f75c(a, b, 12) == 0; }
