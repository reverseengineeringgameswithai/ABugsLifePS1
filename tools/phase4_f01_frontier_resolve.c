/*
 * phase4_f01_frontier_resolve.c -- can anything OTHER than the enumerated
 * writers reach Anthill's scene-transition state?
 *
 * This is the mod-safety question for F01, and the open half of its
 * complete_frontier dimension. The frontier extractor reports 790 accesses that
 * it could not decide inside the 30 functions which provably touch
 * 0x800823A0 (scene-transition request) or 0x80082470 (its countdown timer).
 * "Could not decide" is not "does not reach": each site has to be resolved or
 * explicitly bounded.
 *
 * The static index only records accesses in blocks whose CFG it recovered, and
 * it resolves an effective address only when its own dataflow reached the base.
 * This tool re-walks the SAME extents with a stronger, purpose-built recovery
 * and classifies every memory access into exactly one disposition:
 *
 *   RESOLVED_HIT      base recovered; effective address lands in a window
 *   RESOLVED_MISS     base recovered; provably lands elsewhere
 *   BOUNDED_STRUCT    base is a live struct pointer, but the displacement is far
 *                     smaller than the distance from any plausible base to a
 *                     window, so no in-range displacement can reach one
 *   UNKNOWN           base not recovered here -- an honest residual
 *
 * Recovery models, in order of strength:
 *   - $gp-relative                       ($gp = 0x80081D98, proven constant)
 *   - lui/addiu/ori materialisation      tracked per register, killed on write,
 *                                        invalidated at every branch target
 *   - addu of two known constants
 *
 * A register loaded from memory, produced by a call, or arriving as an argument
 * is NOT guessed at. It becomes UNKNOWN or, where the displacement makes a
 * window unreachable for any base in RAM, BOUNDED_STRUCT with that argument
 * stated.
 *
 * Build: cc -O2 -Wall -Wextra -Werror -o /tmp/fr tools/phase4_f01_frontier_resolve.c
 * Usage: tools/phase4_f01_frontier_resolve <disc_files_root>
 * Output: JSON on stdout.
 *
 * EXIT CODES -- exit 1 is the EXPECTED state while Item 2 is open:
 *   0  no new writer AND zero unresolved stores (the closed-item-2 state,
 *      never yet observed)
 *   1  fail-closed blocker exit: no new writer, but unresolved stores remain.
 *      The JSON on stdout is complete and valid. A verifier chaining this
 *      command with `&&` or running under `set -e` stops BEFORE comparing the
 *      output; treat 1 as a documented, non-error outcome and then require
 *      valid JSON plus byte identity.
 *   2  usage or I/O error; the output is not a receipt.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#define GP_VALUE   0x80081D98u
#define REQ_LO     0x800823A0u
#define REQ_HI     0x800823A2u
#define TMR_LO     0x80082470u
#define TMR_HI     0x80082472u
#define RAM_LO     0x80000000u
#define RAM_HI     0x80200000u

/* The writers Canon already enumerates for the two windows. A RESOLVED_HIT
 * outside this set would be a genuine discovery -- and a modding hazard. */
typedef struct { const char *image; uint32_t pc; } KnownWriter;
/* Writer identity is (image, pc). Overlay load addresses repeat across images,
 * so a pc-only test both mislabels a LOAD in one overlay as an enumerated writer
 * in another, and would let a genuine new STORE pass at a colliding address. */
static const KnownWriter KNOWN_WRITERS[] = {
    { "SCUS", 0x800496d8 }, { "SCUS", 0x800496f8 }, { "SCUS", 0x8004a8b4 },
    { "SCUS", 0x8004a9f4 }, { "SCUS", 0x8004b3c0 }, { "SCUS", 0x8004f224 },
    { "SCUS", 0x8004f28c }, { "SCUS", 0x8004f2f0 }, { "SCUS", 0x8004f6b8 },
    { "SCUS", 0x8004f9e4 }, { "SCUS", 0x8004fadc }, { "SCUS", 0x8004fcb4 },
    { "SCUS", 0x8004fe44 }, { "SCUS", 0x800591dc }, { "SCUS", 0x8005b888 },
    { "SCUS", 0x8005c6b8 },
    { "SCUS", 0x80049704 }, { "SCUS", 0x8004a8c0 }, { "SCUS", 0x8004aa00 },
    { "SCUS", 0x8004b3cc }, { "SCUS", 0x8004f230 }, { "SCUS", 0x8004f298 },
    { "SCUS", 0x8004f2fc }, { "SCUS", 0x8004f6cc }, { "SCUS", 0x8004f9fc },
    { "SCUS", 0x8004fe4c }, { "SCUS", 0x800553f8 }, { "SCUS", 0x800591e8 },
    { "SCUS", 0x8005b890 }, { "SCUS", 0x8005c6cc },
    { "LEVEL01_LEVEL1", 0x800b4100 }, { "LEVEL01_LEVEL1", 0x800b410c },
    { "LEVEL02_LEVEL",  0x800b4190 }, { "LEVEL02_LEVEL",  0x800b419c },
    { "LEVEL02_LEVEL1", 0x800b4424 }, { "LEVEL02_LEVEL1", 0x800b4430 },
    { "LEVEL03_LEVEL1", 0x800b3e70 }, { "LEVEL03_LEVEL1", 0x800b3e7c },
    { "LEVEL04_LEVEL",  0x800b40b0 }, { "LEVEL04_LEVEL",  0x800b40bc },
    { "LEVEL04_LEVEL",  0x800b43b0 }, { "LEVEL04_LEVEL",  0x800b43d4 },
    { "LEVEL04_LEVEL1", 0x800b3e84 }, { "LEVEL04_LEVEL1", 0x800b3e90 },
    { "LEVEL05_LEVEL",  0x800b3ef0 }, { "LEVEL05_LEVEL",  0x800b3efc },
    { "LEVEL05_LEVEL",  0x800b3fe0 },
    { "LEVEL05_LEVEL1", 0x800b42e4 }, { "LEVEL05_LEVEL1", 0x800b42f0 },
    { "LEVEL06_LEVEL",  0x800b3ea4 }, { "LEVEL06_LEVEL",  0x800b3eb0 },
    { "LEVEL06_LEVEL1", 0x800b3f18 }, { "LEVEL06_LEVEL1", 0x800b3f24 },
    { "LEVEL07_LEVEL",  0x800b44b0 }, { "LEVEL07_LEVEL",  0x800b44bc },
    { "LEVEL08_LEVEL",  0x800b3dec },
    { "LEVEL09_LEVEL",  0x800b4460 }, { "LEVEL09_LEVEL",  0x800b4470 },
};

/* The 30 extents the frontier flagged: every function that provably touches a
 * window AND carries at least one access the extractor could not decide.
 * (image_id, start, end) -- overlay entries repeat addresses across images, so
 * the image is part of the identity. */
/* An argument value proved from the callers, so the scan can start with a base
 * it would otherwise never recover. Only entered when the caller graph gives a
 * SINGLE unambiguous value -- never guessed. */
typedef struct { uint32_t fn_start; int reg; uint32_t value; const char *proof; } ArgSeed;
static const ArgSeed ARG_SEEDS[] = {
    { 0x80048138, 4, 0x800A6500,
      "sole caller gameplay_state_machine at 0x8004EFD8 passes a0 = s0 - 0x90 with "
      "s0 = 0x800A6590 (lui/addiu at 0x8004EF70/0x8004EF74); a0 is therefore the "
      "player struct base, matching MEM_800A6500_Player_state" },
};

