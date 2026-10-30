/*
 * editor_visual_fidelity.c -- RCG-002 architecture anchor.
 *
 * This is documentation-grade RE C, not a build unit. It records the visual
 * fidelity decision used by the editor:
 *
 *   1. The 1:1 visual oracle is the real game running in an isolated
 *      DuckStation debugger instance.
 *   2. Offline OpenGL/Blender views are authoring previews and regression
 *      harnesses, not a promise to reproduce every retail draw path.
 *   3. Narrow remaining presentation gaps are tracked separately.
 *
 * Evidence / implementation anchors:
 * - level_editor/live_view.py: owns isolated DuckStation lifecycle, loadState,
 *   gpu.pickObject, VRAM framebuffer readback, and live RAM edit preview.
 * - level_editor/live_editor.py: Qt live editor using VRAM readback at ~30 fps.
 * - level_editor/render_capture.py: offline GL screenshot harness.
 * - level_editor/scene_importer.py + scene3d.py: bounded LEVEL01 offline preview
 *   with per-face texture page handling and proxy objects.
 * - ObsidianVault/Systems/Editor Visual Fidelity Baseline.md:
 *   generated static audit, reproduction command, and residual routing.
 */

typedef enum EditorVisualPath {
  EDITOR_VISUAL_PATH_REAL_GAME = 0,   /* isolated DuckStation framebuffer */
  EDITOR_VISUAL_PATH_OFFLINE_PREVIEW = 1,
  EDITOR_VISUAL_PATH_BLENDER_AUTHORING = 2,
} EditorVisualPath;

typedef struct EditorVisualCapability {
  EditorVisualPath path;
  const char* component;
  const char* role;
  int is_retail_oracle;
} EditorVisualCapability;

static const EditorVisualCapability k_editor_visual_capabilities[] = {
  {
    EDITOR_VISUAL_PATH_REAL_GAME,
    "level_editor/live_view.py",
    "isolated DuckStation renderer, gpu.pickObject, VRAM readback, live RAM preview",
    1,
  },
  {
    EDITOR_VISUAL_PATH_REAL_GAME,
    "level_editor/live_editor.py",
    "Qt live editor loop and carry/edit/build UI",
    1,
  },
  {
    EDITOR_VISUAL_PATH_OFFLINE_PREVIEW,
    "level_editor/render_capture.py",
    "headless OpenGL screenshot harness for preview regressions",
    0,
  },
  {
    EDITOR_VISUAL_PATH_OFFLINE_PREVIEW,
    "level_editor/scene3d.py",
    "bounded LEVEL01 mesh/texture/proxy renderer",
    0,
  },
  {
    EDITOR_VISUAL_PATH_BLENDER_AUTHORING,
    "tools/abl_blender/*",
    "authoring surface for editable level content; verified in DuckStation",
    0,
  },
};

typedef enum EditorVisualResidual {
  EDITOR_VISUAL_RESIDUAL_ACTOR_MODEL_POLISH = 5,/* RCG-005 closed as binding catalog */
  EDITOR_VISUAL_RESIDUAL_PICKUP_VISUALS = 8,    /* RCG-008 */
  EDITOR_VISUAL_RESIDUAL_CAMERA_MODES = 10,     /* RCG-010 */
  EDITOR_VISUAL_RESIDUAL_CLUT_MATERIALS = 13,   /* RCG-013 */
  EDITOR_VISUAL_RESIDUAL_TRANSPARENCY = 14,     /* RCG-014 */
  EDITOR_VISUAL_RESIDUAL_TEXTURE_INVENTORY = 23,/* RCG-023 */
  EDITOR_VISUAL_RESIDUAL_BACKDROP_MODEL = 30,   /* RCG-030 */
} EditorVisualResidual;

/*
 * RCG-002 is closed only at the architecture/foundation level. Do not read
 * this as "offline GL is retail-perfect"; read it as "the editor has a
 * retail-perfect verifier, and the remaining offline presentation work is
 * deliberately narrower." RCG-005's model-binding layer is closed by
 * actor_model_binding_catalog.c; any remaining actor visual polish is covered
 * by the narrower material/FX/behavior residuals above.
 */
static const int k_rcg002_architecture_closed = 1;
