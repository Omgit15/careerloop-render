"""3D hero shot (Locked Stack row 22): headless Blender, Cycles on the CPU. Only for hero pieces;
the job's render-time cap is the process timeout (engines.blender), and a shot over it falls back
to three/flat.html (2.5D in HyperFrames).

    blender -b --factory-startup -P hero.py -- job.json vertical shots/

Writes shots/f0001.png ... The title and line are fitted inside the size's safe zone in camera
space before anything renders; if they cannot fit, the script exits with an error."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
JOB = json.loads(Path(ARGS[0]).read_text("utf-8"))
TOKENS = json.loads((Path(__file__).resolve().parents[1] / "brand" / "tokens.json").read_text("utf-8"))
SIZE = TOKENS["sizes"][ARGS[1]]
(W, H), SAFE = SIZE["size"], SIZE["safe"]
C, D = TOKENS["colour"], JOB["data"]
FONT = Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf")


def rgb(hex_colour: str) -> tuple[float, float, float, float]:
    """sRGB hex to Blender's linear RGBA."""
    srgb = [int(hex_colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return lin[0], lin[1], lin[2], 1.0


def material(name: str, colour: str, roughness: float = 0.35) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF") or nodes.new("ShaderNodeBsdfPrincipled")
    out = nodes.get("Material Output") or nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = rgb(colour)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def setup(scene: bpy.types.Scene) -> None:
    r = scene.render
    r.engine, r.resolution_x, r.resolution_y, r.resolution_percentage = "CYCLES", W, H, 100
    r.fps, r.filepath = 24, str(Path(ARGS[2]) / "f####")
    r.image_settings.file_format = "PNG"
    scene.cycles.device, scene.cycles.samples, scene.cycles.use_denoising = "CPU", D["samples"], False
    scene.frame_start, scene.frame_end = 1, D["frames"]
    world = bpy.data.worlds.new("ground")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = rgb(C["ground"])
    scene.world = world


def add(obj: bpy.types.Object, scene: bpy.types.Scene) -> bpy.types.Object:
    scene.collection.objects.link(obj)
    return obj


def text(body: str, size: float, z: float, colour: str, scene: bpy.types.Scene) -> bpy.types.Object:
    curve = bpy.data.curves.new(body[:20], "FONT")
    curve.body, curve.size, curve.extrude, curve.align_x, curve.align_y = body, size, 0.05, "CENTER", "CENTER"
    if FONT.is_file():
        curve.font = bpy.data.fonts.load(str(FONT))
    obj = add(bpy.data.objects.new(body[:20], curve), scene)
    obj.rotation_euler, obj.location = (math.radians(90), 0, 0), (0, 0, z)
    obj.data.materials.append(material(f"ink-{z}", colour))
    return obj


def inside(scene: bpy.types.Scene, cam: bpy.types.Object, objs: list[bpy.types.Object]) -> bool:
    bpy.context.view_layer.update()
    lo_x, hi_x = SAFE["left"] / W, 1 - SAFE["right"] / W
    lo_y, hi_y = SAFE["bottom"] / H, 1 - SAFE["top"] / H
    for obj in objs:
        for corner in obj.bound_box:
            p = world_to_camera_view(scene, cam, obj.matrix_world @ Vector(corner))
            if not (lo_x <= p.x <= hi_x and lo_y <= p.y <= hi_y):
                return False
    return True


def words(scene: bpy.types.Scene, cam: bpy.types.Object) -> None:
    """Title (and line) at the top of the safe zone, shrunk until they fit; else refuse."""
    holder = add(bpy.data.objects.new("words", None), scene)
    objs = [text(D["title"], 0.8, 0.0, C["ink"], scene)]
    if D.get("line"):
        objs.append(text(D["line"], 0.36, -0.75, C["muted"], scene))
    for o in objs:
        o.parent = holder
    for scale in (1.0, 0.85, 0.72, 0.6, 0.5, 0.42, 0.35):
        for z in (3.0, 2.6, 2.2, 1.8, 1.4):
            holder.scale, holder.location = (scale,) * 3, (0, 0, z)
            if inside(scene, cam, objs):
                return
    raise SystemExit("hero text cannot fit inside the safe zone")


def build() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    setup(scene)
    cam = add(bpy.data.objects.new("camera", bpy.data.cameras.new("camera")), scene)
    cam.location, cam.rotation_euler = (0, -10, 0), (math.radians(90), 0, 0)
    scene.camera = cam
    light = add(bpy.data.objects.new("key", bpy.data.lights.new("key", "AREA")), scene)
    light.data.energy, light.data.size, light.location = 900, 4, (3, -6, 5)
    light.rotation_euler = (math.radians(50), 0, math.radians(25))
    bpy.ops.mesh.primitive_torus_add(major_radius=1.5, minor_radius=0.4, major_segments=96, minor_segments=32,
                                     location=(0, 0, -1.0))
    loop = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    loop.data.materials.append(material("accent", C["accent"]))
    for frame, angle in ((1, 0.0), (D["frames"], 1.5 * math.pi)):
        loop.rotation_euler = (math.radians(60), angle, 0)
        loop.keyframe_insert("rotation_euler", frame=frame)
    words(scene, cam)
    bpy.ops.render.render(animation=True)


build()
