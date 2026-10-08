"""Photoreal coupe + paper parasol for the Lulu hero, rendered with Cycles.

    blender.exe -b --factory-startup --python make_glass.py -- BACKDROP.png PLASTER.png OUT.png [samples] [px_per_unit]

Modelled in millimetres and converted to metres: Cycles' light units and
volume densities only behave at real-world scale. The camera is orthographic
at 18.5 degrees, the angle of the isometric block drawn in the page's SVG, and
is placed so that the glass's foot lands on the centre of the block's top face,
SVG (305, 575). The page behind the glass is put back in as a card that only
refraction can see, so what shows through the glass lines up with the real
page around it. The block is real geometry in burnt-orange plaster; its
texture is sampled in screen space from the same tile the CSS column below it
repeats, so the render and the column share one texture.
"""
import bpy, bmesh, math, sys
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BACKDROP, PLASTER, OUT = argv[0], argv[1], argv[2]
SAMPLES = int(argv[3]) if len(argv) > 3 else 512
PPU = float(argv[4]) if len(argv) > 4 else 2.6           # output px per SVG unit

MM = 0.001
X0, Y0, CW, CH = 80.0, 60.0, 450.0, 720.0                # SVG region rendered, down to the SVG's foot
TILE = 200.0                                             # SVG units per plaster tile (make_tile.py)
ORIGIN_SVG = (305.0, 575.0)                              # block top-face centre
M = 0.0955 / 260.0                                       # metres per SVG unit (rim = 260)
ELEV = math.radians(18.5)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


