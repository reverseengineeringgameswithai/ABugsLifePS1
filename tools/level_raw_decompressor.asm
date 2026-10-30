0x8001a1dc  sll zero, zero, 0             
0x8001a1e0  addiu sp, sp, -112            
0x8001a1e4  sll zero, zero, 0             
0x8001a1e8  sw v0, 0x0(sp)                
0x8001a1ec  sw v1, 0x4(sp)                
0x8001a1f0  sw a0, 0x8(sp)                
0x8001a1f4  sw a1, 0xc(sp)                
0x8001a1f8  sw a2, 0x10(sp)               
0x8001a1fc  sw a3, 0x14(sp)               
0x8001a200  sw t0, 0x18(sp)               
0x8001a204  sw t1, 0x1c(sp)               
0x8001a208  sw t2, 0x20(sp)               
0x8001a20c  sw t3, 0x24(sp)               
0x8001a210  sw t4, 0x28(sp)               
0x8001a214  sw t5, 0x2c(sp)               
0x8001a218  sw t6, 0x30(sp)               
0x8001a21c  sw t7, 0x34(sp)               
0x8001a220  sw s0, 0x38(sp)               
0x8001a224  sw s1, 0x3c(sp)               
0x8001a228  sw s2, 0x40(sp)               
0x8001a22c  sw s3, 0x44(sp)               
0x8001a230  sw s4, 0x48(sp)               
0x8001a234  sw s5, 0x4c(sp)               
0x8001a238  sw s6, 0x50(sp)               
0x8001a23c  sw s7, 0x54(sp)               
0x8001a240  sw t8, 0x58(sp)               
0x8001a244  sw t9, 0x5c(sp)               
0x8001a248  sw k0, 0x60(sp)               
0x8001a24c  sw k1, 0x64(sp)               
0x8001a250  sw gp, 0x68(sp)               
0x8001a254  sw ra, 0x6c(sp)               
0x8001a258  sll zero, zero, 0             
0x8001a25c  addu t6, a0, zero             
0x8001a260  addu s1, a1, zero             
0x8001a264  addiu t5, zero, 0             
0x8001a268  addu t3, sp, zero             
0x8001a26c  addiu sp, sp, -128            
0x8001a270  lbu t5, 0x0(t6)               
0x8001a274  lbu t4, 0x1(t6)               
0x8001a278  lbu s2, 0x2(t6)               
0x8001a27c  lbu t7, 0x3(t6)               
0x8001a280  sll t5, t5, 24                
0x8001a284  sll t4, t4, 16                
0x8001a288  sll s2, s2, 8                 
0x8001a28c  or t5, t5, t4                 
0x8001a290  or t5, t5, s2                 
0x8001a294  or t5, t5, t7                 
0x8001a298  addiu t6, t6, 4               
0x8001a29c  sw t5, 0x0(t3)                
0x8001a2a0  addu v1, t6, zero             
0x8001a2a4  addi v1, v1, 10               
0x8001a2a8  addu a1, s1, zero             
0x8001a2ac  addu a2, a1, zero             
0x8001a2b0  add a2, a2, t5                
0x8001a2b4  lbu t5, 0x0(t6)               
0x8001a2b8  lbu t4, 0x1(t6)               
0x8001a2bc  lbu s2, 0x2(t6)               
0x8001a2c0  lbu t7, 0x3(t6)               
0x8001a2c4  sll t5, t5, 24                
0x8001a2c8  sll t4, t4, 16                
0x8001a2cc  sll s2, s2, 8                 
0x8001a2d0  or t5, t5, t4                 
0x8001a2d4  or t5, t5, s2                 
0x8001a2d8  or t5, t5, t7                 
0x8001a2dc  addiu t6, t6, 4               
0x8001a2e0  addu a0, v1, zero             
0x8001a2e4  add a0, a0, t5                
0x8001a2e8  addi t3, t3, -2               
0x8001a2ec  sh zero, 0x0(t3)              
0x8001a2f0  lui t2, 0xffff                
0x8001a2f4  ori t2, t2, 0xff00            
0x8001a2f8  addiu t7, zero, 1             
0x8001a2fc  lbu t2, 0x0(v1)               
0x8001a300  addi v1, v1, 1                
0x8001a304  addu t2, t2, t2               
0x8001a308  addu t2, t2, t7               
0x8001a30c  addu t2, t2, t2               
0x8001a310  srl t7, t2, 8                 
0x8001a314  j 0x8001a658                   -> 0x8001a658
0x8001a318  andi t7, t7, 0x0001           
0x8001a31c  lbu t2, 0x0(v1)               
0x8001a320  addi v1, v1, 1                
0x8001a324  addu t2, t2, t2               
0x8001a328  addu t2, t2, t7               
0x8001a32c  srl t7, t2, 8                 
0x8001a330  j 0x8001a418                   -> 0x8001a418
0x8001a334  andi t7, t7, 0x0001           
0x8001a338  lbu t2, 0x0(v1)               
0x8001a33c  addi v1, v1, 1                
0x8001a340  addu t2, t2, t2               
0x8001a344  addu t2, t2, t7               
0x8001a348  srl t7, t2, 8                 
0x8001a34c  j 0x8001a488                   -> 0x8001a488
0x8001a350  andi t7, t7, 0x0001           
0x8001a354  lbu t2, 0x0(v1)               
0x8001a358  addi v1, v1, 1                
0x8001a35c  addu t2, t2, t2               
0x8001a360  addu t2, t2, t7               
0x8001a364  srl t7, t2, 8                 
0x8001a368  j 0x8001a4a8                   -> 0x8001a4a8
0x8001a36c  andi t7, t7, 0x0001           
0x8001a370  lbu t2, 0x0(v1)               
0x8001a374  addi v1, v1, 1                
0x8001a378  addu t2, t2, t2               
0x8001a37c  addu t2, t2, t7               
0x8001a380  srl t7, t2, 8                 
0x8001a384  j 0x8001a4cc                   -> 0x8001a4cc
0x8001a388  andi t7, t7, 0x0001           
0x8001a38c  lbu t2, 0x0(v1)               
0x8001a390  addi v1, v1, 1                
0x8001a394  addu t2, t2, t2               
0x8001a398  addu t2, t2, t7               
0x8001a39c  srl t7, t2, 8                 
0x8001a3a0  j 0x8001a500                   -> 0x8001a500
0x8001a3a4  andi t7, t7, 0x0001           
0x8001a3a8  lbu t2, 0x0(v1)               
0x8001a3ac  addi v1, v1, 1                
0x8001a3b0  addu t2, t2, t2               
0x8001a3b4  addu t2, t2, t7               
0x8001a3b8  srl t7, t2, 8                 
0x8001a3bc  j 0x8001a520                   -> 0x8001a520
0x8001a3c0  andi t7, t7, 0x0001           
0x8001a3c4  lbu t2, 0x0(v1)               
0x8001a3c8  addi v1, v1, 1                
0x8001a3cc  addu t2, t2, t2               
0x8001a3d0  addu t2, t2, t7               
0x8001a3d4  srl t7, t2, 8                 
0x8001a3d8  j 0x8001a540                   -> 0x8001a540
0x8001a3dc  andi t7, t7, 0x0001           
0x8001a3e0  lbu t2, 0x0(v1)               
0x8001a3e4  addi v1, v1, 1                
0x8001a3e8  addu t2, t2, t2               
0x8001a3ec  addu t2, t2, t7               
0x8001a3f0  srl t7, t2, 8                 
0x8001a3f4  j 0x8001a56c                   -> 0x8001a56c
0x8001a3f8  andi t7, t7, 0x0001           
0x8001a3fc  addiu t0, zero, 3             
0x8001a400  addu t2, t2, t2               
0x8001a404  srl t7, t2, 8                 
0x8001a408  andi t7, t7, 0x0001           
0x8001a40c  andi t2, t2, 0x00ff           
0x8001a410  beq zero, t2, 0x8001a31c       -> 0x8001a31c
0x8001a414  sll zero, zero, 0             
0x8001a418  addu t1, t1, t1               
0x8001a41c  addu t1, t1, t7               
0x8001a420  srl t7, t1, 16                
0x8001a424  andi t7, t7, 0x0001           
0x8001a428  addi t0, t0, -1               
0x8001a42c  bgez t0, 0x8001a400            -> 0x8001a400
0x8001a430  sll zero, zero, 0             
0x8001a434  addi t1, t1, 2                
0x8001a438  lbu t4, 0x0(v1)               
0x8001a43c  lbu s2, 0x1(v1)               
0x8001a440  sb t4, 0x0(a1)                
0x8001a444  sb s2, 0x1(a1)                
0x8001a448  lbu t4, 0x2(v1)               
0x8001a44c  lbu s2, 0x3(v1)               
0x8001a450  sb t4, 0x2(a1)                
0x8001a454  sb s2, 0x3(a1)                
0x8001a458  addiu v1, v1, 4               
0x8001a45c  addi t1, t1, -1               
0x8001a460  bgez t1, 0x8001a438            -> 0x8001a438
0x8001a464  addi a1, a1, 4                
0x8001a468  j 0x8001a658                   -> 0x8001a658
0x8001a46c  sll zero, zero, 0             
0x8001a470  addu t2, t2, t2               
0x8001a474  srl t7, t2, 8                 
0x8001a478  andi t7, t7, 0x0001           
0x8001a47c  andi t2, t2, 0x00ff           
0x8001a480  beq zero, t2, 0x8001a338       -> 0x8001a338
0x8001a484  sll zero, zero, 0             
0x8001a488  addu t0, t0, t0               
0x8001a48c  addu t0, t0, t7               
0x8001a490  addu t2, t2, t2               
0x8001a494  srl t7, t2, 8                 
0x8001a498  andi t7, t7, 0x0001           
0x8001a49c  andi t2, t2, 0x00ff           
0x8001a4a0  beq zero, t2, 0x8001a354       -> 0x8001a354
0x8001a4a4  sll zero, zero, 0             
0x8001a4a8  beq zero, t7, 0x8001a4e8       -> 0x8001a4e8
0x8001a4ac  sll zero, zero, 0             
0x8001a4b0  addi t0, t0, -1               
0x8001a4b4  add t2, t2, t2                
0x8001a4b8  srl t7, t2, 8                 
0x8001a4bc  andi t7, t7, 0x0001           
0x8001a4c0  andi t2, t2, 0x00ff           
0x8001a4c4  beq zero, t2, 0x8001a370       -> 0x8001a370
0x8001a4c8  sll zero, zero, 0             
0x8001a4cc  addu t0, t0, t0               
0x8001a4d0  addu t0, t0, t7               
0x8001a4d4  srl t7, t0, 16                
0x8001a4d8  andi t7, t7, 0x0001           
0x8001a4dc  addi t4, t0, -9               
0x8001a4e0  beq zero, t4, 0x8001a3fc       -> 0x8001a3fc
0x8001a4e4  sll zero, zero, 0             
0x8001a4e8  addu t2, t2, t2               
0x8001a4ec  srl t7, t2, 8                 
0x8001a4f0  andi t7, t7, 0x0001           
0x8001a4f4  andi t2, t2, 0x00ff           
0x8001a4f8  beq zero, t2, 0x8001a38c       -> 0x8001a38c
0x8001a4fc  sll zero, zero, 0             
0x8001a500  beq zero, t7, 0x8001a58c       -> 0x8001a58c
0x8001a504  sll zero, zero, 0             
0x8001a508  addu t2, t2, t2               
0x8001a50c  srl t7, t2, 8                 
0x8001a510  andi t7, t7, 0x0001           
0x8001a514  andi t2, t2, 0x00ff           
0x8001a518  beq zero, t2, 0x8001a3a8       -> 0x8001a3a8
0x8001a51c  sll zero, zero, 0             
0x8001a520  addu t1, t1, t1               
0x8001a524  addu t1, t1, t7               
0x8001a528  addu t2, t2, t2               
0x8001a52c  srl t7, t2, 8                 
0x8001a530  andi t7, t7, 0x0001           
0x8001a534  andi t2, t2, 0x00ff           
0x8001a538  beq zero, t2, 0x8001a3c4       -> 0x8001a3c4
0x8001a53c  sll zero, zero, 0             
0x8001a540  bne zero, t7, 0x8001a724       -> 0x8001a724
0x8001a544  sll zero, zero, 0             
0x8001a548  bne zero, t1, 0x8001a57c       -> 0x8001a57c
0x8001a54c  sll zero, zero, 0             
0x8001a550  addi t1, t1, 1                
0x8001a554  addu t2, t2, t2               
0x8001a558  srl t7, t2, 8                 
0x8001a55c  andi t7, t7, 0x0001           
0x8001a560  andi t2, t2, 0x00ff           
0x8001a564  beq zero, t2, 0x8001a3e0       -> 0x8001a3e0
0x8001a568  sll zero, zero, 0             
0x8001a56c  addu t1, t1, t1               
0x8001a570  addu t1, t1, t7               
0x8001a574  srl t7, t1, 16                
0x8001a578  andi t7, t7, 0x0001           
0x8001a57c  sll t4, t1, 8                 
0x8001a580  andi t4, t4, 0xff00           
0x8001a584  srl t1, t1, 8                 
0x8001a588  or t1, t1, t4                 
0x8001a58c  andi s3, t1, 0xff00           
0x8001a590  lbu t1, 0x0(v1)               
0x8001a594  addiu v1, v1, 1               
0x8001a598  or t1, t1, s3                 
0x8001a59c  addu t6, a1, zero             
0x8001a5a0  sub t6, t6, t1                
0x8001a5a4  addi t6, t6, -1               
0x8001a5a8  andi t7, t0, 0x0001           
0x8001a5ac  srl t0, t0, 1                 
0x8001a5b0  beq zero, t7, 0x8001a5c8       -> 0x8001a5c8
0x8001a5b4  sll zero, zero, 0             
0x8001a5b8  lbu t4, 0x0(t6)               
0x8001a5bc  addi t6, t6, 1                
0x8001a5c0  sb t4, 0x0(a1)                
0x8001a5c4  addi a1, a1, 1                
0x8001a5c8  addi t0, t0, -1               
0x8001a5cc  bne zero, t1, 0x8001a600       -> 0x8001a600
0x8001a5d0  sll zero, zero, 0             
0x8001a5d4  andi s3, t1, 0xff00           
0x8001a5d8  lbu t1, 0x0(t6)               
0x8001a5dc  sll zero, zero, 0             
0x8001a5e0  or t1, t1, s3                 
0x8001a5e4  sb t1, 0x0(a1)                
0x8001a5e8  addi t0, t0, -1               
0x8001a5ec  sb t1, 0x1(a1)                
0x8001a5f0  bgez t0, 0x8001a5e4            -> 0x8001a5e4
0x8001a5f4  addi a1, a1, 2                
0x8001a5f8  j 0x8001a658                   -> 0x8001a658
0x8001a5fc  sll zero, zero, 0             
0x8001a600  lbu s2, 0x1(t6)               
0x8001a604  lbu t4, 0x0(t6)               
0x8001a608  sb s2, 0x1(a1)                
0x8001a60c  sb t4, 0x0(a1)                
0x8001a610  addi t6, t6, 2                
0x8001a614  addi t0, t0, -1               
0x8001a618  bgez t0, 0x8001a600            -> 0x8001a600
0x8001a61c  addi a1, a1, 2                
0x8001a620  j 0x8001a658                   -> 0x8001a658
0x8001a624  sll zero, zero, 0             
0x8001a628  lbu t2, 0x0(v1)               
0x8001a62c  addi v1, v1, 1                
0x8001a630  addu t2, t2, t2               
0x8001a634  addu t2, t2, t7               
0x8001a638  srl t7, t2, 8                 
0x8001a63c  andi t7, t7, 0x0001           
0x8001a640  bne zero, t7, 0x8001a69c       -> 0x8001a69c
0x8001a644  sll zero, zero, 0             
0x8001a648  lbu t4, 0x0(v1)               
0x8001a64c  addi v1, v1, 1                
0x8001a650  sb t4, 0x0(a1)                
0x8001a654  addi a1, a1, 1                
0x8001a658  addu t2, t2, t2               
0x8001a65c  srl t7, t2, 8                 
0x8001a660  andi t7, t7, 0x0001           
0x8001a664  bne zero, t7, 0x8001a690       -> 0x8001a690
0x8001a668  sll zero, zero, 0             
0x8001a66c  lbu t4, 0x0(v1)               
0x8001a670  addi v1, v1, 1                
0x8001a674  sb t4, 0x0(a1)                
0x8001a678  addi a1, a1, 1                
0x8001a67c  addu t2, t2, t2               
0x8001a680  srl t7, t2, 8                 
0x8001a684  andi t7, t7, 0x0001           
0x8001a688  beq zero, t7, 0x8001a648       -> 0x8001a648
0x8001a68c  sll zero, zero, 0             
0x8001a690  andi t2, t2, 0x00ff           
0x8001a694  beq zero, t2, 0x8001a628       -> 0x8001a628
0x8001a698  sll zero, zero, 0             
0x8001a69c  addiu t0, zero, 2             
0x8001a6a0  addiu t1, zero, 0             
0x8001a6a4  addu t2, t2, t2               
0x8001a6a8  srl t7, t2, 8                 
0x8001a6ac  andi t7, t7, 0x0001           
0x8001a6b0  andi t2, t2, 0x00ff           
0x8001a6b4  beq zero, t2, 0x8001a778       -> 0x8001a778
0x8001a6b8  sll zero, zero, 0             
0x8001a6bc  beq zero, t7, 0x8001a470       -> 0x8001a470
0x8001a6c0  sll zero, zero, 0             
0x8001a6c4  addu t2, t2, t2               
0x8001a6c8  srl t7, t2, 8                 
0x8001a6cc  andi t7, t7, 0x0001           
0x8001a6d0  andi t2, t2, 0x00ff           
0x8001a6d4  beq zero, t2, 0x8001a794       -> 0x8001a794
0x8001a6d8  sll zero, zero, 0             
0x8001a6dc  beq zero, t7, 0x8001a58c       -> 0x8001a58c
0x8001a6e0  sll zero, zero, 0             
0x8001a6e4  addi t0, t0, 1                
0x8001a6e8  add t2, t2, t2                
0x8001a6ec  srl t7, t2, 8                 
0x8001a6f0  andi t7, t7, 0x0001           
0x8001a6f4  andi t2, t2, 0x00ff           
0x8001a6f8  beq zero, t2, 0x8001a7b0       -> 0x8001a7b0
0x8001a6fc  sll zero, zero, 0             
0x8001a700  beq zero, t7, 0x8001a4e8       -> 0x8001a4e8
0x8001a704  sll zero, zero, 0             
0x8001a708  lbu t0, 0x0(v1)               
0x8001a70c  addi v1, v1, 1                
0x8001a710  sll zero, zero, 0             
0x8001a714  beq zero, t0, 0x8001a804       -> 0x8001a804
0x8001a718  addi t0, t0, 8                
0x8001a71c  j 0x8001a4e8                   -> 0x8001a4e8
0x8001a720  sll zero, zero, 0             
0x8001a724  addu t2, t2, t2               
0x8001a728  srl t7, t2, 8                 
0x8001a72c  andi t7, t7, 0x0001           
0x8001a730  andi t2, t2, 0x00ff           
0x8001a734  beq zero, t2, 0x8001a7cc       -> 0x8001a7cc
0x8001a738  sll zero, zero, 0             
0x8001a73c  addu t1, t1, t1               
0x8001a740  addu t1, t1, t7               
0x8001a744  srl t7, t1, 16                
0x8001a748  andi t7, t7, 0x0001           
0x8001a74c  ori t1, t1, 0x0004            
0x8001a750  addu t2, t2, t2               
0x8001a754  srl t7, t2, 8                 
0x8001a758  andi t7, t7, 0x0001           
0x8001a75c  andi t2, t2, 0x00ff           
0x8001a760  beq zero, t2, 0x8001a7e8       -> 0x8001a7e8
0x8001a764  sll zero, zero, 0             
0x8001a768  bne zero, t7, 0x8001a57c       -> 0x8001a57c
0x8001a76c  sll zero, zero, 0             
0x8001a770  j 0x8001a554                   -> 0x8001a554
0x8001a774  sll zero, zero, 0             
0x8001a778  lbu t2, 0x0(v1)               
0x8001a77c  addi v1, v1, 1                
0x8001a780  addu t2, t2, t2               
0x8001a784  addu t2, t2, t7               
0x8001a788  srl t7, t2, 8                 
0x8001a78c  j 0x8001a6bc                   -> 0x8001a6bc
0x8001a790  andi t7, t7, 0x0001           
0x8001a794  lbu t2, 0x0(v1)               
0x8001a798  addi v1, v1, 1                
0x8001a79c  addu t2, t2, t2               
0x8001a7a0  addu t2, t2, t7               
0x8001a7a4  srl t7, t2, 8                 
0x8001a7a8  j 0x8001a6dc                   -> 0x8001a6dc
0x8001a7ac  andi t7, t7, 0x0001           
0x8001a7b0  lbu t2, 0x0(v1)               
0x8001a7b4  addi v1, v1, 1                
0x8001a7b8  addu t2, t2, t2               
0x8001a7bc  addu t2, t2, t7               
0x8001a7c0  srl t7, t2, 8                 
0x8001a7c4  j 0x8001a700                   -> 0x8001a700
0x8001a7c8  andi t7, t7, 0x0001           
0x8001a7cc  lbu t2, 0x0(v1)               
0x8001a7d0  addi v1, v1, 1                
0x8001a7d4  addu t2, t2, t2               
0x8001a7d8  addu t2, t2, t7               
0x8001a7dc  srl t7, t2, 8                 
0x8001a7e0  j 0x8001a73c                   -> 0x8001a73c
0x8001a7e4  andi t7, t7, 0x0001           
0x8001a7e8  lbu t2, 0x0(v1)               
0x8001a7ec  addi v1, v1, 1                
0x8001a7f0  addu t2, t2, t2               
0x8001a7f4  addu t2, t2, t7               
0x8001a7f8  srl t7, t2, 8                 
0x8001a7fc  j 0x8001a768                   -> 0x8001a768
0x8001a800  andi t7, t7, 0x0001           
0x8001a804  addu t2, t2, t2               
0x8001a808  srl t7, t2, 8                 
0x8001a80c  andi t7, t7, 0x0001           
0x8001a810  andi t2, t2, 0x00ff           
0x8001a814  bne zero, t2, 0x8001a834       -> 0x8001a834
0x8001a818  sll zero, zero, 0             
0x8001a81c  lbu t2, 0x0(v1)               
0x8001a820  addi v1, v1, 1                
0x8001a824  addu t2, t2, t2               
0x8001a828  addu t2, t2, t7               
0x8001a82c  srl t7, t2, 8                 
0x8001a830  andi t7, t7, 0x0001           
0x8001a834  bne zero, t7, 0x8001a658       -> 0x8001a658
0x8001a838  sll zero, zero, 0             
0x8001a83c  lhu t5, 0x0(t3)               
0x8001a840  addi t3, t3, 2                
0x8001a844  beq zero, t5, 0x8001a868       -> 0x8001a868
0x8001a848  sll zero, zero, 0             
0x8001a84c  lh s0, 0x0(t3)                
0x8001a850  addi t3, t3, 2                
0x8001a854  sb s0, 0x0(a1)                
0x8001a858  addi a1, a1, 1                
0x8001a85c  addi t5, t5, -1               
0x8001a860  bne zero, t5, 0x8001a84c       -> 0x8001a84c
0x8001a864  sll zero, zero, 0             
0x8001a868  j 0x8001a874                   -> 0x8001a874
0x8001a86c  sll zero, zero, 0             
0x8001a870  sw s0, 0x0(t3)                
0x8001a874  addiu sp, sp, 128             
0x8001a878  sll zero, zero, 0             
0x8001a87c  lw v0, 0x0(sp)                
0x8001a880  lw v1, 0x4(sp)                
0x8001a884  lw a0, 0x8(sp)                
0x8001a888  lw a1, 0xc(sp)                
0x8001a88c  lw a2, 0x10(sp)               
0x8001a890  lw a3, 0x14(sp)               
0x8001a894  lw t0, 0x18(sp)               
0x8001a898  lw t1, 0x1c(sp)               
0x8001a89c  lw t2, 0x20(sp)               
0x8001a8a0  lw t3, 0x24(sp)               
0x8001a8a4  lw t4, 0x28(sp)               
0x8001a8a8  lw t5, 0x2c(sp)               
0x8001a8ac  lw t6, 0x30(sp)               
0x8001a8b0  lw t7, 0x34(sp)               
0x8001a8b4  lw s0, 0x38(sp)               
0x8001a8b8  lw s1, 0x3c(sp)               
0x8001a8bc  lw s2, 0x40(sp)               
0x8001a8c0  lw s3, 0x44(sp)               
0x8001a8c4  lw s4, 0x48(sp)               
0x8001a8c8  lw s5, 0x4c(sp)               
0x8001a8cc  lw s6, 0x50(sp)               
0x8001a8d0  lw s7, 0x54(sp)               
0x8001a8d4  lw t8, 0x58(sp)               
0x8001a8d8  lw t9, 0x5c(sp)               
0x8001a8dc  lw k0, 0x60(sp)               
0x8001a8e0  lw k1, 0x64(sp)               
0x8001a8e4  lw gp, 0x68(sp)               
0x8001a8e8  lw ra, 0x6c(sp)               
0x8001a8ec  sll zero, zero, 0             
0x8001a8f0  addiu sp, sp, 112             
0x8001a8f4  sll zero, zero, 0             
0x8001a8f8  jr ra                         
0x8001a8fc  sll zero, zero, 0             
0x8001a900  lb at, -0x3534(zero)          
0x8001a904  lb at, -0x33b4(zero)          
0x8001a908  lb at, -0x3534(zero)          
0x8001a90c  lb at, -0x33b4(zero)          
0x8001a910  lb at, -0x3534(zero)          
0x8001a914  lb at, -0x3260(zero)          
0x8001a918  lb at, -0x3534(zero)          
0x8001a91c  sll zero, zero, 0             
0x8001a920  lb at, -0x24e4(zero)          
0x8001a924  lb at, -0x20b0(zero)          
0x8001a928  lb at, -0x2088(zero)          
0x8001a92c  lb at, -0x2088(zero)          
0x8001a930  lb at, -0x2334(zero)          
0x8001a934  lb at, -0x2088(zero)          
0x8001a938  lb at, -0x2088(zero)          
0x8001a93c  lb at, -0x2088(zero)          
0x8001a940  lb at, -0x22c4(zero)          
0x8001a944  lb at, -0x20c4(zero)          
0x8001a948  lb at, -0x18ec(zero)          
0x8001a94c  lb at, -0x1850(zero)          
0x8001a950  lb at, -0x1804(zero)          
0x8001a954  lb at, -0x163c(zero)          
0x8001a958  lb at, -0x1740(zero)          