typedef struct { const char *image; uint32_t start, end; const char *name; } Extent;
static const Extent EXTENTS[] = {
    /* GENERATED from analysis/phase4_static_frontier_index.json: EVERY code
     * function in EVERY analysed image.
     *
     * There is deliberately no selection criterion left to state wrongly. The
     * ends were hand-typed and wrong (2026-08-05: 20 of 29 stopped short). The
     * set was then hand-listed and wrong (2026-08-06, found by a fresh verifier:
     * 29 of the 37 the tool's own criterion admitted). Deriving the criterion
     * from the index's CFG-REACHABLE accesses would still miss a window access
     * sitting in an unreachable block, and 22 records reach under half their
     * extent. Scanning the whole corpus ends that regress. Regenerate with
     * tools/phase4_gen_resolver_extents.py, do not edit. */
    { "SCUS", 0x80010000, 0x80013108, "per_object_mesh_draw_payload_emitter" },
    { "SCUS", 0x80013108, 0x800140a0, "grass_mound_mesh_builder" },
    { "SCUS", 0x800140a0, 0x80014360, "gte_trail_cull_transform" },
    { "SCUS", 0x80014360, 0x80014504, "pass3_backdrop_cull" },
    { "SCUS", 0x80014504, 0x800146e0, "build_render_survivor_list" },
    { "SCUS", 0x800146e0, 0x80014724, "gte_camera_matrix_load" },
    { "SCUS", 0x80014724, 0x8001474c, "gte_mvmva_ir_transform" },
    { "SCUS", 0x8001474c, 0x8001478c, "matrix_lut_mesh__mesh_payload_e_glue" },
    { "SCUS", 0x8001478c, 0x80014844, "boss_defeat_fsm__mesh_payload_e_glue" },
    { "SCUS", 0x80014844, 0x80014ad4, "contact_record_billboard_render" },
    { "SCUS", 0x80014ad4, 0x80014b04, "gte_vec_length_sqrt_helper" },
    { "SCUS", 0x80014b04, 0x80014ee0, "dirt_mesh_builder" },
    { "SCUS", 0x80014ee0, 0x800153d0, "boss_defeat_fsm__scene_geometry_glue" },
    { "SCUS", 0x800153d0, 0x800163e0, "scene_geometry_normal_pass" },
    { "SCUS", 0x800163e0, 0x800172dc, "gte_mesh_vertex_normal_transform" },
    { "SCUS", 0x800172dc, 0x80017b98, "shared_all_mesh_renderer" },
    { "SCUS", 0x80017b98, 0x80017cdc, "gte_rotation_matrix_setup" },
    { "SCUS", 0x80017cdc, 0x80017d04, "gte_far_color_set_save" },
    { "SCUS", 0x80017d04, 0x80017d14, "gte_screen_xy_fifo_read" },
    { "SCUS", 0x80017d14, 0x80017d50, "gte_color_matrix_load_symmetric" },
    { "SCUS", 0x80017d50, 0x80017db4, "gte_lighting_vector_transform" },
    { "SCUS", 0x800186ec, 0x8001881c, "gte_rtps_mesh_assembler" },
    { "SCUS", 0x8001881c, 0x80018850, "bone_matrix_arra_object_mesh_dr_glue" },
    { "SCUS", 0x80018850, 0x80018cc4, "gte_quad_near_clip_dispatch" },
    { "SCUS", 0x80018cc4, 0x80018f4c, "poly_interpolate_midpoint_prim" },
    { "SCUS", 0x80018f4c, 0x80019244, "gte_quad_clip_emit_variant_a" },
    { "SCUS", 0x80019244, 0x8001961c, "gte_quad_clip_emit_variant_b" },
    { "SCUS", 0x8001961c, 0x80019934, "gte_quad_clip_emit_variant_c" },
    { "SCUS", 0x80019934, 0x80019ce8, "bulk_ground_sub_emitter" },
    { "SCUS", 0x80019ce8, 0x80019f3c, "emit_subdivided_gouraud_prims" },
    { "SCUS", 0x80019f3c, 0x8001a0e4, "gpu_emit_subdivided_quad_prims" },
    { "SCUS", 0x8001a0e4, 0x8001a1dc, "gpu_build_poly_g4_gouraud" },
    { "SCUS", 0x8001a1dc, 0x8001a1e0, "level_raw_lzss_decompressor" },
    { "SCUS", 0x8001a1e0, 0x8001a900, "decompress_lz_bitstream" },
    { "SCUS", 0x8001ca20, 0x8001cdc0, "mesh_draw_command_interpreter" },
    { "SCUS", 0x8001cdc0, 0x8001d3cc, "dat_parser_relocator" },
    { "SCUS", 0x8001d3cc, 0x8001dfe4, "dirt_object_dispatch" },
    { "SCUS", 0x8001dfe4, 0x8001ea6c, "scene_geometry_draw_dispatcher" },
    { "SCUS", 0x8001ea6c, 0x8001eacc, "survivor_list_primitive_builder_1" },
    { "SCUS", 0x8001eacc, 0x800206e8, "mesh_payload_emit_orchestrator" },
    { "SCUS", 0x800206e8, 0x800207f0, "survivor_list_primitive_builder_2" },
    { "SCUS", 0x800207f0, 0x800212fc, "matrix_lut_mesh_transform_07f0" },
    { "SCUS", 0x800212fc, 0x80021d84, "setpiece_actor_mesh_transform" },
    { "SCUS", 0x80021d84, 0x800224ec, "boss_defeat_fsm_mesh_transform" },
    { "SCUS", 0x800224ec, 0x80022978, "scene_render_driver" },
    { "SCUS", 0x80022978, 0x80022fe0, "textured_mesh_emit" },
    { "SCUS", 0x80022fe0, 0x80023544, "effect_mesh_transform" },
    { "SCUS", 0x80023544, 0x80023abc, "rot_average_project" },
    { "SCUS", 0x80023abc, 0x80023d54, "queued_billboard_quad_render" },
    { "SCUS", 0x80023d54, 0x8002418c, "ot_buffer_mesh_transform_3d54" },
    { "SCUS", 0x8002418c, 0x800245c4, "ot_buffer_mesh_transform_418c" },
    { "SCUS", 0x800245c4, 0x800249d0, "ot_buffer_mesh_transform_45c4" },
    { "SCUS", 0x800249d0, 0x80024ddc, "ot_buffer_mesh_transform_49d0" },
    { "SCUS", 0x80024ddc, 0x80024e04, "contact_record_post_init" },
    { "SCUS", 0x80024e04, 0x80025084, "damageable_object_ptr_mesh_transform" },
    { "SCUS", 0x80025084, 0x800252a0, "oriented_containment_range_test" },
    { "SCUS", 0x800252a0, 0x800252b0, "pickup_record_processor" },
    { "SCUS", 0x800252b0, 0x800252b8, "collision_candidates_build_from_records_entry" },
    { "SCUS", 0x800252b8, 0x800253e8, "collision_candidates_build_from_records" },
    { "SCUS", 0x800253e8, 0x80025f54, "pickup_projector" },
    { "SCUS", 0x80025f54, 0x800260f8, "hud_draw_sprite_tile" },
    { "SCUS", 0x800260f8, 0x80026390, "hud_draw_glyph" },
    { "SCUS", 0x80026390, 0x80026588, "prim_queue_emit_6390" },
    { "SCUS", 0x80026588, 0x80026858, "result_draw_glyph_dim" },
    { "SCUS", 0x80026858, 0x80026a68, "prim_queue_emit_6858" },
    { "SCUS", 0x80026a68, 0x80026d78, "draw_textured_quad" },
    { "SCUS", 0x80026d78, 0x80026df4, "queue_draw_prim" },
    { "SCUS", 0x80026df4, 0x80027004, "result_upload_anim_frame" },
    { "SCUS", 0x80027004, 0x80027c60, "ot_depth_fade_postprocess" },
    { "SCUS", 0x80027c60, 0x80027cbc, "gp_flags_and_buffers_clear" },
    { "SCUS", 0x80027cbc, 0x80028d74, "matrix_lut_mesh_transform" },
    { "SCUS", 0x80028d74, 0x80029030, "prim_queue_emit_8d74" },
    { "SCUS", 0x80029030, 0x800292dc, "object_animate_rotation_matrix" },
    { "SCUS", 0x800292dc, 0x80029508, "object_rotation_matrix_apply" },
    { "SCUS", 0x80029508, 0x80029578, "pass2_object_transform_update" },
    { "SCUS", 0x80029578, 0x8002958c, "gp_state_clear_three_shorts" },
    { "SCUS", 0x8002958c, 0x8002b424, "chunk_mesh_weld_converter" },
    { "SCUS", 0x8002b424, 0x8002b428, "boss_defeat_fsm__scene_geometry_glue_b424" },
    { "SCUS", 0x8002b428, 0x8002d64c, "bone_matrix_array_mesh_transform" },
    { "SCUS", 0x8002d64c, 0x8002d674, "call_8002b424_wrapper" },
    { "SCUS", 0x8002d674, 0x8002fc90, "object_mesh_draw" },
    { "SCUS", 0x8002fc90, 0x8002fce8, "gpu_gt_prim_list_advance" },
    { "SCUS", 0x8002fce8, 0x8002ffa8, "parse_chunk_record_table" },
    { "SCUS", 0x8002ffa8, 0x80030010, "load_named_file" },
    { "SCUS", 0x80030010, 0x80030018, "nullsub_80030010" },
    { "SCUS", 0x80030018, 0x8003001c, "boss_defeat_fsm__scene_geometry_glue_0018" },
    { "SCUS", 0x8003001c, 0x8003043c, "ot_buffer_mesh_transform_001c" },
    { "SCUS", 0x8003043c, 0x80030440, "boss_defeat_fsm__scene_geometry_glue_043c" },
    { "SCUS", 0x80030440, 0x800308cc, "ot_buffer_mesh_transform" },
    { "SCUS", 0x800308cc, 0x800309cc, "pickup_icon_vram_upload" },
    { "SCUS", 0x800309cc, 0x80030aac, "vector_project_onto_plane" },
    { "SCUS", 0x80030aac, 0x80030b98, "vec3_reject_normal_component" },
    { "SCUS", 0x80030b98, 0x80030c78, "vec3_project_point_onto_plane" },
    { "SCUS", 0x80030c78, 0x80030d64, "vector_remove_normal_component" },
    { "SCUS", 0x80030d64, 0x80030f60, "all_model_file_load_unpack" },
    { "SCUS", 0x80030f60, 0x800313a8, "collision_sector_table_builder" },
    { "SCUS", 0x800313a8, 0x80031efc, "collision_grid_builder" },
    { "SCUS", 0x80031efc, 0x800320bc, "point_edge_crossing_test" },
    { "SCUS", 0x800320bc, 0x800322a0, "segment_orientation_test_2d" },
    { "SCUS", 0x800322a0, 0x80032610, "collision_edge_intersection_test" },
    { "SCUS", 0x80032610, 0x800345cc, "collision_point_in_poly" },
    { "SCUS", 0x800345cc, 0x80035280, "collision_resolver_accumulate" },
    { "SCUS", 0x80035280, 0x80035f24, "collision_resolve_pass" },
    { "SCUS", 0x80035f24, 0x8003633c, "player_movement__collision_poin_glue" },
    { "SCUS", 0x8003633c, 0x80036cec, "player_movement_collision_integrator" },
    { "SCUS", 0x80036cec, 0x80036e70, "player_y_commit_store" },
    { "SCUS", 0x80036e70, 0x800370c8, "collision_probe_candidate_pass" },
    { "SCUS", 0x800370c8, 0x80037320, "collision_probe_player_pass" },
    { "SCUS", 0x80037320, 0x800376a0, "collision_candidate_builder" },
    { "SCUS", 0x800376a0, 0x80037a38, "camera_region_query" },
    { "SCUS", 0x80037a38, 0x80037dac, "ground_height_query" },
    { "SCUS", 0x80037dac, 0x80038090, "player_region_poly_query" },
    { "SCUS", 0x80038090, 0x80038e48, "point_in_polygon_region_test" },
    { "SCUS", 0x80038e48, 0x80038eac, "player_sector_lookup" },
    { "SCUS", 0x80038eac, 0x80038ee8, "object_slot_set_field_6" },
    { "SCUS", 0x80038ee8, 0x80038f20, "object_slot_clear_field" },
    { "SCUS", 0x80038f20, 0x80038f38, "flag_ge_threshold" },
    { "SCUS", 0x80038f38, 0x80038f84, "sector_region_code_query" },
    { "SCUS", 0x80038f84, 0x80038fc4, "checkpoint_player_state_read" },
    { "SCUS", 0x80038fc4, 0x800390f0, "build_division_lookup_tables" },
    { "SCUS", 0x800390f0, 0x80039124, "gte_mesh_assembler_counted" },
    { "SCUS", 0x80039124, 0x8003912c, "noop_return_stub_80039124" },
    { "SCUS", 0x8003912c, 0x80039478, "display_env_setup" },
    { "SCUS", 0x80039478, 0x80039780, "display_buffers_init" },
    { "SCUS", 0x80039780, 0x80039854, "vram_clear_framebuffers" },
    { "SCUS", 0x80039854, 0x80039970, "boot_subsystem_init" },
    { "SCUS", 0x80039970, 0x80039a20, "boot_video_audio_init" },
    { "SCUS", 0x80039a20, 0x80039a70, "graphics_reset_teardown" },
    { "SCUS", 0x80039a70, 0x80039bd8, "frame_present" },
    { "SCUS", 0x80039bd8, 0x80039c34, "pad_rumble_update" },
    { "SCUS", 0x80039c34, 0x8003a2dc, "controller_input_update" },
    { "SCUS", 0x8003a2dc, 0x8003a314, "controller_input_latch_update" },
    { "SCUS", 0x8003a314, 0x8003a318, "high_heap_loader_entry" },
    { "SCUS", 0x8003a318, 0x8003c388, "high_heap_loader_level_raw_decompress_orchestrator" },
    { "SCUS", 0x8003c388, 0x8003c8bc, "vram_upload_wait" },
    { "SCUS", 0x8003c8bc, 0x8003cc1c, "level_texture_stage" },
    { "SCUS", 0x8003cc1c, 0x8003cc58, "level_texture_stage_reset" },
    { "SCUS", 0x8003cc58, 0x8003cf2c, "level_texture_upload" },
    { "SCUS", 0x8003cf2c, 0x8003d404, "resource_id_dat_load_dispatcher" },
    { "SCUS", 0x8003d404, 0x8003d620, "collision_grid_level_load_chu_glue" },
    { "SCUS", 0x8003d620, 0x8003d7b0, "collision_grid_l_level_overlay__glue" },
    { "SCUS", 0x8003d7b0, 0x8003daec, "backdrop_horizon_gradient_draw" },
    { "SCUS", 0x8003daec, 0x8003daf0, "scroll_backdrop_moveimage_entry" },
    { "SCUS", 0x8003daf0, 0x8003df14, "scroll_backdrop_moveimage" },
    { "SCUS", 0x8003df14, 0x8003df98, "scroll_background_modulo_offset" },
    { "SCUS", 0x8003df98, 0x8003e020, "gpu_timing_marker_append" },
    { "SCUS", 0x8003e020, 0x8003e054, "gpu_timing_markers_begin" },
    { "SCUS", 0x8003e054, 0x8003e064, "text_draw_stub" },
    { "SCUS", 0x8003e064, 0x8003e0f4, "draw_string_centered" },
    { "SCUS", 0x8003e0f4, 0x8003e104, "empty_function_stub_e0f4" },
    { "SCUS", 0x8003e104, 0x8003e3e0, "dynamic_render_budget_update" },
    { "SCUS", 0x8003e3e0, 0x8003e4e0, "resource_load_buffers_reset" },
    { "SCUS", 0x8003e4e0, 0x8003e4e8, "tpage_prim_setup_entry" },
    { "SCUS", 0x8003e4e8, 0x8003e760, "tpage_prim_setup" },
    { "SCUS", 0x8003e760, 0x8003e7c0, "token_descriptor_reskin" },
    { "SCUS", 0x8003e7c0, 0x8003e83c, "fmv_bin_load" },
    { "SCUS", 0x8003e83c, 0x8003e8c4, "vsync_wait_glue" },
    { "SCUS", 0x8003e8c4, 0x8003e928, "vsync_wait_glue_e8c4" },
    { "SCUS", 0x8003e928, 0x8003eec8, "backdrop_tile_builder" },
    { "SCUS", 0x8003eec8, 0x8003efc8, "dat_load_256byte_table" },
    { "SCUS", 0x8003efc8, 0x8003f2f0, "render_zone_gating_update" },
    { "SCUS", 0x8003f2f0, 0x8003f358, "wait_for_frame_sync_flag" },
    { "SCUS", 0x8003f358, 0x8003f3b4, "seed_cursor_state_jump_dispatch" },
    { "SCUS", 0x8003f3b4, 0x8003f4d4, "switch_dispatch_struct_by_index" },
    { "SCUS", 0x8003f4d4, 0x8003f504, "set_draw_env_offset" },
    { "SCUS", 0x8003f504, 0x8003f5b8, "scene_load_init" },
    { "SCUS", 0x8003f5b8, 0x8003f5fc, "load_memory_bin" },
    { "SCUS", 0x8003f5fc, 0x8003f620, "reset_visual_sprite_object_pool" },
    { "SCUS", 0x8003f620, 0x8003f8f8, "table_836byte_record_populate" },
    { "SCUS", 0x8003f8f8, 0x8003f908, "empty_function_stub_f8f8" },
    { "SCUS", 0x8003f908, 0x8003f918, "empty_function_stub_f908" },
    { "SCUS", 0x8003f918, 0x8003f928, "empty_function_stub_f918" },
    { "SCUS", 0x8003f928, 0x8003f938, "empty_function_stub_f928" },
    { "SCUS", 0x8003f938, 0x800409f8, "render_mesh_transform" },
    { "SCUS", 0x800409f8, 0x80041a74, "vec_normalize_len" },
    { "SCUS", 0x80041a74, 0x80041ac4, "player_vertical_resident_level_glue" },
    { "SCUS", 0x80041ac4, 0x80042428, "vec_normalize_len_1ac4" },
    { "SCUS", 0x80042428, 0x80042c70, "visual_sprite_object_pool_update" },
    { "SCUS", 0x80042c70, 0x80042dcc, "record_slots_populate_free" },
    { "SCUS", 0x80042dcc, 0x80042e94, "get_current_actor_xyz" },
    { "SCUS", 0x80042e94, 0x80042fa0, "vab_bank_loader" },
    { "SCUS", 0x80042fa0, 0x80043018, "vab_load" },
    { "SCUS", 0x80043018, 0x80043068, "display_env_apply" },
    { "SCUS", 0x80043068, 0x80043114, "loadscreen_image_setup" },
    { "SCUS", 0x80043114, 0x80043118, "sound_vab_close_entry" },
    { "SCUS", 0x80043118, 0x80043144, "sound_vab_close" },
    { "SCUS", 0x80043144, 0x80043184, "find_free_slot_16entry" },
    { "SCUS", 0x80043184, 0x80043284, "voice_keyon_vol_3184" },
    { "SCUS", 0x80043284, 0x80043500, "voice_keyon_vol_3284" },
    { "SCUS", 0x80043500, 0x800435f8, "spu_voice_key_onoff" },
    { "SCUS", 0x800435f8, 0x800438a8, "voice_keyon_vol_35f8" },
    { "SCUS", 0x800438a8, 0x80043dac, "sound_voice_trigger" },
    { "SCUS", 0x80043dac, 0x80044350, "voice_keyon_vol" },
    { "SCUS", 0x80044350, 0x80044c5c, "sound_positional_voice" },
    { "SCUS", 0x80044c5c, 0x80044ce8, "sound_system_init" },
    { "SCUS", 0x80044ce8, 0x80044d28, "cd_mix_shim" },
    { "SCUS", 0x80044d28, 0x80045678, "sfx_voice_manager" },
    { "SCUS", 0x80045678, 0x80045704, "nearest_pickup_finalize" },
    { "SCUS", 0x80045704, 0x8004574c, "string_to_upper" },
    { "SCUS", 0x8004574c, 0x800457a0, "build_prefixed_filename" },
    { "SCUS", 0x800457a0, 0x800457dc, "find_file_size" },
    { "SCUS", 0x800457dc, 0x800457e4, "noop_return_stub_800457dc" },
    { "SCUS", 0x800457e4, 0x8004589c, "cd_file_locate" },
    { "SCUS", 0x8004589c, 0x80045978, "cd_find_file_by_name" },
    { "SCUS", 0x80045978, 0x80045a40, "cd_audio_mix_control_5978" },
    { "SCUS", 0x80045a40, 0x80045a60, "music_play_once_wrapper" },
    { "SCUS", 0x80045a60, 0x80045aac, "transition_finalizer_subsystem_reset" },
    { "SCUS", 0x80045aac, 0x80045b00, "cd_audio_mix_control_5aac" },
    { "SCUS", 0x80045b00, 0x80045cac, "cd_audio_mix_control" },
    { "SCUS", 0x80045cac, 0x80045ccc, "music_play_looping_wrapper" },
    { "SCUS", 0x80045ccc, 0x80045cd0, "cd_audio_mix_control_5cd0_gp_entry" },
    { "SCUS", 0x80045cd0, 0x80045d5c, "cd_audio_mix_control_5cd0" },
    { "SCUS", 0x80045d5c, 0x80045d6c, "gp_set_one" },
    { "SCUS", 0x80045d6c, 0x80045fc4, "cd_subsystem_init" },
    { "SCUS", 0x80045fc4, 0x800460e4, "file_lookup_cdsearchfile" },
    { "SCUS", 0x800460e4, 0x800461e0, "ot_frame_flush_60e4" },
    { "SCUS", 0x800461e0, 0x80046330, "ot_frame_flush" },
    { "SCUS", 0x80046330, 0x80046538, "universal_file_loader" },
    { "SCUS", 0x80046538, 0x80046618, "build_level_asset_path" },
    { "SCUS", 0x80046618, 0x80046764, "level_file_path_build" },
    { "SCUS", 0x80046764, 0x800467dc, "cd_controlf_shim" },
    { "SCUS", 0x800467dc, 0x80046828, "cd_controlb_shim" },
    { "SCUS", 0x80046828, 0x8004682c, "music_loop_poll" },
    { "SCUS", 0x8004682c, 0x8004699c, "cd_audio_mix_control_682c" },
    { "SCUS", 0x8004699c, 0x80046ac0, "music_start" },
    { "SCUS", 0x80046ac0, 0x80046ae8, "music_play_once" },
    { "SCUS", 0x80046ae8, 0x80046b14, "music_play_looping" },
    { "SCUS", 0x80046b14, 0x80046b20, "gp_flag_test" },
    { "SCUS", 0x80046b20, 0x80046cac, "level_load_player_spawn_writer" },
    { "SCUS", 0x80046cac, 0x80046d24, "resident_level_t_seed_plant_dan_glue" },
    { "SCUS", 0x80046d24, 0x800470ac, "projectile_aim" },
    { "SCUS", 0x800470ac, 0x80047284, "berry_throw_dispatch" },
    { "SCUS", 0x80047284, 0x80047ebc, "player_contact_response" },
    { "SCUS", 0x80047ebc, 0x80048138, "contact_alloc_cursor_mesh_transform" },
    { "SCUS", 0x80048138, 0x800498ac, "player_vertical_update" },
    { "SCUS", 0x800498ac, 0x80049a58, "enemy_update_deathanim" },
    { "SCUS", 0x80049a58, 0x80049a70, "actor_anim_seq1_param1" },
    { "SCUS", 0x80049a70, 0x80049a88, "actor_anim_seq21_trigger" },
    { "SCUS", 0x80049a88, 0x80049aa0, "actor_anim_seq1_param2_49a88" },
    { "SCUS", 0x80049aa0, 0x80049ab8, "actor_enter_anim_state_3" },
    { "SCUS", 0x80049ab8, 0x80049ad0, "enemy_deathanim_set_anim3" },
    { "SCUS", 0x80049ad0, 0x80049ae8, "actor_anim1_state_handler" },
    { "SCUS", 0x80049ae8, 0x80049b00, "anim_state_set_seq_1_1" },
    { "SCUS", 0x80049b00, 0x80049b18, "actor_anim_seq13_param0" },
    { "SCUS", 0x80049b18, 0x80049b30, "actor_anim_seq25_trigger" },
    { "SCUS", 0x80049b30, 0x80049b48, "actor_anim_seq1_param2_49b30" },
    { "SCUS", 0x80049b48, 0x80049b60, "actor_enter_anim_state_2" },
    { "SCUS", 0x80049b60, 0x80049c30, "enemy_deathanim_finalize_remove_from_list" },
    { "SCUS", 0x80049c30, 0x80049e88, "mover_init_from_record" },
    { "SCUS", 0x80049e88, 0x8004a02c, "enemy_strike_contact_effect" },
    { "SCUS", 0x8004a02c, 0x8004a0a0, "actor_event_sound_trigger" },
    { "SCUS", 0x8004a0a0, 0x8004a0f4, "object_play_sound_38_type_1_10" },
    { "SCUS", 0x8004a0f4, 0x8004a11c, "thumper_driver_cb" },
    { "SCUS", 0x8004a11c, 0x8004a144, "object_play_sound_125" },
    { "SCUS", 0x8004a144, 0x8004a180, "actor_sound40_on_low_state" },
    { "SCUS", 0x8004a180, 0x8004a20c, "mosquito_species_callback" },
    { "SCUS", 0x8004a20c, 0x8004a234, "play_object_sound_42" },
    { "SCUS", 0x8004a234, 0x8004a2b0, "actor_turn_toward_player" },
    { "SCUS", 0x8004a2b0, 0x8004a42c, "aimed_object_spawn_sfx" },
    { "SCUS", 0x8004a42c, 0x8004a700, "object_slot_type_init" },
    { "SCUS", 0x8004a700, 0x8004aa34, "resident_level_transition_initiator" },
    { "SCUS", 0x8004aa34, 0x8004abf4, "actor_transform_anim_vertex_emit" },
    { "SCUS", 0x8004abf4, 0x8004b6dc, "actor_player_contact_resolver" },
    { "SCUS", 0x8004b6dc, 0x8004b940, "damageable_object_ptr_mesh_transform_b6dc" },
    { "SCUS", 0x8004b940, 0x8004c10c, "mover_actor_update" },
    { "SCUS", 0x8004c10c, 0x8004c13c, "actor_set_anim_sequence" },
    { "SCUS", 0x8004c13c, 0x8004c228, "event_bytecode_interpreter" },
    { "SCUS", 0x8004c228, 0x8004c238, "mover_vm_op2_wait" },
    { "SCUS", 0x8004c238, 0x8004c278, "mover_vm_op3_wait_random" },
    { "SCUS", 0x8004c278, 0x8004c32c, "mover_vm_op4_random_dir_step" },
    { "SCUS", 0x8004c32c, 0x8004c46c, "mover_vm_op5_path_next_waypoint" },
    { "SCUS", 0x8004c46c, 0x8004c47c, "mover_vm_op9_branch_if_s3" },
    { "SCUS", 0x8004c47c, 0x8004c59c, "mover_vm_op11_seek_path_endpoint" },
    { "SCUS", 0x8004c59c, 0x8004c5d4, "mover_vm_op12_call_native" },
    { "SCUS", 0x8004c5d4, 0x8004c5e4, "vm_native_spawn_drop_burst" },
    { "SCUS", 0x8004c5e4, 0x8004c5f4, "mover_vm_op_spawn_burst_ring" },
    { "SCUS", 0x8004c5f4, 0x8004c604, "mover_vm_op_dispatch_next" },
    { "SCUS", 0x8004c604, 0x8004c614, "mover_vm_op_overlay_hook_b3b70" },
    { "SCUS", 0x8004c614, 0x8004c624, "mover_vm_op_call_b3bd4" },
    { "SCUS", 0x8004c624, 0x8004c634, "mover_vm_op_call_advance" },
    { "SCUS", 0x8004c634, 0x8004c644, "mover_vm_op_actor_flag_update" },
    { "SCUS", 0x8004c644, 0x8004c654, "vm_op_aimed_drop_spawn" },
    { "SCUS", 0x8004c654, 0x8004c664, "mover_vm_op_call_b3f00" },
    { "SCUS", 0x8004c664, 0x8004c68c, "mover_vm_op13_flags_mask" },
    { "SCUS", 0x8004c68c, 0x8004c6cc, "mover_vm_op14_anim_clip_load" },
    { "SCUS", 0x8004c6cc, 0x8004c6fc, "mover_vm_op15_cond_noise_mask" },
    { "SCUS", 0x8004c6fc, 0x8004c710, "mover_vm_op16_chase_radius_scratch" },
    { "SCUS", 0x8004c710, 0x8004c76c, "mover_vm_op17_player_proximity" },
    { "SCUS", 0x8004c76c, 0x8004c790, "mover_vm_op20_branch_fwd_if_s3" },
    { "SCUS", 0x8004c790, 0x8004c7a0, "mover_vm_op22_done_disable" },
    { "SCUS", 0x8004c7a0, 0x8004c7bc, "mover_vm_op23_set_byte_params" },
    { "SCUS", 0x8004c7bc, 0x8004c7d4, "mover_vm_op24_call_play_sound" },
    { "SCUS", 0x8004c7d4, 0x8004c808, "mover_vm_op25_cond_powerup_flag" },
    { "SCUS", 0x8004c808, 0x8004c818, "mover_vm_op0_jump_back" },
    { "SCUS", 0x8004c818, 0x8004c898, "mover_vm_dispatch_next" },
    { "SCUS", 0x8004c898, 0x8004c8ac, "jr_target_island_8004c898" },
    { "SCUS", 0x8004c8ac, 0x8004d224, "vm_motion_apply_chase" },
    { "SCUS", 0x8004d224, 0x8004d698, "mover_updater" },
    { "SCUS", 0x8004d698, 0x8004d6a8, "setpiece_spawn_manager" },
    { "SCUS", 0x8004d6a8, 0x8004d9e8, "setpiece_sfx_cue" },
    { "SCUS", 0x8004d9e8, 0x8004da94, "setpiece_spawn_init" },
    { "SCUS", 0x8004da94, 0x8004db7c, "level_complete_finale" },
    { "SCUS", 0x8004db7c, 0x8004dc0c, "polar_to_xz_offset" },
    { "SCUS", 0x8004dc0c, 0x8004dd98, "respawn_collision_reset" },
    { "SCUS", 0x8004dd98, 0x8004df18, "setpiece_actor_update" },
    { "SCUS", 0x8004df18, 0x8004ea8c, "camera_follow_update" },
    { "SCUS", 0x8004ea8c, 0x8004ecd4, "enemy_ai_dispatcher" },
    { "SCUS", 0x8004ecd4, 0x8004f478, "gameplay_state_machine" },
    { "SCUS", 0x8004f478, 0x8004f480, "gameplay_frame_render_entry" },
    { "SCUS", 0x8004f480, 0x8004fa40, "gameplay_frame_render" },
    { "SCUS", 0x8004fa40, 0x8004fc3c, "main_shell_state_machine" },
    { "SCUS", 0x8004fc3c, 0x8004fc50, "scene_flow_set_substate_1" },
    { "SCUS", 0x8004fc50, 0x8004fc64, "scene_flow_set_substate_11" },
    { "SCUS", 0x8004fc64, 0x8004fc78, "scene_flow_set_substate_2" },
    { "SCUS", 0x8004fc78, 0x8004fc8c, "scene_flow_set_substate_7" },
    { "SCUS", 0x8004fc8c, 0x8004fca0, "scene_flow_set_substate_12" },
    { "SCUS", 0x8004fca0, 0x800502c4, "scene_flow_dispatcher" },
    { "SCUS", 0x800502c4, 0x8005038c, "fmv_sequence_completion_check" },
    { "SCUS", 0x8005038c, 0x800503fc, "scene_setup_and_load" },
    { "SCUS", 0x800503fc, 0x8005044c, "spawn_fx_object" },
    { "SCUS", 0x8005044c, 0x800507f8, "play_sound" },
    { "SCUS", 0x800507f8, 0x80050838, "cd_audio_volume_apply" },
    { "SCUS", 0x80050838, 0x80050870, "sfx_menu_blip" },
    { "SCUS", 0x80050870, 0x80050994, "sfx_voice_trigger_glue" },
    { "SCUS", 0x80050994, 0x80050c40, "sfx_dispatch" },
    { "SCUS", 0x80050c40, 0x80050d1c, "contact_pickup_sfx" },
    { "SCUS", 0x80050d1c, 0x80050d98, "sfx_voice_manager_glue_0d1c" },
    { "SCUS", 0x80050d98, 0x80050e18, "sfx_voice_manager_glue" },
    { "SCUS", 0x80050e18, 0x80050e6c, "sfx_voice_manager_glue_0e18" },
    { "SCUS", 0x80050e6c, 0x80050ea0, "sfx_dispatch_glue" },
    { "SCUS", 0x80050ea0, 0x80050ea8, "pickup_target_reset_on_finalize_entry" },
    { "SCUS", 0x80050ea8, 0x80050ee4, "pickup_target_reset_on_finalize" },
    { "SCUS", 0x80050ee4, 0x80050ee8, "sfx_nearest_pickup_gp_entry" },
    { "SCUS", 0x80050ee8, 0x800510f0, "sfx_nearest_pickup_f_glue_0ee8" },
    { "SCUS", 0x800510f0, 0x80051294, "ambient_sfx_sequence_update" },
    { "SCUS", 0x80051294, 0x80051358, "controller_action_mask_update" },
    { "SCUS", 0x80051358, 0x8005149c, "sfx_proximity_priority_gate" },
    { "SCUS", 0x8005149c, 0x8005182c, "setpiece_light_color_update" },
    { "SCUS", 0x8005182c, 0x80051938, "all_enemies_defeated_event" },
    { "SCUS", 0x80051938, 0x80051940, "effect_drop_spawn_stage_entry" },
    { "SCUS", 0x80051940, 0x80051b84, "effect_drop_spawn_stage" },
    { "SCUS", 0x80051b84, 0x80051db4, "effect_render_stage" },
    { "SCUS", 0x80051db4, 0x80051dbc, "harvester_update_entry" },
    { "SCUS", 0x80051dbc, 0x80052090, "harvester_equip_and_active_update" },
    { "SCUS", 0x80052090, 0x8005222c, "collect_object_short_list" },
    { "SCUS", 0x8005222c, 0x800524b8, "level_transition_orchestrator" },
    { "SCUS", 0x800524b8, 0x80052508, "xz_distance_within_radius_test" },
    { "SCUS", 0x80052508, 0x80052574, "seed_plant_dande_seed_plant_min_glue" },
    { "SCUS", 0x80052574, 0x800526f4, "hud_anim_driver" },
    { "SCUS", 0x800526f4, 0x800526fc, "hud_draw" },
    { "SCUS", 0x800526fc, 0x80053638, "results_screen_render" },
    { "SCUS", 0x80053638, 0x80053640, "draw_mirrored_fullscreen_quads_entry" },
    { "SCUS", 0x80053640, 0x80053754, "draw_mirrored_fullscreen_quads" },
    { "SCUS", 0x80053754, 0x80053814, "seed_token_reskin_cycle" },
    { "SCUS", 0x80053814, 0x80054810, "type_0x3f_construct_contact_action_dispatch" },
    { "SCUS", 0x80054810, 0x80054964, "scene_verb_dispatch" },
    { "SCUS", 0x80054964, 0x80054aac, "scene_verb_dispatcher" },
    { "SCUS", 0x80054aac, 0x80054ad4, "store_four_bytes" },
    { "SCUS", 0x80054ad4, 0x80054c90, "contact_cursor_transition_reset" },
    { "SCUS", 0x80054c90, 0x80054eac, "checkpoint_save" },
    { "SCUS", 0x80054eac, 0x80054eb4, "grain_pickup_handler" },
    { "SCUS", 0x80054eb4, 0x8005518c, "sfx_nearest_pickup_f_glue" },
    { "SCUS", 0x8005518c, 0x80055414, "sfx_voice_trigger_gl_glue" },
    { "SCUS", 0x80055414, 0x80055478, "scene_flow_state_table_init" },
    { "SCUS", 0x80055478, 0x80055538, "serialize_savegame_buffer" },
    { "SCUS", 0x80055538, 0x80055644, "scene_config_apply" },
    { "SCUS", 0x80055644, 0x80055d38, "player_action_effects_update" },
    { "SCUS", 0x80055d38, 0x80055d4c, "load_numbered_asset_file_scene_entry" },
    { "SCUS", 0x80055d4c, 0x80055db0, "load_numbered_asset_file" },
    { "SCUS", 0x80055db0, 0x80055f8c, "load_stage_vram_upload" },
    { "SCUS", 0x80055f8c, 0x800563d4, "vram_upload_wait_5f8c" },
    { "SCUS", 0x800563d4, 0x80056f68, "actor_skinned_update" },
    { "SCUS", 0x80056f68, 0x800571e0, "results_pickup_finalize_step" },
    { "SCUS", 0x800571e0, 0x8005721c, "pickup_sfx_trigger_7c" },
    { "SCUS", 0x8005721c, 0x80057258, "pickup_sfx_trigger_7d" },
    { "SCUS", 0x80057258, 0x80057404, "nearest_pickup_scan_step" },
    { "SCUS", 0x80057404, 0x8005743c, "clear_gameplay_pool_on_reset" },
    { "SCUS", 0x8005743c, 0x80057620, "berry_homing_target_acquire" },
    { "SCUS", 0x80057620, 0x80057704, "checkpoint_construct" },
    { "SCUS", 0x80057704, 0x800577dc, "spawn_drop_scatter_burst" },
    { "SCUS", 0x800577dc, 0x800577e4, "contact_object_spawn_ring_entry" },
    { "SCUS", 0x800577e4, 0x80057920, "contact_object_spawn_ring" },
    { "SCUS", 0x80057920, 0x800579e0, "spawn_object_burst_ring" },
    { "SCUS", 0x800579e0, 0x80057a94, "spawn_objects_radial_ring" },
    { "SCUS", 0x80057a94, 0x80057b84, "spawn_drop_burst_effect" },
    { "SCUS", 0x80057b84, 0x80057c74, "vm_native_aimed_drop_spawn" },
    { "SCUS", 0x80057c74, 0x80057c9c, "actor_clear_motion_set_flag" },
    { "SCUS", 0x80057c9c, 0x80057dcc, "contact_object_s_spawn_drop_glue_7c9c" },
    { "SCUS", 0x80057dcc, 0x80057dd4, "spawn_drop_burst_by_object_type_entry" },
    { "SCUS", 0x80057dd4, 0x80057eac, "spawn_drop_burst_by_object_type" },
    { "SCUS", 0x80057eac, 0x80057eb4, "spawn_drop_burst_from_kind_entry" },
    { "SCUS", 0x80057eb4, 0x80057f44, "spawn_drop_burst_from_kind" },
    { "SCUS", 0x80057f44, 0x80057f4c, "spawn_drop_burst_8_entry" },
    { "SCUS", 0x80057f4c, 0x8005806c, "spawn_drop_burst_8" },
    { "SCUS", 0x8005806c, 0x800580e0, "spawn_drop_burst_five" },
    { "SCUS", 0x800580e0, 0x80058154, "spawn_drop_burst_type2" },
    { "SCUS", 0x80058154, 0x800581c8, "spawn_drop_burst_type76" },
    { "SCUS", 0x800581c8, 0x80058258, "spawn_drop_burst" },
    { "SCUS", 0x80058258, 0x800582e8, "spawn_drop_burst_type12" },
    { "SCUS", 0x800582e8, 0x80058378, "enemy_update_dea_spawn_drop_glue" },
    { "SCUS", 0x80058378, 0x800583f4, "spawn_drop_burst_16" },
    { "SCUS", 0x800583f4, 0x80058484, "mine_detonation_effect" },
    { "SCUS", 0x80058484, 0x800584f8, "spawn_drop_burst_sound5" },
    { "SCUS", 0x800584f8, 0x80058584, "spawn_drop_burst_5_type79" },
    { "SCUS", 0x80058584, 0x80058620, "spawn_drops_from_offset_table" },
    { "SCUS", 0x80058620, 0x800586b0, "spawn_drop_burst_type4" },
    { "SCUS", 0x800586b0, 0x80058af8, "contact_pickup_walker" },
    { "SCUS", 0x80058af8, 0x8005905c, "contact_vs_actor_handler" },
    { "SCUS", 0x8005905c, 0x8005921c, "berry_tough_damage_dispatch" },
    { "SCUS", 0x8005921c, 0x80059384, "sfx_all_enemies_defe_glue" },
    { "SCUS", 0x80059384, 0x800593e8, "enemy_contact_damage_store" },
    { "SCUS", 0x800593e8, 0x8005953c, "contact_scatter_component_decode" },
    { "SCUS", 0x8005953c, 0x80059e44, "pickup_effect_dispatch" },
    { "SCUS", 0x80059e44, 0x8005a0e0, "spawn_drop" },
    { "SCUS", 0x8005a0e0, 0x8005a0f0, "contact_object_spawn_full" },
    { "SCUS", 0x8005a0f0, 0x8005a308, "contact_object_spawn" },
    { "SCUS", 0x8005a308, 0x8005b12c, "berry_projectile_update" },
    { "SCUS", 0x8005b12c, 0x8005b134, "respawn_transition_state_handler_entry" },
    { "SCUS", 0x8005b134, 0x8005b440, "respawn_transition_state_handler" },
    { "SCUS", 0x8005b440, 0x8005b4e4, "transition_fade_draw_loop" },
    { "SCUS", 0x8005b4e4, 0x8005b4ec, "animated_overlay_display_loop_entry" },
    { "SCUS", 0x8005b4ec, 0x8005b70c, "animated_overlay_display_loop" },
    { "SCUS", 0x8005b70c, 0x8005b714, "gameplay_state_reset_cursor_seed_entry" },
    { "SCUS", 0x8005b714, 0x8005bc64, "gameplay_state_reset_cursor_seed" },
    { "SCUS", 0x8005bc64, 0x8005bdbc, "plant_slot_respawn_scan" },
    { "SCUS", 0x8005bdbc, 0x8005bfbc, "plant_spawn" },
    { "SCUS", 0x8005bfbc, 0x8005c110, "plant_behavior_walker" },
    { "SCUS", 0x8005c110, 0x8005c258, "seed_plant_cannon_handler" },
    { "SCUS", 0x8005c258, 0x8005c58c, "seed_plant_propeller_handler" },
    { "SCUS", 0x8005c58c, 0x8005c6f0, "seed_plant_trampoline_handler" },
    { "SCUS", 0x8005c6f0, 0x8005c744, "seed_plant_type6_handler" },
    { "SCUS", 0x8005c744, 0x8005c818, "seed_plant_type7_handler" },
    { "SCUS", 0x8005c818, 0x8005c918, "seed_plant_dandelion_handler" },
    { "SCUS", 0x8005c918, 0x8005ca24, "seed_plant_mine_handler" },
    { "SCUS", 0x8005ca24, 0x8005ca7c, "seed_plant_purple_shooter_handler" },
    { "SCUS", 0x8005ca7c, 0x8005cce8, "seed_plant_blue_shooter_handler" },
    { "SCUS", 0x8005cce8, 0x8005cd2c, "seed_plant_passive_handler" },
    { "SCUS", 0x8005cd2c, 0x8005d50c, "gameplay_effect_spawner" },
    { "SCUS", 0x8005d50c, 0x8005d51c, "set_gp_ptr_plus_c" },
    { "SCUS", 0x8005d51c, 0x8005d53c, "advance_parse_cursor_past_record" },
    { "SCUS", 0x8005d53c, 0x8005d654, "chunk_pointer_relocate_index_fixup" },
    { "SCUS", 0x8005d654, 0x8005d8d8, "level_chunk_loader" },
    { "SCUS", 0x8005d8d8, 0x8005d924, "actor_index_conditional_store" },
    { "SCUS", 0x8005d924, 0x8005dad0, "level_chunk_file_load" },
    { "SCUS", 0x8005dad0, 0x8005de60, "level_load_chunks" },
    { "SCUS", 0x8005de60, 0x8005ec1c, "load_character_models" },
    { "SCUS", 0x8005ec1c, 0x8005ec84, "angle_delta_wrap" },
    { "SCUS", 0x8005ec84, 0x8005ec94, "skin_transform_bone" },
    { "SCUS", 0x8005ec94, 0x8005f110, "anm_animation_player_keyframe_core" },
    { "SCUS", 0x8005f110, 0x8005f4ec, "anm_animation_crossfade_keyframe_core" },
    { "SCUS", 0x8005f4ec, 0x8005f5b8, "reset_actor_slot_field50" },
    { "SCUS", 0x8005f5b8, 0x8005f688, "record_array_state_field_set" },
    { "SCUS", 0x8005f688, 0x8005f690, "__main" },
    { "SCUS", 0x8005f690, 0x8005f6b4, "entry0" },
    { "SCUS", 0x8005f6b4, 0x8005f730, "stup1" },
    { "SCUS", 0x8005f730, 0x8005f73c, "stup0" },
    { "SCUS", 0x8005f7ec, 0x8005f7f8, "sprintf" },
    { "SCUS", 0x8005f7f8, 0x80060048, "vsprintf_core" },
    { "SCUS", 0x80060058, 0x800600c4, "memmove" },
    { "SCUS", 0x800600cc, 0x8006014c, "InitGeom" },
    { "SCUS", 0x80060154, 0x800601dc, "SquareRoot0" },
    { "SCUS", 0x800601e4, 0x80060270, "InvSquareRoot" },
    { "SCUS", 0x80060270, 0x80060284, "VectorNormalS" },
    { "SCUS", 0x80060284, 0x800602b0, "VectorNormal" },
    { "SCUS", 0x800602b0, 0x800602c4, "VectorNormalSS" },
    { "SCUS", 0x800602c4, 0x800602e0, "gte_svector_store_wrapper" },
    { "SCUS", 0x800602e0, 0x8006039c, "MSC02_OBJ_FC" },
    { "SCUS", 0x8006039c, 0x80060480, "MatrixNormal" },
    { "SCUS", 0x80060484, 0x80060590, "MulMatrix0" },
    { "SCUS", 0x80060594, 0x800605b8, "effect_mesh_tran_render_mesh_tr_glue" },
    { "SCUS", 0x800605c4, 0x800605f4, "SetRotMatrix" },
    { "SCUS", 0x800605f4, 0x80060614, "SetTransMatrix" },
    { "SCUS", 0x80060614, 0x8006062c, "gte_set_geom_offset" },
    { "SCUS", 0x80060634, 0x80060640, "gte_control_reg26_set" },
    { "SCUS", 0x80060644, 0x80060670, "RotTransPers" },
    { "SCUS", 0x80060674, 0x80060698, "bone_matrix_arra_object_mesh_dr_glue_0674" },
    { "SCUS", 0x800606a4, 0x8006071c, "RotTransPers4" },
    { "SCUS", 0x80060724, 0x800607a0, "RotAverage4" },
    { "SCUS", 0x800607a4, 0x80060854, "RotAverageNclip4" },
    { "SCUS", 0x80060854, 0x80060ae0, "RotMatrix" },
    { "SCUS", 0x80060ae4, 0x80060c64, "atan2_heading" },
    { "SCUS", 0x80060c64, 0x80060ccc, "_patch_gte" },
    { "SCUS", 0x80060cd4, 0x80060d04, "exception_context_save" },
    { "SCUS", 0x80060d04, 0x80060df0, "LoadTPage" },
    { "SCUS", 0x80060df0, 0x80060e58, "LoadClut" },
    { "SCUS", 0x80060e58, 0x80060ec0, "LoadClut2" },
    { "SCUS", 0x80060ec0, 0x80060f78, "SetDefDrawEnv" },
    { "SCUS", 0x80060f78, 0x80060fb4, "SetDefDispEnv" },
    { "SCUS", 0x80060fb4, 0x80060ff4, "SetDumpFnt" },
    { "SCUS", 0x80060ff4, 0x80061098, "FntLoad" },
    { "SCUS", 0x80061098, 0x80061350, "FntOpen" },
    { "SCUS", 0x80061350, 0x80061668, "FntFlush" },
    { "SCUS", 0x80061668, 0x80061678, "FntPrint" },
    { "SCUS", 0x80061678, 0x80061a48, "text_stream_printf" },
    { "SCUS", 0x80061a48, 0x80061a84, "GetTPage" },
    { "SCUS", 0x80061a84, 0x80061a9c, "GetClut" },
    { "SCUS", 0x80061a9c, 0x80061afc, "DumpTPage" },
    { "SCUS", 0x80061afc, 0x80061b3c, "DumpClut" },
    { "SCUS", 0x80061b3c, 0x80061b58, "NextPrim" },
    { "SCUS", 0x80061b58, 0x80061b74, "IsEndPrim" },
    { "SCUS", 0x80061b74, 0x80061bb0, "AddPrim" },
    { "SCUS", 0x80061bb0, 0x80061bec, "AddPrims" },
    { "SCUS", 0x80061bec, 0x80061c10, "CatPrim" },
    { "SCUS", 0x80061c10, 0x80061c28, "TermPrim" },
    { "SCUS", 0x80061c28, 0x80061c50, "SetSemiTrans" },
    { "SCUS", 0x80061c50, 0x80061c78, "SetShadeTex" },
    { "SCUS", 0x80061c78, 0x80061c8c, "SetPolyF3" },
    { "SCUS", 0x80061c8c, 0x80061ca0, "SetPolyFT3" },
    { "SCUS", 0x80061ca0, 0x80061cb4, "SetPolyG3" },
    { "SCUS", 0x80061cb4, 0x80061cc8, "SetPolyGT3" },
    { "SCUS", 0x80061cc8, 0x80061cdc, "SetPolyF4" },
    { "SCUS", 0x80061cdc, 0x80061cf0, "SetPolyFT4" },
    { "SCUS", 0x80061cf0, 0x80061d04, "SetPolyG4" },
    { "SCUS", 0x80061d04, 0x80061d18, "SetPolyGT4" },
    { "SCUS", 0x80061d18, 0x80061d2c, "SetSprt8" },
    { "SCUS", 0x80061d2c, 0x80061d40, "SetSprt16" },
    { "SCUS", 0x80061d40, 0x80061d54, "SetSprt" },
    { "SCUS", 0x80061d54, 0x80061d68, "SetTile1" },
    { "SCUS", 0x80061d68, 0x80061d7c, "SetTile8" },
    { "SCUS", 0x80061d7c, 0x80061d90, "SetTile16" },
    { "SCUS", 0x80061d90, 0x80061da4, "SetTile" },
    { "SCUS", 0x80061da4, 0x80061db8, "SetLineF2" },
    { "SCUS", 0x80061db8, 0x80061dcc, "SetLineG2" },
    { "SCUS", 0x80061dcc, 0x80061dec, "SetLineF3" },
    { "SCUS", 0x80061dec, 0x80061e0c, "SetLineG3" },
    { "SCUS", 0x80061e0c, 0x80061e2c, "SetLineF4" },
    { "SCUS", 0x80061e2c, 0x80061e4c, "SetLineG4" },
    { "SCUS", 0x80061e4c, 0x80061e78, "SetDrawTPage" },
    { "SCUS", 0x80061e78, 0x80061ed8, "SetDrawMove" },
    { "SCUS", 0x80061ed8, 0x80061f44, "SetDrawLoad" },
    { "SCUS", 0x80061f44, 0x80061f7c, "MargePrim" },
    { "SCUS", 0x80061f7c, 0x80062090, "DumpDrawEnv" },
    { "SCUS", 0x80062090, 0x8006213c, "DumpDispEnv" },
    { "SCUS", 0x8006213c, 0x800622c0, "ResetGraph" },
    { "SCUS", 0x800622c0, 0x800622c8, "SetGraphReverse" },
    { "SCUS", 0x800622c8, 0x800623d4, "libgpu_graph_mode_dispatch" },
    { "SCUS", 0x800623d4, 0x80062438, "SetGraphDebug" },
    { "SCUS", 0x80062438, 0x80062440, "SetGraphQueue" },
    { "SCUS", 0x80062440, 0x800624e4, "dma_callback_stub" },
    { "SCUS", 0x800624e4, 0x800624f4, "GetGraphType" },
    { "SCUS", 0x800624f4, 0x80062504, "GetGraphDebug" },
    { "SCUS", 0x80062504, 0x8006250c, "DrawSyncCallback" },
    { "SCUS", 0x8006250c, 0x80062560, "handler_register_8007fbd4" },
    { "SCUS", 0x80062560, 0x800625fc, "SetDispMask" },
    { "SCUS", 0x800625fc, 0x80062668, "DrawSync" },
    { "SCUS", 0x80062668, 0x80062790, "checkRECT" },
    { "SCUS", 0x80062790, 0x80062824, "ClearImage" },
    { "SCUS", 0x80062824, 0x800628c0, "ClearImage2" },
    { "SCUS", 0x800628c0, 0x80062924, "LoadImage" },
    { "SCUS", 0x80062924, 0x80062988, "StoreImage" },
    { "SCUS", 0x80062988, 0x80062a4c, "MoveImage" },
    { "SCUS", 0x80062a4c, 0x80062a54, "ClearOTag" },
    { "SCUS", 0x80062a54, 0x80062b04, "link_prim_packet_chain" },
    { "SCUS", 0x80062b04, 0x80062b9c, "ClearOTagR" },
    { "SCUS", 0x80062b9c, 0x80062bfc, "DrawPrim" },
    { "SCUS", 0x80062bfc, 0x80062c70, "DrawOTag" },
    { "SCUS", 0x80062c70, 0x80062d74, "frame_render_driver" },
    { "SCUS", 0x80062d74, 0x80062e90, "DrawOTagEnv" },
    { "SCUS", 0x80062e90, 0x80062ec8, "GetDrawEnv" },
    { "SCUS", 0x80062ec8, 0x80062ed0, "PutDispEnv" },
    { "SCUS", 0x80062ed0, 0x80063370, "frame_present_copy_worker" },
    { "SCUS", 0x80063370, 0x800633a8, "GetDispEnv" },
    { "SCUS", 0x800633a8, 0x800633b0, "GetODE" },
    { "SCUS", 0x800633b0, 0x800633d8, "call_vptr56_sign" },
    { "SCUS", 0x800633d8, 0x80063414, "SetTexWindow" },
    { "SCUS", 0x80063414, 0x80063498, "SetDrawArea" },
    { "SCUS", 0x80063498, 0x800634dc, "SetDrawOffset" },
    { "SCUS", 0x800634dc, 0x80063508, "SetPriority" },
    { "SCUS", 0x80063508, 0x80063560, "SetDrawMode" },
    { "SCUS", 0x80063560, 0x80063778, "SetDrawEnv" },
    { "SCUS", 0x80063778, 0x800639cc, "SetDrawEnv2" },
    { "SCUS", 0x800639cc, 0x80063a08, "drawenv_background_fill_builder" },
    { "SCUS", 0x80063a08, 0x80063a60, "get_mode" },
    { "SCUS", 0x80063a60, 0x80063b2c, "get_cs" },
    { "SCUS", 0x80063b2c, 0x80063bf8, "get_ce" },
    { "SCUS", 0x80063bf8, 0x80063c3c, "get_ofs" },
    { "SCUS", 0x80063c3c, 0x80063cc0, "get_tw" },
    { "SCUS", 0x80063cc0, 0x80063d70, "get_dx" },
    { "SCUS", 0x80063d70, 0x80063d88, "_status" },
    { "SCUS", 0x80063d88, 0x80063e70, "_otc" },
    { "SCUS", 0x80063e70, 0x800640cc, "_clr" },
    { "SCUS", 0x800640cc, 0x80064308, "_dws" },
    { "SCUS", 0x80064308, 0x8006458c, "_drs" },
    { "SCUS", 0x8006458c, 0x800645b4, "_ctl" },
    { "SCUS", 0x800645b4, 0x800645c8, "_getctl" },
    { "SCUS", 0x800645c8, 0x80064618, "_cwb" },
    { "SCUS", 0x80064618, 0x80064664, "_cwc" },
    { "SCUS", 0x80064664, 0x80064694, "_param" },
    { "SCUS", 0x80064694, 0x800646b8, "_addque" },
    { "SCUS", 0x800646b8, 0x80064998, "gpu_present_drawotag_vsync" },
    { "SCUS", 0x80064998, 0x800649a0, "_exeque" },
    { "SCUS", 0x800649a0, 0x80064c84, "dma_intr_install" },
    { "SCUS", 0x80064c84, 0x80064de0, "_reset" },
    { "SCUS", 0x80064de0, 0x80064f28, "_sync" },
    { "SCUS", 0x80064f28, 0x80064f5c, "set_alarm" },
    { "SCUS", 0x80064f5c, 0x800650c8, "get_alarm" },
    { "SCUS", 0x800650c8, 0x800651a4, "_version" },
    { "SCUS", 0x800651a4, 0x800651d0, "memset_2" },
    { "SCUS", 0x800651d0, 0x800651e0, "VSync" },
    { "SCUS", 0x800651e0, 0x80065318, "alarm_vsync_timeout" },
    { "SCUS", 0x80065318, 0x800653b4, "v_wait" },
    { "SCUS", 0x800653d4, 0x800653dc, "ResetCallback" },
    { "SCUS", 0x800653dc, 0x80065404, "ResetCallback_dispatch_tail" },
    { "SCUS", 0x80065404, 0x8006540c, "InterruptCallback" },
    { "SCUS", 0x8006540c, 0x80065434, "InterruptCallback_dispatch_tail" },
    { "SCUS", 0x80065434, 0x8006543c, "DMACallback" },
    { "SCUS", 0x8006543c, 0x80065464, "exec_queue_kick" },
    { "SCUS", 0x80065464, 0x80065498, "VSyncCallback" },
    { "SCUS", 0x80065498, 0x800654a0, "VSyncCallbacks" },
    { "SCUS", 0x800654a0, 0x800654c8, "VSyncCallbacks_dispatch_tail" },
    { "SCUS", 0x800654c8, 0x800654d0, "StopCallback" },
    { "SCUS", 0x800654d0, 0x800654f8, "StopCallback_dispatch_tail" },
    { "SCUS", 0x800654f8, 0x80065500, "RestartCallback" },
    { "SCUS", 0x80065500, 0x80065528, "RestartCallback_dispatch_tail" },
    { "SCUS", 0x80065528, 0x80065538, "CheckCallback" },
    { "SCUS", 0x80065538, 0x80065550, "GetIntrMask" },
    { "SCUS", 0x80065550, 0x8006556c, "SetIntrMask" },
    { "SCUS", 0x8006556c, 0x80065648, "startIntr" },
    { "SCUS", 0x80065648, 0x80065830, "trapIntr" },
    { "SCUS", 0x80065830, 0x80065984, "setIntr" },
    { "SCUS", 0x80065984, 0x80065a30, "stopIntr" },
    { "SCUS", 0x80065a30, 0x80065ab8, "restartIntr" },
    { "SCUS", 0x80065ab8, 0x80065ae4, "memclr" },
    { "SCUS", 0x80065af4, 0x80065b4c, "startIntrVSync" },
    { "SCUS", 0x80065b4c, 0x80065bc4, "trapIntrVSync" },
    { "SCUS", 0x80065bc4, 0x80065bf0, "setIntrVSync" },
    { "SCUS", 0x80065bf0, 0x80065c1c, "memclr_2" },
    { "SCUS", 0x80065c1c, 0x80065c6c, "startIntrDMA" },
    { "SCUS", 0x80065c6c, 0x80065c74, "trapIntrDMA" },
    { "SCUS", 0x80065c74, 0x80065df0, "trap_exception_report" },
    { "SCUS", 0x80065df0, 0x80065e98, "setIntrDMA" },
    { "SCUS", 0x80065e98, 0x80065ec4, "memclr_3" },
    { "SCUS", 0x80065ec4, 0x80065edc, "swap_global_80080e44" },
    { "SCUS", 0x80065edc, 0x80065eec, "load_global_80080e44" },
    { "SCUS", 0x80065fbc, 0x80065fcc, "EnterCriticalSection" },
    { "SCUS", 0x80065fcc, 0x80065fdc, "ExitCriticalSection" },
    { "SCUS", 0x8006607c, 0x80066118, "SetRCnt" },
    { "SCUS", 0x80066118, 0x80066150, "GetRCnt" },
    { "SCUS", 0x80066150, 0x80066180, "StartRCnt" },
    { "SCUS", 0x80066180, 0x800661b4, "StopRCnt" },
    { "SCUS", 0x800661b4, 0x800661e8, "ResetRCnt" },
    { "SCUS", 0x800661ec, 0x80066388, "file_dev_dir_hook_install_and_firstfile" },
    { "SCUS", 0x80066388, 0x80066488, "file_dev_dir_hook_trampoline" },
    { "SCUS", 0x800664b8, 0x800664c8, "load_global_80080e68" },
    { "SCUS", 0x800664c8, 0x80066558, "pad_subsystem_init" },
    { "SCUS", 0x80066558, 0x800665e8, "pad_subsystem_init_6558" },
    { "SCUS", 0x800665e8, 0x80066618, "pad_subsystem_init_65e8" },
    { "SCUS", 0x80066618, 0x80066650, "pad_subsystem_shutdown" },
    { "SCUS", 0x80066650, 0x800666c8, "pad_intr_enqueue" },
    { "SCUS", 0x800666c8, 0x80066700, "interrupt_handler_dequeue" },
    { "SCUS", 0x80066700, 0x80066768, "pad_reset_wait_delay" },
    { "SCUS", 0x80066768, 0x800667a8, "pad_status_ready_check" },
    { "SCUS", 0x8006680c, 0x80066820, "call_via_ptr_80086aa8" },
    { "SCUS", 0x80066820, 0x80066834, "pad_stop_driver_thunk" },
    { "SCUS", 0x80066834, 0x800668a4, "icache_flush_glue" },
    { "SCUS", 0x800668ac, 0x80066914, "icache_flush_glue_68ac" },
    { "SCUS", 0x8006691c, 0x80066b90, "SsSeqCalledTbyT" },
    { "SCUS", 0x80066b90, 0x80066e8c, "_SsSndCrescendo" },
    { "SCUS", 0x80066e8c, 0x80067148, "_SsSndDecrescendo" },
    { "SCUS", 0x80067148, 0x800671e4, "_SsSndPause" },
    { "SCUS", 0x800671e4, 0x80067210, "_SsSndPlay" },
    { "SCUS", 0x80067210, 0x80067318, "_SsSeqPlay" },
    { "SCUS", 0x80067318, 0x8006755c, "_SsSeqGetEof" },
    { "SCUS", 0x8006755c, 0x80067904, "_SsGetSeqData" },
    { "SCUS", 0x80067904, 0x800679b4, "_SsReadDeltaValue" },
    { "SCUS", 0x800679b4, 0x80067ab0, "_SsSndNextSep" },
    { "SCUS", 0x80067ab0, 0x80067b10, "_SsSndReplay" },
    { "SCUS", 0x80067b10, 0x80067bf8, "_SsInit" },
    { "SCUS", 0x80067bf8, 0x80067c28, "sound_lib_init_sequence" },
    { "SCUS", 0x80067c28, 0x80067c78, "SsSetMVol" },
    { "SCUS", 0x80067c78, 0x80067ee0, "_SsStart" },
    { "SCUS", 0x80067ee0, 0x80067f00, "SpuInitHot" },
    { "SCUS", 0x80067f00, 0x80067f20, "SpuInit" },
    { "SCUS", 0x80067f20, 0x80067f60, "_SsTrapIntrVSync" },
    { "SCUS", 0x80067f60, 0x80067f68, "_SsSeqCalledTbyT_1per2" },
    { "SCUS", 0x80067f68, 0x80067fb0, "ss_seq_tick_every_other_dispatch" },
    { "SCUS", 0x80067fb0, 0x80068134, "seq_playback_state_init" },
    { "SCUS", 0x80068134, 0x8006815c, "seq_state_init_wrapper_one_arg" },
    { "SCUS", 0x8006815c, 0x80068188, "seq_state_init_wrapper_two_arg" },
    { "SCUS", 0x80068188, 0x80068284, "SsSetSerialVol" },
    { "SCUS", 0x80068284, 0x800683f0, "SsSetTickMode" },
    { "SCUS", 0x800683f0, 0x80068414, "sound_state_set_if_changed" },
    { "SCUS", 0x80068414, 0x80068634, "_SsSndTempo" },
    { "SCUS", 0x80068634, 0x800689d0, "SsUtKeyOn" },
    { "SCUS", 0x800689d0, 0x80068b24, "SsUtKeyOff" },
    { "SCUS", 0x80068b24, 0x80068eb8, "SsUtKeyOnV" },
    { "SCUS", 0x80068eb8, 0x80068f30, "SsUtKeyOffV" },
    { "SCUS", 0x80068f30, 0x80068f88, "SsUtGetDetVVol" },
    { "SCUS", 0x80068f88, 0x80068ff4, "SsUtSetDetVVol" },
    { "SCUS", 0x80068ff4, 0x80069080, "SsUtGetVVol" },
    { "SCUS", 0x80069080, 0x80069164, "SsUtSetVVol" },
    { "SCUS", 0x80069164, 0x800693f0, "_SsVmAlloc" },
    { "SCUS", 0x800693f0, 0x80069604, "_SsVmDoAllocate" },
    { "SCUS", 0x80069604, 0x80069614, "clear_global_short_80091610" },
    { "SCUS", 0x80069614, 0x800699c8, "_SsVmFlush" },
    { "SCUS", 0x800699c8, 0x80069cd8, "_SsVmInit" },
    { "SCUS", 0x80069cd8, 0x80069d9c, "note2pitch" },
    { "SCUS", 0x80069d9c, 0x80069e98, "note2pitch2" },
    { "SCUS", 0x80069e98, 0x8006a35c, "vmNoiseOn" },
    { "SCUS", 0x8006a35c, 0x8006a3a0, "vmNoiseOff" },
    { "SCUS", 0x8006a3a0, 0x8006a470, "_SsVmKeyOffNow" },
    { "SCUS", 0x8006a470, 0x8006a920, "_SsVmKeyOnNow" },
    { "SCUS", 0x8006a920, 0x8006ae58, "_SsVmSetSeqVol" },
    { "SCUS", 0x8006ae58, 0x8006aebc, "_SsVmGetSeqVol" },
    { "SCUS", 0x8006aebc, 0x8006af04, "_SsVmGetSeqLVol" },
    { "SCUS", 0x8006af04, 0x8006af4c, "_SsVmGetSeqRVol" },
    { "SCUS", 0x8006af4c, 0x8006af54, "_SsVmSeqKeyOff" },
    { "SCUS", 0x8006af54, 0x8006afe8, "ss_vm_seq_keyoff_body" },
    { "SCUS", 0x8006afe8, 0x8006b0ac, "_SsVmVSetUp" },
    { "SCUS", 0x8006b0ac, 0x8006b130, "SsVabClose" },
    { "SCUS", 0x8006b130, 0x8006b160, "SsVabOpenHead" },
    { "SCUS", 0x8006b160, 0x8006b190, "SsVabOpenHeadSticky" },
    { "SCUS", 0x8006b190, 0x8006b1c0, "SsVabFakeHead" },
    { "SCUS", 0x8006b1c0, 0x8006b59c, "SsVabOpenHeadWithMode" },
    { "SCUS", 0x8006b59c, 0x8006b65c, "SsVabTransBody" },
    { "SCUS", 0x8006b65c, 0x8006b684, "SsVabTransCompleted" },
    { "SCUS", 0x8006b684, 0x8006b6a4, "spu__spu_init_glue" },
    { "SCUS", 0x8006b6a4, 0x8006b79c, "_SpuInit" },
    { "SCUS", 0x8006b79c, 0x8006b7a4, "SpuStart" },
    { "SCUS", 0x8006b7a4, 0x8006b818, "event_open_enable" },
    { "SCUS", 0x8006b818, 0x8006baac, "_spu_init" },
    { "SCUS", 0x8006baac, 0x8006babc, "_spu_FwriteByIO" },
    { "SCUS", 0x8006babc, 0x8006bc78, "spu_fwrite_by_io_body" },
    { "SCUS", 0x8006bc78, 0x8006bc80, "_spu_FiDMA" },
    { "SCUS", 0x8006bc80, 0x8006bd38, "spu_fidma_body" },
    { "SCUS", 0x8006bd38, 0x8006bd40, "_spu_Fr_" },
    { "SCUS", 0x8006bd40, 0x8006bde4, "spu_fr_body" },
    { "SCUS", 0x8006bde4, 0x8006bdf4, "_spu_t" },
    { "SCUS", 0x8006bdf4, 0x8006c074, "spu_transfer_mode_dispatch_body" },
    { "SCUS", 0x8006c074, 0x8006c07c, "_spu_Fw" },
    { "SCUS", 0x8006c07c, 0x8006c0fc, "spu_fw_body" },
    { "SCUS", 0x8006c0fc, 0x8006c164, "_spu_Fr" },
    { "SCUS", 0x8006c164, 0x8006c1ac, "_spu_FsetRXX" },
    { "SCUS", 0x8006c1ac, 0x8006c250, "_spu_FsetRXXa" },
    { "SCUS", 0x8006c250, 0x8006c28c, "_spu_FgetRXXa" },
    { "SCUS", 0x8006c28c, 0x8006c2ec, "_spu_FsetPCR" },
    { "SCUS", 0x8006c2ec, 0x8006c318, "_spu_FsetDelayW" },
    { "SCUS", 0x8006c318, 0x8006c344, "_spu_FsetDelayR" },
    { "SCUS", 0x8006c344, 0x8006c3ac, "_spu_Fw1ts" },
    { "SCUS", 0x8006c3bc, 0x8006c3e0, "_SpuDataCallback" },
    { "SCUS", 0x8006c3e0, 0x8006c434, "SpuInitMalloc" },
    { "SCUS", 0x8006c434, 0x8006c43c, "SpuMalloc" },
    { "SCUS", 0x8006c43c, 0x8006c6fc, "spu_malloc_body" },
    { "SCUS", 0x8006c6fc, 0x8006ca04, "_spu_gcSPU" },
    { "SCUS", 0x8006ca04, 0x8006ca80, "SpuFree" },
    { "SCUS", 0x8006ca80, 0x8006caa4, "SpuSetNoiseVoice" },
    { "SCUS", 0x8006caa4, 0x8006ccac, "_SpuSetAnyVoice" },
    { "SCUS", 0x8006ccac, 0x8006cd0c, "SpuRead" },
    { "SCUS", 0x8006cd0c, 0x8006cd64, "SpuSetTransferStartAddr" },
    { "SCUS", 0x8006cd64, 0x8006cd98, "SpuSetTransferMode" },
    { "SCUS", 0x8006cd98, 0x8006cda0, "SpuIsTransferCompleted" },
    { "SCUS", 0x8006cda0, 0x8006ce40, "event_poll_wait" },
    { "SCUS", 0x8006ce40, 0x8006ce6c, "ss_vab_set_transfer_mode" },
    { "SCUS", 0x8006ce6c, 0x8006ce84, "global_814f8_ne_1" },
    { "SCUS", 0x8006ce84, 0x8006d218, "SpuSetCommonAttr" },
    { "SCUS", 0x8006d218, 0x8006d2e8, "SpuRGetAllKeysStatus" },
    { "SCUS", 0x8006d2e8, 0x8006d370, "SpuGetAllKeysStatus" },
    { "SCUS", 0x8006d370, 0x8006d3a4, "SpuSetVoicePitch" },
    { "SCUS", 0x8006d3a4, 0x8006d3d4, "StSetRing" },
    { "SCUS", 0x8006d3d4, 0x8006d3f8, "CdGetToc" },
    { "SCUS", 0x8006d3f8, 0x8006d61c, "CdGetToc2" },
    { "SCUS", 0x8006d61c, 0x8006d6b4, "CdInit" },
    { "SCUS", 0x8006d6b4, 0x8006d6dc, "def_cbsync" },
    { "SCUS", 0x8006d6dc, 0x8006d704, "def_cbready" },
    { "SCUS", 0x8006d704, 0x8006d72c, "def_cbread" },
    { "SCUS", 0x8006d72c, 0x8006d73c, "CdStatus" },
    { "SCUS", 0x8006d73c, 0x8006d74c, "CdMode" },
    { "SCUS", 0x8006d74c, 0x8006d75c, "CdLastCom" },
    { "SCUS", 0x8006d75c, 0x8006d76c, "CdLastPos" },
    { "SCUS", 0x8006d76c, 0x8006d7d8, "CdReset" },
    { "SCUS", 0x8006d7d8, 0x8006d7f8, "CdFlush" },
    { "SCUS", 0x8006d7f8, 0x8006d810, "CdSetDebug" },
    { "SCUS", 0x8006d810, 0x8006d844, "CdComstr" },
    { "SCUS", 0x8006d844, 0x8006d878, "CdIntstr" },
    { "SCUS", 0x8006d878, 0x8006d898, "CdSync" },
    { "SCUS", 0x8006d898, 0x8006d8b8, "CdReady" },
    { "SCUS", 0x8006d8b8, 0x8006d8d0, "CdSyncCallback" },
    { "SCUS", 0x8006d8d0, 0x8006d8e8, "CdReadyCallback" },
    { "SCUS", 0x8006d8e8, 0x8006da20, "CdControl" },
    { "SCUS", 0x8006da20, 0x8006db4c, "CdControlF" },
    { "SCUS", 0x8006db4c, 0x8006dc90, "CdControlB" },
    { "SCUS", 0x8006dc90, 0x8006dcb0, "CdMix" },
    { "SCUS", 0x8006dcb0, 0x8006dcd0, "CdGetSector" },
    { "SCUS", 0x8006dcd0, 0x8006dcf0, "CdGetSector2" },
    { "SCUS", 0x8006dcf0, 0x8006dd14, "CdDataCallback" },
    { "SCUS", 0x8006dd14, 0x8006dd34, "CdDataSync" },
    { "SCUS", 0x8006dd34, 0x8006de38, "CdIntToPos" },
    { "SCUS", 0x8006de38, 0x8006deb8, "CdPosToInt" },
    { "SCUS", 0x8006deb8, 0x8006e440, "getintr" },
    { "SCUS", 0x8006e440, 0x8006e6c0, "CD_sync" },
    { "SCUS", 0x8006e6c0, 0x8006e98c, "CD_ready" },
    { "SCUS", 0x8006e98c, 0x8006eda8, "CD_cw" },
    { "SCUS", 0x8006eda8, 0x8006ee30, "CD_vol" },
    { "SCUS", 0x8006ee30, 0x8006ef10, "CD_flush" },
    { "SCUS", 0x8006ef10, 0x8006f004, "CD_initvol" },
    { "SCUS", 0x8006f004, 0x8006f054, "CD_initintr" },
    { "SCUS", 0x8006f054, 0x8006f240, "CD_init" },
    { "SCUS", 0x8006f240, 0x8006f3ac, "CD_datasync" },
    { "SCUS", 0x8006f3ac, 0x8006f4ac, "CD_getsector" },
    { "SCUS", 0x8006f4ac, 0x8006f59c, "CD_getsector2" },
    { "SCUS", 0x8006f59c, 0x8006f5ac, "CD_set_test_parmnum" },
    { "SCUS", 0x8006f5ac, 0x8006f5b4, "callback" },
    { "SCUS", 0x8006f5b4, 0x8006f690, "cd_interrupt_callback_body" },
    { "SCUS", 0x8006f690, 0x8006f6a0, "CdSearchFile" },
    { "SCUS", 0x8006f6a0, 0x8006f95c, "cd_media_dir_cache" },
    { "SCUS", 0x8006f95c, 0x8006f97c, "_cmp" },
    { "SCUS", 0x8006f97c, 0x8006fc5c, "CD_newmedia" },
    { "SCUS", 0x8006fc5c, 0x8006fd04, "CD_searchdir" },
    { "SCUS", 0x8006fd04, 0x8006fd0c, "CD_cachefile" },
    { "SCUS", 0x8006fd0c, 0x8006ffb0, "cd_sector_read_seek" },
    { "SCUS", 0x8006ffb0, 0x8007001c, "cd_read" },
    { "SCUS", 0x8007001c, 0x800702ec, "cb_read" },
    { "SCUS", 0x800702ec, 0x80070354, "cb_data" },
    { "SCUS", 0x80070354, 0x800703e8, "cd_ready_poll_control" },
    { "SCUS", 0x800703e8, 0x800705fc, "cd_read_retry" },
    { "SCUS", 0x800705fc, 0x80070698, "CdReadBreak" },
    { "SCUS", 0x80070698, 0x8007079c, "CdRead" },
    { "SCUS", 0x8007079c, 0x80070868, "CdReadSync" },
    { "SCUS", 0x80070868, 0x80070880, "CdReadCallback" },
    { "SCUS", 0x80070880, 0x80070898, "CdReadMode" },
    { "SCUS", 0x80070898, 0x8007092c, "CdRead2" },
    { "SCUS", 0x8007092c, 0x8007094c, "StCdInterrupt2" },
    { "SCUS", 0x8007094c, 0x800709ac, "StClearRing" },
    { "SCUS", 0x800709ac, 0x80070a30, "cd_ready_poll_control_09ac" },
    { "SCUS", 0x80070a30, 0x80070ac0, "str_data_ready_callback" },
    { "SCUS", 0x80070ac0, 0x80070b20, "StGetBackloc" },
    { "SCUS", 0x80070b20, 0x80070ba8, "StSetStream" },
    { "SCUS", 0x80070ba8, 0x80070c60, "StFreeRing" },
    { "SCUS", 0x80070c60, 0x80070c9c, "init_ring_status" },
    { "SCUS", 0x80070c9c, 0x80070d60, "StGetNext" },
    { "SCUS", 0x80070d60, 0x80070d80, "stream_config_store" },
    { "SCUS", 0x80070d80, 0x800716f0, "StCdInterrupt" },
    { "SCUS", 0x800716f0, 0x80071724, "mem2mem" },
    { "SCUS", 0x80071724, 0x800718e0, "dma_execute" },
    { "SCUS", 0x800718e0, 0x80071900, "PadChkVsync" },
    { "SCUS", 0x80071900, 0x80071920, "PadStartCom" },
    { "SCUS", 0x80071920, 0x80071940, "PadStopCom" },
    { "SCUS", 0x80071940, 0x8007198c, "PadChkMtap" },
    { "SCUS", 0x8007198c, 0x80071a58, "PadGetState" },
    { "SCUS", 0x80071a58, 0x80071b50, "PadInfoMode" },
    { "SCUS", 0x80071b50, 0x80071c24, "PadInfoAct" },
    { "SCUS", 0x80071c24, 0x80071ccc, "PadInfoComb" },
    { "SCUS", 0x80071ccc, 0x80071d04, "PadSetActAlign" },
    { "SCUS", 0x80071d04, 0x80071d4c, "PadSetMainMode" },
    { "SCUS", 0x80071d4c, 0x80071da0, "PadSetAct" },
    { "SCUS", 0x80071da0, 0x80071eb8, "PadEnableCom" },
    { "SCUS", 0x80071eb8, 0x80071ee4, "_padSetVsyncParam" },
    { "SCUS", 0x80071ee4, 0x80071f4c, "pad_sio_irq_callback" },
    { "SCUS", 0x80071f4c, 0x800720dc, "pad_vsync_handler" },
    { "SCUS", 0x800720dc, 0x800720f0, "pad_vsync_latch_consume" },
    { "SCUS", 0x800720f0, 0x800721bc, "_padStartCom" },
    { "SCUS", 0x800721bc, 0x80072200, "_padStopCom" },
    { "SCUS", 0x80072200, 0x80072534, "_padInitSioMode" },
    { "SCUS", 0x80072534, 0x80072624, "pad_sio_advance_stage" },
    { "SCUS", 0x80072624, 0x80072834, "_padSioRW" },
    { "SCUS", 0x80072834, 0x80072aac, "_padSioRW2" },
    { "SCUS", 0x80072aac, 0x80072b3c, "_padClrIntSio0" },
    { "SCUS", 0x80072b3c, 0x80072b64, "_padWaitRXready" },
    { "SCUS", 0x80072b70, 0x80072b7c, "_padSetAct" },
    { "SCUS", 0x80072b7c, 0x80072b8c, "store_three_fields" },
    { "SCUS", 0x80072b8c, 0x80072c10, "_padSendAtLoadInfo" },
    { "SCUS", 0x80072c10, 0x80072e80, "_padRecvAtLoadInfo" },
    { "SCUS", 0x80072e80, 0x80072eb8, "_padGetActSize" },
    { "SCUS", 0x80072eb8, 0x80072f8c, "_padLoadActInfo" },
    { "SCUS", 0x80072f8c, 0x80073034, "sub_80072f8c" },
    { "SCUS", 0x80073034, 0x8007342c, "sub_80073034" },
    { "SCUS", 0x8007342c, 0x80073494, "_padSetActAlign" },
    { "SCUS", 0x80073494, 0x800734b0, "sub_80073494" },
    { "SCUS", 0x800734b0, 0x80073578, "sub_800734b0" },
    { "SCUS", 0x80073578, 0x80073610, "_padSetMainMode" },
    { "SCUS", 0x80073610, 0x80073664, "sub_80073610" },
    { "SCUS", 0x80073664, 0x800736c4, "sub_80073664" },
    { "SCUS", 0x800736c4, 0x800736e4, "_padCmdParaMode" },
    { "SCUS", 0x800736e4, 0x800736f8, "init_fields_45" },
    { "SCUS", 0x800736f8, 0x80073718, "sub_800736f8" },
    { "SCUS", 0x80073718, 0x80073738, "sub_80073718" },
    { "SCUS", 0x80073738, 0x80073758, "sub_80073738" },
    { "SCUS", 0x80073758, 0x8007376c, "init_fields_4b" },
    { "SCUS", 0x80073770, 0x800737b8, "pad_sio_stage_begin" },
    { "SCUS", 0x800737b8, 0x80073890, "pad_sio_stage_command" },
    { "SCUS", 0x80073890, 0x8007393c, "pad_sio_stage_length" },
    { "SCUS", 0x8007393c, 0x800739c8, "pad_sio_stage_transfer" },
    { "SCUS", 0x800739c8, 0x80073d78, "pad_sio_stage_finish" },
    { "SCUS", 0x80073d7c, 0x80073d80, "sub_80073d7c" },
    { "SCUS", 0x80073d80, 0x80073ee0, "PadInitDirect" },
    { "SCUS", 0x80073ee0, 0x80073f48, "pad_direct_clear_info" },
    { "SCUS", 0x80073f48, 0x8007403c, "pad_direct_next_port" },
    { "SCUS", 0x8007403c, 0x8007404c, "pad_direct_clear_command" },
    { "SCUS", 0x8007404c, 0x80074108, "pad_direct_get_txd" },
    { "SCUS", 0x80074108, 0x80074384, "pad_direct_current_limit" },
    { "SCUS", 0x80074384, 0x800743bc, "pad_direct_ptr_to_port" },
    { "SCUS", 0x800743bc, 0x800743dc, "pad_direct_port_to_info" },
    { "SCUS", 0x800743dc, 0x800743e0, "sub_800743dc" },
    { "SCUS", 0x800743ec, 0x800743f0, "sub_800743ec" },
    { "SCUS", 0x800743f0, 0x80074424, "_padInitDirSeq" },
    { "SCUS", 0x80074424, 0x80074534, "pad_direct_send_auto" },
    { "SCUS", 0x80074534, 0x80074798, "pad_direct_recv_auto" },
    { "SCUS", 0x80074798, 0x80074878, "_dirFailAuto" },
    { "SCUS", 0x80074878, 0x800748a4, "pad_direct_engine_ready" },
    { "SCUS", 0x800748b0, 0x800748d0, "setRC2wait" },
    { "SCUS", 0x800748d0, 0x80074970, "chkRC2wait" },
    { "LEVEL01_LEVEL", 0x800b39a4, 0x800b3aec, "level_overlay_init" },
    { "LEVEL01_LEVEL", 0x800b3aec, 0x800b3bb8, "level_state_writer" },
    { "LEVEL01_LEVEL", 0x800b3bb8, 0x800b3f54, "level_spawn_region_handler" },
    { "LEVEL01_LEVEL1", 0x800b39a4, 0x800b3af4, "level_overlay_init" },
    { "LEVEL01_LEVEL1", 0x800b3af4, 0x800b3b58, "level_state_writer" },
    { "LEVEL01_LEVEL1", 0x800b3b58, 0x800b3b68, "level_state_writer_b58" },
    { "LEVEL01_LEVEL1", 0x800b3b68, 0x800b42f0, "level_actor_event_handler" },
    { "LEVEL02_LEVEL", 0x800b39a4, 0x800b3aec, "level_overlay_init" },
    { "LEVEL02_LEVEL", 0x800b3aec, 0x800b3b70, "level_state_writer" },
    { "LEVEL02_LEVEL", 0x800b3b70, 0x800b3b84, "set_state_60" },
    { "LEVEL02_LEVEL", 0x800b3b84, 0x800b3b8c, "level_audio_handler" },
    { "LEVEL02_LEVEL", 0x800b3b8c, 0x800b4860, "level_completion_handler" },
    { "LEVEL02_LEVEL1", 0x800b39c8, 0x800b3b0c, "level_overlay_draw" },
    { "LEVEL02_LEVEL1", 0x800b3b0c, 0x800b3b14, "empty_stub" },
    { "LEVEL02_LEVEL1", 0x800b3b14, 0x800b3d04, "level_state_writer" },
    { "LEVEL02_LEVEL1", 0x800b3d04, 0x800b3f00, "level_completion_handler" },
    { "LEVEL02_LEVEL1", 0x800b3f00, 0x800b3f08, "level_state_writer_f00" },
    { "LEVEL02_LEVEL1", 0x800b3f08, 0x800b48f4, "level_completion_handler_f08" },
    { "LEVEL02_LEVEL1", 0x800b48f4, 0x800b4a50, "color_channel_lerp" },
    { "LEVEL03_LEVEL", 0x800b39a4, 0x800b3adc, "level_overlay_init" },
    { "LEVEL03_LEVEL", 0x800b3adc, 0x800b3c54, "level_state_init" },
    { "LEVEL03_LEVEL", 0x800b3c54, 0x800b3d78, "level_ground_query" },
    { "LEVEL03_LEVEL", 0x800b3d78, 0x800b3e88, "level_spawn_handler" },
    { "LEVEL03_LEVEL", 0x800b3e88, 0x800b3e98, "level_state_writer" },
    { "LEVEL03_LEVEL", 0x800b3e98, 0x800b42ac, "level_object_spawn_handler" },
    { "LEVEL03_LEVEL", 0x800b42ac, 0x800b4a0c, "level_object_spawn_handler_2ac" },
    { "LEVEL03_LEVEL1", 0x800b39a4, 0x800b3adc, "level_overlay_init" },
    { "LEVEL03_LEVEL1", 0x800b3adc, 0x800b3b2c, "init_overlay_state" },
    { "LEVEL03_LEVEL1", 0x800b3b2c, 0x800b4490, "level_completion_handler" },
    { "LEVEL04_LEVEL", 0x800b39a4, 0x800b39a8, "level_overlay_init" },
    { "LEVEL04_LEVEL", 0x800b39a8, 0x800b39b8, "level_state_writer_9a8" },
    { "LEVEL04_LEVEL", 0x800b39b8, 0x800b3b08, "level_overlay_draw" },
    { "LEVEL04_LEVEL", 0x800b3b08, 0x800b3c5c, "level_state_writer" },
    { "LEVEL04_LEVEL", 0x800b3c5c, 0x800b3cd8, "level_ground_query" },
    { "LEVEL04_LEVEL", 0x800b3cd8, 0x800b3d84, "level_state_writer_cd8" },
    { "LEVEL04_LEVEL", 0x800b3d84, 0x800b3f3c, "level_audio_handler" },
    { "LEVEL04_LEVEL", 0x800b3f3c, 0x800b4414, "level04_complete_handler" },
    { "LEVEL04_LEVEL1", 0x800b39a4, 0x800b3aec, "level_overlay_init" },
    { "LEVEL04_LEVEL1", 0x800b3aec, 0x800b3b14, "add_child_field_20" },
    { "LEVEL04_LEVEL1", 0x800b3b14, 0x800b3c70, "level_state_writer" },
    { "LEVEL04_LEVEL1", 0x800b3c70, 0x800b3c78, "level_state_writer_c70" },
    { "LEVEL04_LEVEL1", 0x800b3c78, 0x800b4b24, "level_completion_handler" },
    { "LEVEL05_LEVEL", 0x800b39a4, 0x800b39a8, "level_overlay_init" },
    { "LEVEL05_LEVEL", 0x800b39c8, 0x800b3b18, "level_overlay_draw" },
    { "LEVEL05_LEVEL", 0x800b3b18, 0x800b3b54, "init_overlay_state" },
    { "LEVEL05_LEVEL", 0x800b3b54, 0x800b3d78, "level_audio_handler" },
    { "LEVEL05_LEVEL", 0x800b3d78, 0x800b3d80, "level_audio_handler_d78" },
    { "LEVEL05_LEVEL", 0x800b3d80, 0x800b410c, "level_completion_handler" },
    { "LEVEL05_LEVEL1", 0x800b39a4, 0x800b39b8, "level_overlay_init" },
    { "LEVEL05_LEVEL1", 0x800b39b8, 0x800b3afc, "level_overlay_draw" },
    { "LEVEL05_LEVEL1", 0x800b3afc, 0x800b3bd4, "level05_overlay_param_init" },
    { "LEVEL05_LEVEL1", 0x800b3bd4, 0x800b3c04, "compare_overlay_halfword" },
    { "LEVEL05_LEVEL1", 0x800b3c04, 0x800b4a88, "level_completion_handler" },
    { "LEVEL06_LEVEL", 0x800b39a4, 0x800b3aec, "level_overlay_init" },
    { "LEVEL06_LEVEL", 0x800b3aec, 0x800b3b94, "level_state_writer" },
    { "LEVEL06_LEVEL", 0x800b3b94, 0x800b3bbc, "clear_overlay_state" },
    { "LEVEL06_LEVEL", 0x800b3bbc, 0x800b3bc4, "transition_handler_arg_entry" },
    { "LEVEL06_LEVEL", 0x800b3bc4, 0x800b3f04, "level_transition_handler" },
    { "LEVEL06_LEVEL1", 0x800b39a4, 0x800b3af4, "level_overlay_init" },
    { "LEVEL06_LEVEL1", 0x800b3af4, 0x800b3b30, "level06_select_grid_offset" },
    { "LEVEL06_LEVEL1", 0x800b3b30, 0x800b3c98, "level_state_writer" },
    { "LEVEL06_LEVEL1", 0x800b3c98, 0x800b3ca8, "level_state_writer_c98" },
    { "LEVEL06_LEVEL1", 0x800b3ca8, 0x800b3f78, "level_spawn_handler" },
    { "LEVEL07_LEVEL", 0x800b39c8, 0x800b3b00, "level_overlay_draw" },
    { "LEVEL07_LEVEL", 0x800b3b00, 0x800b3c54, "level_state_writer" },
    { "LEVEL07_LEVEL", 0x800b3c54, 0x800b3da8, "level_state_writer_c54" },
    { "LEVEL07_LEVEL", 0x800b3da8, 0x800b3fc8, "level_state_writer_da8" },
    { "LEVEL07_LEVEL", 0x800b3fc8, 0x800b3fd0, "level_state_writer_fc8" },
    { "LEVEL07_LEVEL", 0x800b3fd0, 0x800b42ac, "level_fx_mesh_handler" },
    { "LEVEL07_LEVEL", 0x800b42ac, 0x800b54e8, "level_completion_handler" },
    { "LEVEL07_LEVEL1", 0x800b39dc, 0x800b3b54, "level_overlay_draw" },
    { "LEVEL07_LEVEL1", 0x800b3b54, 0x800b3c94, "level_completion_sub" },
    { "LEVEL07_LEVEL1", 0x800b3c94, 0x800b3c9c, "state_writer_arg_entry" },
    { "LEVEL07_LEVEL1", 0x800b3c9c, 0x800b3f00, "level_state_writer" },
    { "LEVEL07_LEVEL1", 0x800b3f00, 0x800b3f08, "level_completion_wrapper" },
    { "LEVEL07_LEVEL1", 0x800b3f08, 0x800b3f48, "dispatch_small_mode" },
    { "LEVEL07_LEVEL1", 0x800b3f48, 0x800b3f58, "level_state_writer_f48" },
    { "LEVEL07_LEVEL1", 0x800b3f58, 0x800b492c, "level_transition_handler" },
    { "LEVEL08_LEVEL", 0x800b39a4, 0x800b3ae8, "level_overlay_init" },
    { "LEVEL08_LEVEL", 0x800b3ae8, 0x800b3b54, "level_audio_handler" },
    { "LEVEL08_LEVEL", 0x800b3b54, 0x800b3c74, "level_state_writer" },
    { "LEVEL08_LEVEL", 0x800b3c74, 0x800b3c7c, "level_state_writer_c74" },
    { "LEVEL08_LEVEL", 0x800b3c7c, 0x800b4390, "level_actor_ai_handler" },
    { "LEVEL08_LEVEL1", 0x800b39a4, 0x800b3aec, "level_overlay_init" },
    { "LEVEL08_LEVEL1", 0x800b3aec, 0x800b3b70, "level_overlay_draw" },
    { "LEVEL08_LEVEL1", 0x800b3b70, 0x800b3c74, "level_ground_handler" },
    { "LEVEL08_LEVEL1", 0x800b3c74, 0x800b4084, "level_actor_move_handler" },
    { "LEVEL08_LEVEL1", 0x800b4084, 0x800b47c0, "level_render_hud_handler" },
    { "LEVEL09_LEVEL", 0x800b39a4, 0x800b3aec, "level_overlay_init" },
    { "LEVEL09_LEVEL", 0x800b3aec, 0x800b3b70, "level_overlay_draw" },
    { "LEVEL09_LEVEL", 0x800b3b70, 0x800b3bd0, "clear_flags_set_tail" },
    { "LEVEL09_LEVEL", 0x800b3bd0, 0x800b3c2c, "set_flags_clear_tail" },
    { "LEVEL09_LEVEL", 0x800b3c2c, 0x800b3dc8, "level_state_writer" },
    { "LEVEL09_LEVEL", 0x800b3dc8, 0x800b3de8, "call_set_flags_clear_tail" },
    { "LEVEL09_LEVEL", 0x800b3de8, 0x800b4cd0, "level_actor_ai_handler" },
    { "LEVEL09_LEVEL1", 0x800b39a4, 0x800b3aec, "level_overlay_init" },
    { "LEVEL10_LEVEL", 0x800b39a4, 0x800b3adc, "level_overlay_init" },
    { "LEVEL10_LEVEL", 0x800b3adc, 0x800b3bf0, "level_ground_query" },
    { "LEVEL10_LEVEL", 0x800b3bf0, 0x800b3c1c, "init_overlay_state" },
    { "LEVEL10_LEVEL", 0x800b3c1c, 0x800b40b8, "level_object_spawn_handler" },
    { "MEMORY", 0x800b5ba8, 0x800b5f78, "frontend_sprite_draw" },
    { "MEMORY", 0x800b5f78, 0x800b6138, "frontend_page_draw_f78" },
    { "MEMORY", 0x800b6138, 0x800b653c, "frontend_tpage_draw" },
    { "MEMORY", 0x800b653c, 0x800b6594, "scroll_bg_update" },
    { "MEMORY", 0x800b6594, 0x800b659c, "frontend_verb_stub" },
    { "MEMORY", 0x800b659c, 0x800b687c, "frontend_menu_input_loop" },
    { "MEMORY", 0x800b687c, 0x800b79c8, "menu_nav_cursor" },
    { "MEMORY", 0x800b79c8, 0x800b7a84, "frontend_state_init" },
    { "MEMORY", 0x800b7a84, 0x800b7ba4, "frontend_scroll_screen_a84" },
    { "MEMORY", 0x800b7ba4, 0x800b7da0, "menu_screen_dispatch" },
    { "MEMORY", 0x800b7da0, 0x800b878c, "frontend_scroll_sprite_screen" },
    { "MEMORY", 0x800b878c, 0x800b8988, "frontend_screen_music_once" },
    { "MEMORY", 0x800b8988, 0x800b8acc, "frontend_screen_music_once_8988" },
    { "MEMORY", 0x800b8acc, 0x800b8ad4, "frontend_menu_state_setup" },
    { "MEMORY", 0x800b8ad4, 0x800b96e4, "main_menu_state" },
    { "MEMORY", 0x800b96e4, 0x800b9724, "frontend_state_dispatch" },
    { "MEMORY", 0x800b9724, 0x800b97f8, "frontend_scroll_screen_driver" },
    { "MEMORY", 0x800b97f8, 0x800b9900, "frontend_char_dispatch" },
    { "MEMORY", 0x800b9900, 0x800b9a88, "font_rom_convert" },
    { "MEMORY", 0x800b9a88, 0x800b9c4c, "vram_image_load_dispatch" },
    { "MEMORY", 0x800b9c4c, 0x800b9e90, "card_event_setup" },
    { "MEMORY", 0x800b9e90, 0x800b9e98, "card_event_close_90" },
    { "MEMORY", 0x800b9e98, 0x800b9f84, "card_event_close" },
    { "MEMORY", 0x800b9f84, 0x800b9fa4, "card_event_close_wrapper" },
    { "MEMORY", 0x800b9fa4, 0x800b9fac, "card_event_test_a4" },
    { "MEMORY", 0x800b9fac, 0x800ba030, "card_event_poll" },
    { "MEMORY", 0x800ba030, 0x800ba038, "card_event_test_30" },
    { "MEMORY", 0x800ba038, 0x800ba0a4, "card_event_poll_038" },
    { "MEMORY", 0x800ba0a4, 0x800ba1f0, "memcard_io_leaf" },
    { "MEMORY", 0x800ba1f0, 0x800ba22c, "memcard_directory_load_for_slot" },
    { "MEMORY", 0x800ba22c, 0x800ba2d0, "card_event_poll_22c" },
    { "MEMORY", 0x800ba2d0, 0x800ba374, "card_event_poll_2d0" },
    { "MEMORY", 0x800ba374, 0x800ba4d4, "memcard_save_block_util" },
    { "MEMORY", 0x800ba4d4, 0x800ba668, "vram_image_load" },
    { "MEMORY", 0x800ba668, 0x800ba9d4, "memcard_load_scan" },
    { "MEMORY", 0x800ba9d4, 0x800baa08, "memcard_filename_format" },
    { "MEMORY", 0x800baa08, 0x800baad4, "save_string_glyph_encode" },
    { "MEMORY", 0x800bad08, 0x800baee8, "save_block_builder_SCmagic" },
    { "MEMORY", 0x800baee8, 0x800baf30, "memcard_probe" },
    { "MEMORY", 0x800baf30, 0x800bafcc, "memcard_save_write" },
    { "MEMORY", 0x800bafcc, 0x800bafd4, "memcard_slot_state_get" },
    { "MEMORY", 0x800bafd4, 0x800bb09c, "memcard_save_dispatch" },
    { "MEMORY", 0x800bb09c, 0x800bb19c, "memcard_file_read" },
    { "MEMORY", 0x800bb19c, 0x800bb298, "vram_image_store" },
    { "MEMORY", 0x800bb298, 0x800bb2d0, "memcard_file_erase" },
    { "MEMORY", 0x800bb2d0, 0x800bb448, "frontend_jr_subdispatch" },
    { "MEMORY", 0x800bb448, 0x800bb6f4, "memcard_slot_manage" },
    { "MEMORY", 0x800bb6f4, 0x800bc250, "memcard_load_dispatch" },
    { "MEMORY", 0x800bc250, 0x800bd518, "save_load_screen_main" },
    { "MEMORY", 0x800bd518, 0x800bd6a8, "save_load_screen_entry" },
    { "MEMORY", 0x800bd6c4, 0x800bd6c8, "bios_call_thunk_6c4" },
    { "MEMORY", 0x800bd6d8, 0x800bd710, "memcard_ack_card_change" },
    { "MEMORY", 0x800bd71c, 0x800bd720, "bios_call_thunk_b0" },
    { "MEMORY", 0x800bd730, 0x800bd788, "pad_init" },
    { "MEMORY", 0x800bd788, 0x800bd7c0, "pad_stop" },
    { "MEMORY", 0x800bd7c0, 0x800bd7e8, "overlay_load_finalize" },
    { "MEMORY", 0x800bd804, 0x800bd808, "bios_call_thunk_804" },
    { "MEMORY", 0x800bd818, 0x800bd880, "overlay_flush_cache" },
};