# ------------------------------------------------------------------ profiles
def catmull_rom(pts, per_span):
    """Centripetal Catmull-Rom through pts; also returns where each control
    point landed in the output."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out, idx = [], []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = [Vector(p) for p in P[i - 1:i + 3]]
        d1 = max((p1 - p0).length, 1e-6) ** 0.5
        d2 = max((p2 - p1).length, 1e-6) ** 0.5
        d3 = max((p3 - p2).length, 1e-6) ** 0.5
        m1 = ((p1 - p0) / d1 ** 2 - (p2 - p0) / (d1 + d2) ** 2 + (p2 - p1) / d2 ** 2) * d2
        m2 = ((p2 - p1) / d2 ** 2 - (p3 - p1) / (d2 + d3) ** 2 + (p3 - p2) / d3 ** 2) * d2
        a = 2 * (p1 - p2) + m1 + m2
        b = -3 * (p1 - p2) - 2 * m1 - m2
        idx.append(len(out))
        for k in range(per_span):
            t = k / per_span
            pt = a * t ** 3 + b * t ** 2 + m1 * t + p1
            out.append((pt.x, pt.y))
    idx.append(len(out))
    out.append(tuple(P[-2]))
    return out, idx


# (radius, height) mm. Proportions of a real cocktail coupe: height about 1.5x
# the rim, a 6 mm stem, a heavy base under the bowl and a thin rolled lip.
GLASS_CTRL = [
    (0, 1.5), (8, 1.25), (16, 0.85), (24, 0.4), (30, 0.08),
    (32.3, 0.18), (33.2, 0.9), (33.3, 1.7), (32.6, 2.6),
    (30, 3.15), (24, 3.7), (17, 4.7), (11, 6.7), (7.3, 10.2), (5.3, 15.5), (4.1, 22),
    (3.4, 31), (3.1, 43), (3.0, 56), (3.1, 66), (3.6, 73),
    (5.2, 78.8), (9.3, 83), (15.5, 87.6), (23.5, 94), (31.5, 102), (38.3, 111.5),
    (43.2, 121.5), (46.3, 131.5), (47.4, 138.6),
    (47.75, 140.3), (47.25, 141.5), (46.4, 142.0), (45.6, 141.5), (45.3, 140.3),
    (44.6, 134), (41.6, 125), (36.6, 115), (29.2, 105.2), (21.2, 97.2), (13.6, 91.6),
    (7, 88.8), (0, 88.0),
]
LIP_START = GLASS_CTRL.index((45.3, 140.3))
glass_samples, glass_idx = catmull_rom(GLASS_CTRL, 9)
inner = glass_samples[glass_idx[LIP_START]:]             # (r, z), rim -> bottom

LEVEL = 126.0
OVERLAP = 0.08   # the drink reaches slightly into the glass wall: no air film between them


def r_inner_at(z):
    for (r0, z0), (r1, z1) in zip(inner, inner[1:]):
        if (z0 - z) * (z1 - z) <= 0 and z0 != z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return inner[-1][0]


liquid = [(0.0, inner[-1][1] - OVERLAP)]
for r, z in reversed(inner):
    if 0.5 < r and z <= LEVEL - 1.2:
        liquid.append((r + OVERLAP, z))
re_ = r_inner_at(LEVEL + 0.55) + OVERLAP
liquid += [(re_, LEVEL + 0.55), (re_ - 0.45, LEVEL + 0.22), (re_ - 1.6, LEVEL + 0.05),
           (re_ - 4.0, LEVEL), (re_ * 0.5, LEVEL), (0.0, LEVEL)]


def lathe(name, samples, steps=224):
    bm = bmesh.new()
    verts = [bm.verts.new((r * MM, 0.0, z * MM)) for r, z in samples]
    edges = [bm.edges.new((a, b)) for a, b in zip(verts, verts[1:])]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=math.tau, steps=steps, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


# ----------------------------------------------------------------- materials
def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, nt, nt.nodes.new("ShaderNodeOutputMaterial")


def shadow_split(nt, surface_socket, out, tint):
    """Glass blocks shadow rays outright in Cycles, which gives a CG-black
    shadow. Real glass and drink let most of that light through, tinted."""
    lp = nt.nodes.new("ShaderNodeLightPath")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (*tint, 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs["Fac"])
    nt.links.new(surface_socket, mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def glass_material():
    m, nt, o = new_mat("glass")
    g = nt.nodes.new("ShaderNodeBsdfGlass")
    g.inputs["IOR"].default_value = 1.52
    g.inputs["Roughness"].default_value = 0.0
    shadow_split(nt, g.outputs[0], o, (0.50, 0.52, 0.50))
    v = nt.nodes.new("ShaderNodeVolumeAbsorption")      # the green of thick soda-lime glass
    v.inputs["Color"].default_value = (0.80, 0.96, 0.90, 1)
    v.inputs["Density"].default_value = 22.0
    nt.links.new(v.outputs[0], o.inputs["Volume"])
    return m


def liquid_material():
    m, nt, o = new_mat("cocktail")
    g = nt.nodes.new("ShaderNodeBsdfGlass")
    g.inputs["IOR"].default_value = 1.345
    g.inputs["Roughness"].default_value = 0.0
    shadow_split(nt, g.outputs[0], o, (0.50, 0.24, 0.06))
    ab = nt.nodes.new("ShaderNodeVolumeAbsorption")
    ab.inputs["Color"].default_value = (0.97, 0.68, 0.22, 1)
    ab.inputs["Density"].default_value = 78.0
    sc = nt.nodes.new("ShaderNodeVolumeScatter")         # a touch of haze from the shake
    sc.inputs["Color"].default_value = (1.0, 0.70, 0.38, 1)
    sc.inputs["Density"].default_value = 8.0
    try:
        sc.inputs["Anisotropy"].default_value = 0.45
    except KeyError:
        pass
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(ab.outputs[0], add.inputs[0])
    nt.links.new(sc.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], o.inputs["Volume"])
    return m


# The lights are strong enough to put real highlights in the glass, which is
# several times what a matte surface wants. Paper and wood get scaled down
# instead of a separate, weaker set of lights for them.
MATTE_GAIN = 0.16


def paper_material(name, rgb):
    rgb = tuple(c * MATTE_GAIN for c in rgb)
    m, nt, o = new_mat(name)
    d = nt.nodes.new("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (*rgb, 1)
    t = nt.nodes.new("ShaderNodeBsdfTranslucent")
    t.inputs["Color"].default_value = (rgb[0], rgb[1] * 0.8, rgb[2] * 0.55, 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.38
    nt.links.new(d.outputs[0], mix.inputs[1])
    nt.links.new(t.outputs[0], mix.inputs[2])
    noise = nt.nodes.new("ShaderNodeTexNoise")            # paper fibre
    noise.inputs["Scale"].default_value = 1400.0
    noise.inputs["Detail"].default_value = 8.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.00005
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], d.inputs["Normal"])
    nt.links.new(mix.outputs[0], o.inputs["Surface"])
    return m


def principled(name, rgb, rough):
    m, nt, o = new_mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    nt.links.new(b.outputs[0], o.inputs["Surface"])
    return m


def link(ob):
    scene.collection.objects.link(ob)
    return ob


def mesh_object(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


# --------------------------------------------------------------------- glass
glass = lathe("Glass", glass_samples)
glass.data.materials.append(glass_material())
drink = lathe("Cocktail", liquid)
drink.data.materials.append(liquid_material())

# ------------------------------------------- parasol on the front-left lip, top to camera
PHI, THETA = math.radians(-20), math.radians(25)
lip = Vector((-46.4 * math.cos(PHI), 46.4 * math.sin(PHI), 142.9))
d = Vector((-math.sin(THETA) * math.cos(PHI), math.sin(THETA) * math.sin(PHI), math.cos(THETA)))
BELOW, ABOVE, TOP = 41.0, 22.0, 10.0                    # stick length below the lip, to the apex, past it
bottom = lip - d * BELOW
apex = lip + d * ABOVE
rot = d.to_track_quat("Z", "Y").to_euler()

wood = principled("wood", tuple(c * MATTE_GAIN for c in (0.78, 0.60, 0.38)), 0.6)
stick_len = BELOW + ABOVE + TOP
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.9 * MM, radius2=0.8 * MM,
                      depth=stick_len * MM)
for v in bm.verts:
    v.co.z += stick_len * MM / 2
stick = mesh_object("Stick", bm)
stick.location = bottom * MM
stick.rotation_euler = rot
stick.data.materials.append(wood)
for p in stick.data.polygons:
    p.use_smooth = True

N_PANEL, N_ANG, N_RAD = 12, 12, 20
R, H, SAG = 21.0, 9.0, 0.9
bm = bmesh.new()
grid = []
for i in range(N_PANEL * N_ANG + 1):
    th = math.tau * i / (N_PANEL * N_ANG)
    f = (i / N_ANG) % 1.0
    edge_r = R * (1 - 0.07 * math.sin(math.pi * f))       # scallop between ribs
    row = []
    for j in range(N_RAD + 1):
        s = j / N_RAD
        z = -H * s - SAG * math.sin(math.pi * f) * s ** 1.5
        row.append(bm.verts.new((edge_r * s * math.cos(th) * MM, edge_r * s * math.sin(th) * MM, z * MM)))
    grid.append(row)
for i in range(N_PANEL * N_ANG):
    for j in range(N_RAD):
        fc = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
        fc.material_index = (i // N_ANG) % 2
        fc.smooth = True
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-8)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
canopy = mesh_object("Canopy", bm)
canopy.location = apex * MM
canopy.rotation_euler = rot
canopy.data.materials.append(paper_material("paper_yellow", (0.92, 0.58, 0.06)))
canopy.data.materials.append(paper_material("paper_white", (0.86, 0.84, 0.78)))
sol = canopy.modifiers.new("Thickness", "SOLIDIFY")
sol.thickness = 0.16 * MM
sol.offset = -1.0
slope = math.atan2(H, R)
for k in range(N_PANEL):
    th = math.tau * k / N_PANEL
    bm = bmesh.new()
    rib_len = R * 0.96 / math.cos(slope)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.30 * MM, radius2=0.24 * MM,
                          depth=rib_len * MM)
    for v in bm.verts:
        v.co.z += rib_len * MM / 2
    rib = mesh_object("Rib", bm)
    rib.parent = canopy
    rib.location = (0, 0, -0.45 * MM)
    rib.rotation_euler = Euler((0, math.pi / 2 + slope, th), "XYZ")
    rib.data.materials.append(wood)

# --------------------------------------------------------------------- block
# A square column turned 45 degrees: its top is the rhombus drawn in the SVG,
# (85..525, 505..645). Edges are rounded a little, as on any real plinth.
HALF = 220 * M
BOTTOM = -0.16
bm = bmesh.new()
top_v = [bm.verts.new((HALF * math.cos(a), HALF * math.sin(a), 0.0)) for a in (0, math.pi / 2, math.pi, 1.5 * math.pi)]
bot_v = [bm.verts.new((v.co.x, v.co.y, BOTTOM)) for v in top_v]
bm.faces.new(top_v)
bm.faces.new(list(reversed(bot_v)))
for i in range(4):
    j = (i + 1) % 4
    bm.faces.new((top_v[i], bot_v[i], bot_v[j], top_v[j]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
res = bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.0011, offset_type="OFFSET", segments=6,
                      profile=0.5, affect="EDGES", clamp_overlap=True)
for f_ in bm.faces:
    f_.smooth = False
for f_ in res["faces"]:
    f_.smooth = True
block = mesh_object("Block", bm)


def plaster_material():
    m, nt, o = new_mat("plaster")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = 0.72
    # tile sampled in SVG coordinates through the camera, like the CSS column
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Window"], sep.inputs[0])
    ux = nt.nodes.new("ShaderNodeMath"); ux.operation = "MULTIPLY_ADD"
    ux.inputs[1].default_value = CW / TILE
    ux.inputs[2].default_value = X0 / TILE
    nt.links.new(sep.outputs["X"], ux.inputs[0])
    uy = nt.nodes.new("ShaderNodeMath"); uy.operation = "MULTIPLY_ADD"
    uy.inputs[1].default_value = CH / TILE
    uy.inputs[2].default_value = -(Y0 + CH) / TILE
    nt.links.new(sep.outputs["Y"], uy.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(ux.outputs[0], comb.inputs["X"])
    nt.links.new(uy.outputs[0], comb.inputs["Y"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(PLASTER)
    tex.extension = "REPEAT"
    tex.interpolation = "Cubic"
    nt.links.new(comb.outputs[0], tex.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    mul.inputs["A"].default_value = (*BLOCK_RGB, 1)
    nt.links.new(tex.outputs["Color"], mul.inputs["B"])
    # Darkening down the faces. A lamp would have to almost touch the block to
    # fall off this fast; folding it into the colour gives the same look on a
    # matte surface and lands the faces on the column's colours at the join.
    oc = nt.nodes.new("ShaderNodeTexCoord")
    oz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(oc.outputs["Object"], oz.inputs[0])
    fall = nt.nodes.new("ShaderNodeMapRange")
    fall.interpolation_type = "SMOOTHSTEP"
    fall.inputs["From Min"].default_value = FALL_Z[0]
    fall.inputs["From Max"].default_value = FALL_Z[1]
    fall.inputs["To Min"].default_value = FALL_K
    fall.inputs["To Max"].default_value = 1.0
    nt.links.new(oz.outputs["Z"], fall.inputs["Value"])
    shade = nt.nodes.new("ShaderNodeMix")
    shade.data_type = "RGBA"
    shade.blend_type = "MULTIPLY"
    shade.inputs["Factor"].default_value = 1.0
    nt.links.new(mul.outputs["Result"], shade.inputs["A"])
    nt.links.new(fall.outputs["Result"], shade.inputs["B"])
    # Contact shadow: occlusion from anything within a centimetre or so. The
    # block is convex, so the only thing that close is the glass's foot,
    # which darkens the plaster under and right around it, the way a glass
    # standing on a surface does. Without it the glass looks like it floats.
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 24
    ao.inputs["Distance"].default_value = CONTACT_DIST
    ao_mix = nt.nodes.new("ShaderNodeMix")
    ao_mix.data_type = "FLOAT"
    ao_mix.inputs["Factor"].default_value = CONTACT_STRENGTH
    ao_mix.inputs["A"].default_value = 1.0
    nt.links.new(ao.outputs["AO"], ao_mix.inputs["B"])
    contact = nt.nodes.new("ShaderNodeMix")
    contact.data_type = "RGBA"
    contact.blend_type = "MULTIPLY"
    contact.inputs["Factor"].default_value = 1.0
    nt.links.new(shade.outputs["Result"], contact.inputs["A"])
    nt.links.new(ao_mix.outputs["Result"], contact.inputs["B"])
    nt.links.new(contact.outputs["Result"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.0002
    nt.links.new(tex.outputs["Color"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], b.inputs["Normal"])
    nt.links.new(b.outputs[0], o.inputs["Surface"])
    return m


BLOCK_RGB = (0.56, 0.175, 0.018)
BLOCK_TOP_W, BLOCK_LEFT_W, BLOCK_RIGHT_W = 2.1, 0.26, 0.055
FALL_Z, FALL_K = (-0.075, -0.008), 0.26          # object z range (m) and how dark it gets
CONTACT_DIST, CONTACT_STRENGTH = 0.018, 0.85     # contact-shadow reach (m) and depth
block.data.materials.append(plaster_material())

# ------------------------------------------------- camera (ortho, the block's angle)
PPM = PPU / M                                           # output px per metre
W_PX, H_PX = int(round(CW * PPU)), int(round(CH * PPU))
F = Vector((0, math.cos(ELEV), -math.sin(ELEV)))        # view direction
U = Vector((0, math.sin(ELEV), math.cos(ELEV)))         # screen up
Rv = Vector((1, 0, 0))
px, py = (ORIGIN_SVG[0] - X0) * PPU, (ORIGIN_SVG[1] - Y0) * PPU
target = -Rv * ((px - W_PX / 2) / PPM) + U * ((py - H_PX / 2) / PPM)
cx_svg, cy_svg = X0 + CW / 2, Y0 + CH / 2


def svg_to_world(sx, sy, depth):
    return target + Rv * ((sx - cx_svg) * M) + U * ((cy_svg - sy) * M) + F * depth


cam_data = bpy.data.cameras.new("Cam")
cam_data.type = "ORTHO"
cam_data.sensor_fit = "AUTO"
cam_data.ortho_scale = max(CW, CH) * M
cam_data.clip_start = 0.001
cam_data.clip_end = 5.0
cam = link(bpy.data.objects.new("Cam", cam_data))
cam.location = target - F * 1.0
cam.rotation_euler = Euler((math.pi / 2 - ELEV, 0, 0), "XYZ")
scene.camera = cam

# --------------------------------- the page behind, seen only through the glass
bm = bmesh.new()
corners = [(0, 780), (620, 780), (620, 0), (0, 0)]
vs = [bm.verts.new(svg_to_world(sx, sy, 0.30)) for sx, sy in corners]
face = bm.faces.new(vs)
uv = bm.loops.layers.uv.new("UVMap")
for loop, (u_, v_) in zip(face.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    loop[uv].uv = (u_, v_)
card = mesh_object("PageCard", bm)
card.visible_camera = False
card.visible_diffuse = False
card.visible_shadow = False
card.visible_volume_scatter = False
m, nt, o = new_mat("page")
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(BACKDROP)
tex.extension = "EXTEND"
em = nt.nodes.new("ShaderNodeEmission")
em.inputs["Strength"].default_value = 1.0
nt.links.new(tex.outputs["Color"], em.inputs["Color"])
nt.links.new(em.outputs[0], o.inputs["Surface"])
card.data.materials.append(m)

# ------------------------------------------------------------------- world
world = bpy.data.worlds.new("World")
try:
    world.use_nodes = True
except Exception:
    pass
wnt = world.node_tree
for n in list(wnt.nodes):
    wnt.nodes.remove(n)
bg = wnt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.0032, 0.0070, 0.0080, 1)   # --ink
wo = wnt.nodes.new("ShaderNodeOutputWorld")
wnt.links.new(bg.outputs[0], wo.inputs["Surface"])
scene.world = world


# ------------------------------------------------------------------- lights
def area(name, loc, aim, size, power, color, shape="RECTANGLE"):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = shape
    ld.size, ld.size_y = size
    ld.energy = power
    ld.color = color
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    ob.rotation_euler = (Vector(aim) - Vector(loc)).normalized().to_track_quat("-Z", "Y").to_euler()
    ob.visible_camera = False
    return ob


def receivers(light, objects, state):
    """Light linking: state EXCLUDE keeps this light off the objects,
    INCLUDE makes them the only things it lights."""
    coll = bpy.data.collections.new(light.name + "_rx")
    for ob_ in objects:
        coll.objects.link(ob_)
    for co in coll.collection_objects:
        co.light_linking.link_state = state
    light.light_linking.receiver_collection = coll


C = (0, 0, 0.075)
glass_lights = [
    area("StripLeft", (-0.30, -0.16, 0.10), C, (0.05, 0.40), 11, (0.86, 0.94, 1.0)),   # long cool highlight
    area("StripRight", (0.30, -0.10, 0.10), C, (0.04, 0.40), 7, (1.0, 0.72, 0.42)),   # warm counter-edge
    area("Pendant", (-0.17, -0.06, 0.38), C, (0.09, 0.09), 7, (1.0, 0.78, 0.50), "DISK"),  # bar lamp overhead
    area("Front", (0.0, -0.55, 0.16), C, (0.30, 0.18), 0.6, (0.85, 0.92, 1.0), "ELLIPSE"),
]
# The glass needs lights strong and close enough to put real highlights in
# it; on a matte block those same lights flatten every face. The block gets
# its own: a soft lamp above and in front-left, so the top is brightest and
# the faces fall away into the dark the way a plinth does under a bar light.
for L_ in glass_lights:
    receivers(L_, [block], "EXCLUDE")
E = HALF / 2                                            # top-edge midpoints of the two faces
block_lights = [
    # lamp above and behind to the left: lights the top and lays the glass's
    # shadow forward-right across it, where the camera can see it
    area("BlockTop", (-0.085, 0.05, 0.34), (0, 0, 0), (0.07, 0.07), BLOCK_TOP_W, (1.0, 0.74, 0.46), "DISK"),
    # thin strips just off each face's top edge: light that close falls off
    # fast down the face, the way the drawn block darkened into the column
    area("BlockLeft", (-E - 0.050, -E - 0.050, 0.03), (-E, -E, -0.05), (0.24, 0.012), BLOCK_LEFT_W, (1.0, 0.72, 0.44)),
    area("BlockRight", (E + 0.050, -E - 0.050, 0.03), (E, -E, -0.05), (0.24, 0.012), BLOCK_RIGHT_W, (1.0, 0.66, 0.40)),
]
for L_ in block_lights:
    receivers(L_, [block], "INCLUDE")

# Edison bulbs of the bar: never in frame, only in reflections and the drink
for (x, y, z, rad, k) in [(-0.32, 0.62, 0.18, 0.011, 30), (0.08, 0.72, 0.25, 0.014, 34),
                          (0.36, 0.48, 0.12, 0.010, 26), (-0.14, 0.82, 0.08, 0.012, 28),
                          (0.26, 0.86, 0.22, 0.011, 30), (-0.30, -0.40, 0.30, 0.012, 22),
                          (0.22, -0.45, 0.34, 0.012, 22)]:
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=rad)
    ob = mesh_object("Bulb", bm)
    ob.location = (x, y, z)
    bm_, bnt, bo = new_mat("bulb")
    e = bnt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (1.0, 0.58, 0.22, 1)
    e.inputs["Strength"].default_value = k
    bnt.links.new(e.outputs[0], bo.inputs["Surface"])
    ob.data.materials.append(bm_)
    ob.visible_camera = False
    ob.visible_shadow = False
    ob.visible_diffuse = False

# ------------------------------------------------------------------- render
r = scene.render
r.engine = "CYCLES"
r.resolution_x, r.resolution_y, r.resolution_percentage = W_PX, H_PX, 100
r.film_transparent = True
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGBA"
r.image_settings.color_depth = "16"
r.filepath = OUT
c = scene.cycles
c.samples = SAMPLES
c.use_adaptive_sampling = True
c.adaptive_threshold = 0.003
c.use_denoising = True
c.max_bounces = 48
c.transmission_bounces = 40
c.glossy_bounces = 24
c.diffuse_bounces = 3
c.volume_bounces = 4
c.transparent_max_bounces = 48
c.caustics_reflective = False
c.caustics_refractive = False
c.sample_clamp_indirect = 6.0
try:
    c.film_transparent_glass = False
except Exception:
    pass
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    try:
        prefs.refresh_devices()
    except Exception:
        prefs.get_devices()
    on = 0
    for dev in prefs.devices:
        dev.use = dev.type == "OPTIX"
        on += dev.use
    c.device = "GPU" if on else "CPU"
    print("[glass] device", c.device, [dv.name for dv in prefs.devices if dv.use])
except Exception as ex:
    print("[glass] GPU setup failed, CPU:", ex)
scene.view_settings.view_transform = "Standard"   # the page card must come out as it went in
scene.view_settings.look = "None"

print("[glass] canvas", W_PX, "x", H_PX, "svg box", X0, Y0, CW, CH)
bpy.ops.render.render(write_still=True)
print("[glass] wrote", OUT)
