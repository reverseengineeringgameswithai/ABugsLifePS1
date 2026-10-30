/* CD_set_test_parmnum @ 0x8006F59C — stores a0 into the CD test-parm-count
 * global (0x80081B70) (PsyQ libcd). Matching reimplementation. Pure setter.
 *   lui at,0x8008; sw a0,0x1b70(at); jr ra; nop
 */
extern int g_80081b70;
void CD_set_test_parmnum(int a0) { g_80081b70 = a0; }