typedef struct { uint8_t *p; size_t n; } Blob;
static Blob slurp(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END); long z = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *b = malloc((size_t)z);
    if (!b || fread(b, 1, (size_t)z, f) != (size_t)z) { fprintf(stderr, "read %s\n", path); exit(2); }
    fclose(f);
    return (Blob){ b, (size_t)z };
}
static uint32_t le32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }

static int is_known_writer(const char *image, uint32_t pc)
{
    for (size_t i = 0; i < sizeof KNOWN_WRITERS / sizeof KNOWN_WRITERS[0]; i++)
        if (KNOWN_WRITERS[i].pc == pc && strcmp(KNOWN_WRITERS[i].image, image) == 0)
            return 1;
    return 0;
}
static int in_window(uint32_t a, uint32_t width)
{
    uint32_t end = a + width;
    return (a < REQ_HI && end > REQ_LO) || (a < TMR_HI && end > TMR_LO);
}

/* ------------------------------------------------------------------ scan --- */

/* Unresolved sites are buffered so they can be emitted as their own array after
 * the resolved hits, rather than interleaved with them. */
static char *ubuf; static size_t ulen, ucap;
static void uadd(const char *fmt, ...)
{
    va_list ap; va_start(ap, fmt);
    char line[512];
    int n = vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (ulen + (size_t)n + 1 > ucap) {
        ucap = ucap ? ucap * 2 : 65536;
        while (ulen + (size_t)n + 1 > ucap) ucap *= 2;
        ubuf = realloc(ubuf, ucap);
        if (!ubuf) exit(2);
    }
    memcpy(ubuf + ulen, line, (size_t)n); ulen += (size_t)n; ubuf[ulen] = 0;
}

