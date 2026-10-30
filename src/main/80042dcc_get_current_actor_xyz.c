/* get_current_actor_xyz @ 0x80042dcc - copy XYZ of the last active actor (index
 * *pn) into *ox/*oy/*oz. Records are 836 B; holding &index in a pointer keeps its
 * base register live, and the int* stores force a reload between fields. */
typedef struct { int x, y, z; char pad[824]; } Actor;   /* 836-byte record */
extern Actor g_8009c894[];
extern short g_800a658c;         /* active actor count/index */

void get_current_actor_xyz(int *ox, int *oy, int *oz)
{
    short *pn = &g_800a658c;

    if (*pn > 0) {
        *ox = g_8009c894[*pn - 1].x;
        *oy = g_8009c894[*pn - 1].y;
        *oz = g_8009c894[*pn - 1].z;
    }
}
