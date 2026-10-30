/* CdGetSector2 @ 0x8006dcd0 - fetch a sector; returns 1 on success (helper==0). */
extern int sub_8006f4ac();
int CdGetSector2() { return sub_8006f4ac() == 0; }