/* Successors of instruction i within the extent, as indices. Returns how many
 * were written to out[]. A jr/return has none; an unconditional jump has one. */
static int succs_of(const uint8_t *img, size_t img_len, uint32_t img_base, size_t skip,
                    uint32_t start, size_t words, size_t i, size_t out[2])
{
    size_t off = skip + (start + i * 4 - img_base);
    if (off + 4 > img_len) return 0;
    uint32_t w = le32(img + off), op = w >> 26;
    int n = 0;
    if (op == 0 && (w & 0x3f) == 8) return 0;                 /* jr: leaves */
    if (op == 2) {                                            /* j */
        uint32_t t = (((start + (uint32_t)(i * 4) + 4) & 0xf0000000u) | ((w & 0x03ffffffu) << 2));
        if (t >= start && (t - start) / 4 < words) out[n++] = (t - start) / 4;
        return n;                                             /* no fallthrough */
    }
    if (op == 1 || (op >= 4 && op <= 7) || (op >= 0x14 && op <= 0x17)) {
        int32_t d = (int16_t)(w & 0xffff);
        uint32_t t = start + (uint32_t)(i * 4) + 4 + (uint32_t)(d * 4);
        if (t >= start && (t - start) / 4 < words) out[n++] = (t - start) / 4;
    }
    if (i + 1 < words) out[n++] = i + 1;
    return n;
}

