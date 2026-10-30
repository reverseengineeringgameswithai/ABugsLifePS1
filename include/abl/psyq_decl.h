#ifndef ABL_PSYQ_DECL_H
#define ABL_PSYQ_DECL_H

/* Clean-room declarations derived from the documented PlayStation API and the
 * retail call ABI. This is deliberately small; it is not a Sony header copy. */
typedef unsigned char u_char;
typedef unsigned short u_short;
typedef unsigned int u_int;
typedef unsigned long u_long;

typedef struct ABL_CdlLOC {
    u_char minute;
    u_char second;
    u_char sector;
    u_char track;
} CdlLOC;

typedef struct ABL_CdlFILTER {
    u_char file;
    u_char chan;
} CdlFILTER;

#if ABL_PSYQ_DECL_PROFILE == 2
#define ABL_PSYQ_EXTERN(ret, name, args) extern ret name()
#else
#define ABL_PSYQ_EXTERN(ret, name, args) extern ret name args
#endif

ABL_PSYQ_EXTERN(int, CdControl, (u_char com, u_char *param, u_char *result));
ABL_PSYQ_EXTERN(int, CdControlF, (u_char com, u_char *param));
ABL_PSYQ_EXTERN(int, CdControlB, (u_char com, u_char *param, u_char *result));
ABL_PSYQ_EXTERN(int, CdMix, (void *vol));
ABL_PSYQ_EXTERN(CdlLOC *, CdIntToPos, (int sector, CdlLOC *loc));
ABL_PSYQ_EXTERN(int, SsSetSerialVol, (int s_num, short voll, short volr));

#endif