/* Mark every index reachable from the extent entry WITHOUT executing `def`.
 * An index so reached is NOT dominated by def -- a path exists that bypasses
 * the definition and arrives with the register undefined. This is dominance
 * proper; `def_pc < first_join` was only a proxy and admitted exactly the
 * branch-bypass counterexample below. */
static void reach_avoiding(const uint8_t *img, size_t img_len, uint32_t img_base,
                           size_t skip, uint32_t start, size_t words, size_t def,
                           uint8_t *seen)
{
    memset(seen, 0, words);
    size_t *stack = malloc(words * sizeof *stack);
    if (!stack) exit(2);
    size_t sp = 0;
    if (def != 0 && words) { seen[0] = 1; stack[sp++] = 0; }
    while (sp) {
        size_t i = stack[--sp], out[2];
        int n = succs_of(img, img_len, img_base, skip, start, words, i, out);
        for (int k = 0; k < n; k++) {
            size_t t = out[k];
            if (t == def || seen[t]) continue;   /* def is a barrier */
            seen[t] = 1; stack[sp++] = t;
        }
    }
    free(stack);
}

typedef struct { int known; uint32_t v; uint32_t def_pc; } Reg;

/* Two quantities, deliberately not merged.
 *
 * The COMPLETENESS claim -- "no writer outside the enumerated set" -- must be
 * made over the whole corpus, because any smaller scope is a selection that can
 * be got wrong, and twice was. The BLOCKER count for item 2 must not be: an
 * unresolved store in a function that never touches the state is not a blocker
 * for this row, and counting it would inflate the residual as badly as the old
 * hand-picked set deflated it.
 *
 * So: scan everything, and emit unresolved sites only for extents that actually
 * reach a window. Which extents those are is discovered by the scan itself, not
 * declared. */
static int g_emit_unresolved;
static long g_extent_hits;

typedef struct {
    long resolved_hit, resolved_miss, bounded_struct, unknown, total;
    long new_writers, new_readers;
    long unknown_store, unknown_load;
} Counts;

static void scan_extent(const uint8_t *img, size_t img_len, uint32_t img_base,
                        size_t skip, const Extent *ex, Counts *c, int *first, int *ufirst)
{
    /* pass 1: branch targets inside the extent become join points */
    size_t words = (ex->end - ex->start) / 4;
    uint32_t first_join = 0xffffffffu;   /* lowest merge point in the extent */
    uint8_t *join = calloc(words ? words : 1, 1);
    if (!join) exit(2);
    for (size_t i = 0; i < words; i++) {
        size_t off = skip + (ex->start + i * 4 - img_base);
        if (off + 4 > img_len) break;
        uint32_t w = le32(img + off), op = w >> 26;
        uint32_t t = 0; int have = 0;
        if (op == 1 || (op >= 4 && op <= 7) || (op >= 0x14 && op <= 0x17)) {
            int32_t s = (int16_t)(w & 0xffff);
            t = ex->start + (uint32_t)(i * 4) + 4 + (uint32_t)(s * 4); have = 1;
        } else if (op == 2 || op == 3) {
            t = (((ex->start + (uint32_t)(i * 4) + 4) & 0xf0000000u) | ((w & 0x03ffffffu) << 2));
            have = 1;
        }
        if (have && t >= ex->start && t < ex->end) {
            join[(t - ex->start) / 4] = 1;
            if (t < first_join) first_join = t;
        }
    }

    /* pass 1b: how many times is each register written in this extent?
     * A register written EXACTLY ONCE holds the same value on every path that
     * reaches a use after that write, so a control-flow merge does not
     * invalidate it. Without this, a callee-saved base like `s1 = a0` -- set once
     * at the prologue of a 6 KB function -- dies at the first branch target and
     * every access through it is reported unknown. */
    int writes[32]; uint32_t write_pc[32];
    memset(writes, 0, sizeof writes); memset(write_pc, 0, sizeof write_pc);
    for (size_t i = 0; i < words; i++) {
        size_t off2 = skip + (ex->start + i * 4 - img_base);
        if (off2 + 4 > img_len) break;
        uint32_t w2 = le32(img + off2), op2 = w2 >> 26;
        uint32_t rt2 = (w2 >> 16) & 31, rd2 = (w2 >> 11) & 31;
        int reg = -1;
        if (op2 == 0) { uint32_t f = w2 & 0x3f; if (f != 8 && f != 0x0c) reg = (int)rd2; }
        else if (op2 == 0x0f || op2 == 0x08 || op2 == 0x09 || op2 == 0x0a ||
                 op2 == 0x0b || op2 == 0x0c || op2 == 0x0d || op2 == 0x0e ||
                 (op2 >= 0x20 && op2 <= 0x26)) reg = (int)rt2;
        else if (op2 == 0x03) reg = 31;
        /* A callee-save RESTORE (`lw rN, K(sp)` matching a prologue
         * `sw rN, K(sp)`) is not a definition: it puts back the caller's value on
         * the way out. Counting it makes every saved register look
         * multiply-defined, which is why `s1 = a0` in a 6 KB function never
         * survived a merge. */
        if (reg > 0 && op2 == 0x23 && ((w2 >> 21) & 31) == 29) {
            uint32_t k = w2 & 0xffff;
            for (size_t j = 0; j < i; j++) {
                size_t o3 = skip + (ex->start + j * 4 - img_base);
                if (o3 + 4 > img_len) break;
                uint32_t w3 = le32(img + o3);
                if ((w3 >> 26) == 0x2b && ((w3 >> 21) & 31) == 29 &&
                    ((w3 >> 16) & 31) == (uint32_t)reg && (w3 & 0xffff) == k) {
                    reg = -1; break;
                }
            }
        }
        if (reg > 0) { writes[reg]++; write_pc[reg] = ex->start + (uint32_t)(i * 4); }
    }

    /* per-register bypass sets, computed lazily */
    uint8_t dom_valid[32]; uint8_t *dom_bypass[32];
    memset(dom_valid, 0, sizeof dom_valid);
    for (int q = 0; q < 32; q++) { dom_bypass[q] = malloc(words ? words : 1); if (!dom_bypass[q]) exit(2); }
    uint8_t *dom_scratch = malloc(words ? words : 1);
    if (!dom_scratch) exit(2);

    Reg r[32];
    memset(r, 0, sizeof r);
    r[0].known = 1; r[0].v = 0;
    r[28].known = 1; r[28].v = GP_VALUE;
    for (size_t k = 0; k < sizeof ARG_SEEDS / sizeof ARG_SEEDS[0]; k++)
        if (ARG_SEEDS[k].fn_start == ex->start) {
            r[ARG_SEEDS[k].reg].known = 1;
            r[ARG_SEEDS[k].reg].v = ARG_SEEDS[k].value;
        }

    for (size_t i = 0; i < words; i++) {
        uint32_t pc = ex->start + (uint32_t)(i * 4);
        size_t off = skip + (pc - img_base);
        if (off + 4 > img_len) break;
        uint32_t w = le32(img + off);
        uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31, rd = (w >> 11) & 31;
        int32_t simm = (int16_t)(w & 0xffff);
        uint32_t uimm = w & 0xffff;

        if (join[i]) {
            /* A merge invalidates a constant that different paths could disagree
             * on. A register written exactly once, at a pc below this one, cannot
             * disagree -- every path that got here past that write carries the
             * same value -- so it survives. */
            /* DOMINANCE, not just singleton-ness. A sole definition only holds
             * on every path if it sits before the FIRST merge in the extent --
             * otherwise a path can branch around it and reach the use with the
             * register undefined. Argument seeds (def_pc 0) dominate by
             * construction: they hold on entry. */
            for (int q = 1; q < 32; q++) {
                if (q == 28 || !r[q].known) { if (q != 28) r[q].known = 0; continue; }
                if (writes[q] > 1) { r[q].known = 0; continue; }
                /* Seeded arguments (def_pc 0) hold on entry and dominate every
                 * instruction by construction. Otherwise require real dominance. */
                if (r[q].def_pc == 0) continue;
                size_t def_i = (r[q].def_pc - ex->start) / 4;
                if (!dom_valid[q]) {
                    reach_avoiding(img, img_len, img_base, skip, ex->start, words,
                                   def_i, dom_scratch);
                    memcpy(dom_bypass[q], dom_scratch, words);
                    dom_valid[q] = 1;
                }
                if (dom_bypass[q][i]) r[q].known = 0;   /* a path bypasses the def */
            }
        }

        int width = 0, is_mem = 0, is_store = 0;
        switch (op) {
        case 0x20: case 0x24: width = 1; is_mem = 1; break;              /* lb  lbu */
        case 0x21: case 0x25: width = 2; is_mem = 1; break;              /* lh  lhu */
        case 0x23:            width = 4; is_mem = 1; break;              /* lw      */
        case 0x28:            width = 1; is_mem = 1; is_store = 1; break;/* sb      */
        case 0x29:            width = 2; is_mem = 1; is_store = 1; break;/* sh      */
        case 0x2b:            width = 4; is_mem = 1; is_store = 1; break;/* sw      */
        default: break;
        }

        if (is_mem) {
            c->total++;
            if (r[rs].known) {
                uint32_t ea = r[rs].v + (uint32_t)simm;
                if (in_window(ea, (uint32_t)width)) {
                    c->resolved_hit++;
                    int known = is_known_writer(ex->image, pc);
                    /* A previously unlisted STORE would be a new writer -- a real
                     * modding hazard. A previously unlisted LOAD is a consumer:
                     * expected, but it is who OBSERVES a change to this state. */
                    if (!known) { if (is_store) c->new_writers++; else c->new_readers++; }
                    g_extent_hits++;
                    if (!g_emit_unresolved)
                    printf("%s   {\"disposition\":\"RESOLVED_HIT\",\"image\":\"%s\",\"function\":\"%s\","
                           "\"pc\":\"0x%08x\",\"ea\":\"0x%08x\",\"width\":%d,\"store\":%s,"
                           "\"already_enumerated\":%s}",
                           *first ? "" : ",\n", ex->image, ex->name, pc, ea, width,
                           is_store ? "true" : "false", known ? "true" : "false");
                    if (!g_emit_unresolved) *first = 0;
                } else {
                    c->resolved_miss++;
                }
            } else if (rs == 29 || rs == 30) {
                c->bounded_struct++;      /* stack frame: disjoint from the gp globals */
            } else {
                /* Base unknown. An unknown STORE is a POTENTIAL WRITER: it is
                 * exactly what "the writer set is complete" would have to
                 * exclude, and this pass cannot. Kept separate from unknown
                 * loads so the distinction can never be collapsed again. */
                c->unknown++;
                if (is_store) c->unknown_store++; else c->unknown_load++;
                if (g_emit_unresolved) uadd("%s   {\"image\":\"%s\",\"function\":\"%s\",\"pc\":\"0x%08x\","
                     "\"base_reg\":%u,\"disp\":%d,\"width\":%d,\"store\":%s}",
                     *ufirst ? "" : ",\n", ex->image, ex->name, pc, rs, simm, width,
                     is_store ? "true" : "false");
                *ufirst = 0;
            }
        }

        /* constant transfer */
        switch (op) {
        case 0x0f: if (rt) { r[rt].known = 1; r[rt].v = uimm << 16; r[rt].def_pc = pc; } break;
        case 0x09: case 0x0d:
            if (rt) {
                if (r[rs].known) {
                    r[rt].known = 1; r[rt].def_pc = pc;
                    r[rt].v = (op == 0x09) ? r[rs].v + (uint32_t)simm : (r[rs].v | uimm);
                } else r[rt].known = 0;
            }
            break;
        case 0x00:
            if ((w & 0x3f) == 0x21 || (w & 0x3f) == 0x20) {   /* addu / add */
                if (rd) {
                    if (r[rs].known && r[rt].known) {
                        r[rd].known = 1; r[rd].v = r[rs].v + r[rt].v; r[rd].def_pc = pc;
                    } else r[rd].known = 0;
                }
            } else if ((w & 0x3f) == 0x09) {                  /* jalr */
                for (int q = 1; q < 32; q++)
                    if (q <= 15 || q == 24 || q == 25 || q == 31) r[q].known = 0;
            } else if (rd && rd != 28) r[rd].known = 0;
            break;
        case 0x03:                                            /* jal */
            for (int q = 1; q < 32; q++)
                if (q <= 15 || q == 24 || q == 25 || q == 31) r[q].known = 0;
            break;
        default:
            if (op == 0x08 || op == 0x0a || op == 0x0b || op == 0x0c || op == 0x0e ||
                (op >= 0x20 && op <= 0x26))
                if (rt && rt != 28) r[rt].known = 0;
            break;
        }
        r[0].known = 1; r[0].v = 0;
        r[28].known = 1; r[28].v = GP_VALUE;
    }
    free(join);
    free(dom_scratch);
    for (int q = 0; q < 32; q++) free(dom_bypass[q]);
}

/* The exact branch-bypass counterexample: a path skips the sole definition of
 * s1 and reaches the load with it undefined. `def_pc < first_join` accepted this
 * and reported a false RESOLVED_HIT on 0x800823A0. */
static int self_test(void)
{
    static const uint32_t BYPASS[] = {
        0x14800002,   /* bne  a0, zero, +2  -> skips the lui                */
        0x00000000,   /* nop                                                */
        0x3C118008,   /* lui  s1, 0x8008    (sole static definition of s1)  */
        0x86230000 | 0x23a0,  /* lh v0, 0x23a0(s1)  <- must NOT resolve     */
    };
    static const uint32_t STRAIGHT[] = {
        0x3C118008,   /* lui  s1, 0x8008                                    */
        0x86230000 | 0x23a0,  /* lh v0, 0x23a0(s1)  <- must resolve         */
    };
    struct { const char *name; const uint32_t *w; size_t n; long want; } cases[] = {
        { "branch bypasses the sole definition", BYPASS,   4, 0 },
        { "straight-line definition dominates",  STRAIGHT, 2, 1 },
    };
    int bad = 0;
    for (size_t k = 0; k < 2; k++) {
        uint8_t *blob = malloc(cases[k].n * 4);
        if (!blob) exit(2);
        for (size_t j = 0; j < cases[k].n; j++)
            for (int b = 0; b < 4; b++) blob[j * 4 + b] = (uint8_t)(cases[k].w[j] >> (8 * b));
        Extent ex = { "SELFTEST", 0x80010000u, 0x80010000u + (uint32_t)(cases[k].n * 4), "t" };
        Counts c = {0}; int f = 1, uf = 1;
        FILE *devnull = freopen("/dev/null", "w", stdout);
        scan_extent(blob, cases[k].n * 4, 0x80010000u, 0, &ex, &c, &f, &uf);
        (void)devnull;
        freopen("/dev/tty", "w", stdout);
        if (c.resolved_hit != cases[k].want) {
            fprintf(stderr, "SELF-TEST FAIL: %s -> %ld hits, want %ld\n",
                    cases[k].name, c.resolved_hit, cases[k].want);
            bad = 1;
        } else {
            fprintf(stderr, "self-test ok: %-38s %ld hit\n", cases[k].name, c.resolved_hit);
        }
        free(blob);
    }
    return bad;
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) return self_test();
    if (argc != 2) { fprintf(stderr, "usage: %s <disc_files_root>|--self-test\n", argv[0]); return 2; }
    char path[4096];
    snprintf(path, sizeof path, "%s/SCUS_942.88", argv[1]);
    Blob exe = slurp(path);
    /* overlay id -> file, all mapped at 0x800B39A0 */
    /* GENERATED from the index's image table: id, path relative to the disc
     * root, and load base. The last hand-maintained table in this file; it used
     * to hold 13 of the 20 overlays and assume one shared base, which is why
     * BITS/MEMORY.BIN was unreachable. */
    static const struct { const char *id, *rel; uint32_t base; } OVL[] = {
        { "LEVEL01_LEVEL", "LEVEL01/LEVEL.BIN", 0x800b39a0u },
        { "LEVEL01_LEVEL1", "LEVEL01/LEVEL1.BIN", 0x800b39a0u },
        { "LEVEL02_LEVEL", "LEVEL02/LEVEL.BIN", 0x800b39a0u },
        { "LEVEL02_LEVEL1", "LEVEL02/LEVEL1.BIN", 0x800b39a0u },
        { "LEVEL03_LEVEL", "LEVEL03/LEVEL.BIN", 0x800b39a0u },
        { "LEVEL03_LEVEL1", "LEVEL03/LEVEL1.BIN", 0x800b39a0u },
        { "LEVEL04_LEVEL", "LEVEL04/LEVEL.BIN", 0x800b39a0u },
        { "LEVEL04_LEVEL1", "LEVEL04/LEVEL1.BIN", 0x800b39a0u },
        { "LEVEL05_LEVEL", "LEVEL05/LEVEL.BIN", 0x800b39a0u },
        { "LEVEL05_LEVEL1", "LEVEL05/LEVEL1.BIN", 0x800b39a0u },
        { "LEVEL06_LEVEL", "LEVEL06/LEVEL.BIN", 0x800b39a0u },
        { "LEVEL06_LEVEL1", "LEVEL06/LEVEL1.BIN", 0x800b39a0u },
        { "LEVEL07_LEVEL", "LEVEL07/LEVEL.BIN", 0x800b39a0u },
        { "LEVEL07_LEVEL1", "LEVEL07/LEVEL1.BIN", 0x800b39a0u },
        { "LEVEL08_LEVEL", "LEVEL08/LEVEL.BIN", 0x800b39a0u },
        { "LEVEL08_LEVEL1", "LEVEL08/LEVEL1.BIN", 0x800b39a0u },
        { "LEVEL09_LEVEL", "LEVEL09/LEVEL.BIN", 0x800b39a0u },
        { "LEVEL09_LEVEL1", "LEVEL09/LEVEL1.BIN", 0x800b39a0u },
        { "LEVEL10_LEVEL", "LEVEL10/LEVEL.BIN", 0x800b39a0u },
        { "MEMORY", "BITS/MEMORY.BIN", 0x800b5788u },
    };

    Counts c = {0};
    int first = 1, ufirst = 1;
    printf("{\n \"question\": \"Can anything other than the enumerated writers reach "
           "0x800823A0 or 0x80082470?\",\n");
    printf(" \"scope\": \"every "
           "code function in every analysed image: the index's range_type=='code' "
           "records, including the promoted target-root island 0x8004C898 (its 20 "
           "bytes and 2 register-based stores left the uncensused complement on "
           "2026-08-06). That IS a criterion -- it excludes 54 thunk records (one of "
           "which holds a resolved store, to 0x80080E68, outside both windows), 78 "
           "data records, and 35,192 gap bytes in no census record across ALL 21 "
           "loaded-image ranges -- 34,208 in SCUS_942_88, 424 in MEMORY, 560 across "
           "five level overlays -- (file-universe complement 37,316 bytes; the two "
           "differ by the nonresident header prefixes). A third-party sweep on 2026-08-06, over "
           "its then-current 47,420-byte uncensused complement, found 351 stores "
           "and 1,016 loads there and ZERO window-reaching accesses, so the "
           "exclusion is bounded rather than merely disclosed. Set, ends and image "
           "table are generated from the static index "
           "(tools/phase4_gen_resolver_extents.py); the census itself is the "
           "remaining trust root\",\n");
    printf(" \"resolved_hits\": [\n");
    size_t n_ext = sizeof EXTENTS / sizeof EXTENTS[0];
    uint8_t *touches = calloc(n_ext, 1);
    Counts corpus = {0};
    if (!touches) return 2;
    for (int pass = 0; pass < 2; pass++) {
    g_emit_unresolved = pass;
    /* Resolved hits are printed in the CORPUS pass only -- they are the same in
     * both by construction, and reprinting them would corrupt the array. */
    if (pass) { c = (Counts){0}; ufirst = 1; ulen = 0; if (ubuf) ubuf[0] = 0; }
    for (size_t i = 0; i < n_ext; i++) {
        if (pass && !touches[i]) continue;
        g_extent_hits = 0;
        const Extent *ex = &EXTENTS[i];
        /* One exit from the dispatch, so the hit-marking below cannot be
         * skipped. It previously sat after a `continue` in the resident branch,
         * which marked overlays only -- and a discovery pass that silently sees
         * half the corpus is the same bug this whole file keeps growing. */
        if (strcmp(ex->image, "SCUS") == 0) {
            scan_extent(exe.p, exe.n, 0x80010000u, 0x800, ex, &c, &first, &ufirst);
        } else {
            for (size_t k = 0; k < sizeof OVL / sizeof OVL[0]; k++) {
                if (strcmp(OVL[k].id, ex->image)) continue;
                snprintf(path, sizeof path, "%s/%s", argv[1], OVL[k].rel);
                Blob ov = slurp(path);
                scan_extent(ov.p, ov.n, OVL[k].base, 0, ex, &c, &first, &ufirst);
                free(ov.p);
                break;
            }
        }
        if (!pass && g_extent_hits) touches[i] = 1;
    }
    if (!pass) corpus = c;
    }
    long n_touch = 0;
    for (size_t i = 0; i < n_ext; i++) n_touch += touches[i];
    printf("\n ],\n \"unresolved_sites_scope\": \"window-touching extents only -- "
           "the corpus-wide residual is in the corpus block\",\n"
           " \"unresolved_sites\": [\n%s\n ],\n", ubuf ? ubuf : "");
    printf(" \"corpus\": {\"comment\": \"the completeness claim, over EVERY code "
           "function in EVERY analysed image -- no selection\",\n"
           "   \"extents\": %zu, \"memory_accesses_examined\": %ld, "
           "\"resolved_hit\": %ld,\n"
           "   \"resolved_writers_not_previously_enumerated\": %ld, "
           "\"readers_not_previously_enumerated\": %ld,\n"
           "   \"unresolved_store_sites\": %ld, \"unresolved_load_sites\": %ld},\n",
           n_ext, corpus.total, corpus.resolved_hit, corpus.new_writers, corpus.new_readers,
           corpus.unknown_store, corpus.unknown_load);
    printf(" \"window_touching\": {\"comment\": \"the item-2 blocker denominator: "
           "extents the corpus scan RESOLVED an access into a window. Discovered, "
           "not declared -- but discovered from RESOLVABLE accesses only, so a "
           "function whose sole window access goes through an unrecoverable base "
           "does not enter this denominator. Conservative for the safety claim "
           "(which is corpus-wide), deflating for the residual.\",\n"
           "   \"extents\": %ld, \"discovered_from\": \"resolved hits only\"},\n",
           n_touch);
    printf(" \"counts\": {\"memory_accesses_examined\": %ld, \"resolved_hit\": %ld,\n"
           "   \"resolved_miss\": %ld, \"bounded_stack_frame\": %ld, \"unknown\": %ld},\n",
           c.total, c.resolved_hit, c.resolved_miss, c.bounded_struct, c.unknown);
    printf(" \"resolved_writers_not_previously_enumerated\": %ld,\n", c.new_writers);
    printf(" \"UNRESOLVED_STORE_SITES\": %ld,\n", c.unknown_store);
    printf(" \"unresolved_load_sites\": %ld,\n", c.unknown_load);
    printf(" \"top_level_keys_scope\": \"window-touching extents. The corpus-wide "
           "equivalents are in the corpus block and are much larger; do not quote "
           "these two as a property of the image.\",\n");
    /* The conclusion is corpus-scoped, so the number in it must be too. It used
     * to quote the window-touching figure (238) beside the words "the writer set",
     * which is the corpus-wide claim -- a 22x understatement of what this pass
     * cannot exclude, and the same scope-mismatch this file keeps producing. */
    printf(" \"claim\": \"No additional writer among the RESOLVED accesses, over "
           "the WHOLE CORPUS (%ld accesses in %zu extents). But %ld unresolved "
           "store sites remain corpus-wide (%ld of them in the %ld extents that "
           "reach a window); this pass cannot exclude any of them, so the writer "
           "set is NOT shown to be complete.\",\n",
           corpus.total, n_ext, corpus.unknown_store, c.unknown_store, n_touch);
    printf(" \"readers_not_previously_enumerated\": %ld,\n", c.new_readers);
    printf(" \"residual\": \"UNKNOWN sites keep a base this pass could not recover "
           "(argument pointers, memory-loaded pointers, call results). They are NOT "
           "argued to be disjoint.\"\n}\n");
    /* The pass condition is about WRITERS: a new one means the enumerated set
     * was incomplete and any mod to this state is unsafe. New readers are a
     * finding to report, not a failure. */
    /* An unresolved STORE is an Item-2 blocker: it is precisely what a
     * completeness claim would have to exclude. Failing closed on it is what
     * stops "zero additional resolved writers" being read as "no unknown
     * writer" -- which is exactly the overclaim this review caught. */
    return c.new_writers != 0 || c.unknown_store != 0;
}
