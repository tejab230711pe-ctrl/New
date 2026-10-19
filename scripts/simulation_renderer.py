#!/usr/bin/env python3
"""
AFSD Simulation Renderer Library
================================
Provides high-performance, publication-grade 3D rendering for Additive Friction
Stir Deposition (AFSD) simulations, based on the engineering-accurate schematic
formulation in `process_schematic.py`.

Key Features:
- Batched Poly3DCollection rendering (100x faster than single-polygon additions)
- Directional key lighting, fill light, Blinn-Phong specular highlights
- Solid base plate with fine FE mesh, ambient occlusion, and machined edge bevels
- 360° soft curled flash annulus collar with continuous C1 curvature and thermal color gradation
- Consumable tool rod with dynamic spindle rotation and chamfered top cap
- Progressive friction surfacing deposit layer with 3D semicircular frictional shear ripples,
  advancing/retreating side flash ridges, crowned profile, and trailing starter face
- Localized thermal heat-affected zone (HAZ) glowing dynamically under the tool shoulder
- Precision dimension lines (Width: 120 mm, Length: 300 mm, Thickness: 20 mm)
- Real-time HUD telemetry badges and process stage status banners
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# ═══════════════════════════════════════════════════════════════════════════ #
#                            LIGHTING MODEL                                   #
# ═══════════════════════════════════════════════════════════════════════════ #

LIGHT_DIR = np.array([-0.38, -0.52, 0.76])
LIGHT_DIR = LIGHT_DIR / np.linalg.norm(LIGHT_DIR)

FILL_LIGHT = np.array([0.5, 0.3, 0.8])
FILL_LIGHT = FILL_LIGHT / np.linalg.norm(FILL_LIGHT)

VIEW_DIR = np.array([np.cos(np.radians(-48)), np.sin(np.radians(-48)), 0.45])
VIEW_DIR = VIEW_DIR / np.linalg.norm(VIEW_DIR)

HALF_VEC = (LIGHT_DIR + VIEW_DIR)
HALF_VEC = HALF_VEC / np.linalg.norm(HALF_VEC)


class BatchRenderer:
    """High-performance batched 3D polygon renderer."""
    def __init__(self):
        self.batches = {}

    def add_poly(self, verts, fc, ec="none", lw=0.08, zo=2):
        if zo not in self.batches:
            self.batches[zo] = {'verts': [], 'fc': [], 'ec': [], 'lw': []}
        self.batches[zo]['verts'].append(verts)
        self.batches[zo]['fc'].append(fc)
        self.batches[zo]['ec'].append(ec)
        self.batches[zo]['lw'].append(lw)

    def commit(self, ax):
        for zo in sorted(self.batches.keys()):
            b = self.batches[zo]
            if not b['verts']:
                continue
            poly = Poly3DCollection(b['verts'],
                                    facecolors=b['fc'],
                                    edgecolors=b['ec'],
                                    linewidths=b['lw'],
                                    zorder=zo)
            ax.add_collection3d(poly)


# ── 1. SOFT CONTACT SHADOW ───────────────────────────────────────────────── #

def draw_contact_shadow(renderer, x0, y0, dx, dy, z_plane=-2.0, is_dark_bg=False):
    """Renders a soft, realistic ground contact shadow under the plate."""
    xs = np.linspace(x0 - 4, x0 + dx + 10, 16)
    ys = np.linspace(y0 - 6, y0 + dy + 10, 24)
    shadow_base = np.array([0.02, 0.04, 0.08]) if is_dark_bg else np.array([0.72, 0.75, 0.80])
    
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = x0 + dx / 2, y0 + dy / 2
            d = np.sqrt(((xs[i] - cx) / (dx * 0.58))**2 + ((ys[j] - cy) / (dy * 0.58))**2)
            alpha_s = np.clip(0.35 * (1.0 - d**1.4), 0.0, 0.35)
            if alpha_s > 0.015:
                if is_dark_bg:
                    col = shadow_base * alpha_s + np.array([0.04, 0.06, 0.10]) * (1.0 - alpha_s)
                else:
                    col = shadow_base * (1.0 - alpha_s) + np.array([1.0, 1.0, 1.0]) * (1.0 - alpha_s * 0.8)
                col = np.clip(col, 0.0, 1.0)
                verts = [
                    [xs[i],     ys[j],     z_plane],
                    [xs[i + 1], ys[j],     z_plane],
                    [xs[i + 1], ys[j + 1], z_plane],
                    [xs[i],     ys[j + 1], z_plane],
                ]
                renderer.add_poly(verts, col, col, lw=0.0, zo=0)


# ── 2. SOLID BASE PLATE (STEEL ALLOY WITH FINE FE MESH) ──────────────────── #

def draw_solid_plate(renderer, ax, x0, y0, z0, dx, dy, dz,
                     nx=36, ny=54, nz=5, rcx=0, rcy=50, rod_r=12.5,
                     heat_temp=293.15, is_contact=True):
    """
    Renders high-realism metallic base plate:
    - Per-quad Blinn-Phong specular sheen and directional lighting gradient
    - Ambient occlusion near base plate bottom and around tool contact zone
    - Machined chamfer edge highlights on visible top boundaries
    - Crisp fine FE mesh lines (#0E1F2E)
    - Dynamic localized thermal glow around the active stir zone
    """
    x1, y1, z1 = x0 + dx, y0 + dy, z0 + dz
    
    base_plate_rgb = np.array([168, 192, 216]) / 255.0
    warm_plate_rgb = np.array([184, 204, 224]) / 255.0
    cool_plate_rgb = np.array([142, 168, 194]) / 255.0
    mesh_ec = "#0E1F2E"
    
    n_top = np.array([0, 0, 1.0])
    dot_top_key = max(0.0, float(np.dot(n_top, LIGHT_DIR)))
    dot_top_spec = max(0.0, float(np.dot(n_top, HALF_VEC))) ** 24
    
    xs = np.linspace(x0, x1, nx + 1)
    ys = np.linspace(y0, y1, ny + 1)
    
    glow_hot = np.array([235, 110, 30]) / 255.0   # 650-700K stir zone glow
    glow_warm = np.array([210, 150, 70]) / 255.0  # 450-550K HAZ
    
    # (A) Top Face
    for i in range(nx):
        for j in range(ny):
            xm = 0.5 * (xs[i] + xs[i + 1])
            ym = 0.5 * (ys[j] + ys[j + 1])
            
            d_tool = np.sqrt((xm - rcx)**2 + (ym - rcy)**2)
            ao_tool = 0.85 + 0.15 * np.clip((d_tool - rod_r) / 16.0, 0.0, 1.0)
            
            grad_x = 0.94 + 0.12 * ((x1 - xm) / dx)
            grad_y = 0.94 + 0.12 * ((y1 - ym) / dy)
            surf_grad = grad_x * grad_y
            
            intensity = (0.38 + 0.48 * dot_top_key + 0.14 * dot_top_spec) * ao_tool * surf_grad
            intensity = np.clip(intensity, 0.0, 1.0)
            
            blend = np.clip(dot_top_key * surf_grad, 0.0, 1.0)
            base_col = cool_plate_rgb * (1.0 - blend) + warm_plate_rgb * blend
            fc_top = np.clip(base_col * intensity + 0.08 * dot_top_spec, 0.0, 1.0)
            
            if is_contact and heat_temp > 350.0 and d_tool < 36.0:
                heat_frac = np.clip((heat_temp - 300.0) / 420.0, 0.0, 1.0)
                falloff = np.exp(-0.5 * (d_tool / 12.0)**2) * heat_frac
                t_col = glow_hot if d_tool < 16.0 else glow_warm
                fc_top = fc_top * (1.0 - falloff * 0.75) + t_col * (falloff * 0.75)
                fc_top = np.clip(fc_top, 0.0, 1.0)
            
            verts = [
                [xs[i],     ys[j],     z1],
                [xs[i + 1], ys[j],     z1],
                [xs[i + 1], ys[j + 1], z1],
                [xs[i],     ys[j + 1], z1],
            ]
            renderer.add_poly(verts, fc_top, mesh_ec, lw=0.07, zo=2)
            
    # (B) Front Face (Y = y0)
    n_front = np.array([0, -1.0, 0])
    dot_front_key = max(0.0, float(np.dot(n_front, LIGHT_DIR)))
    dot_front_spec = max(0.0, float(np.dot(n_front, HALF_VEC))) ** 18
    zs = np.linspace(z0, z1, nz + 1)
    
    for i in range(nx):
        xm = 0.5 * (xs[i] + xs[i + 1])
        grad_x = 0.92 + 0.16 * ((x1 - xm) / dx)
        for k in range(nz):
            zm = 0.5 * (zs[k] + zs[k + 1])
            ao_z = 0.76 + 0.24 * ((zm - z0) / dz)
            intensity = (0.32 + 0.52 * dot_front_key + 0.16 * dot_front_spec) * ao_z * grad_x
            intensity = np.clip(intensity, 0.0, 1.0)
            fc_front = np.clip(cool_plate_rgb * intensity + 0.06 * dot_front_spec, 0.0, 1.0)
            verts = [
                [xs[i],     y0, zs[k]],
                [xs[i + 1], y0, zs[k]],
                [xs[i + 1], y0, zs[k + 1]],
                [xs[i],     y0, zs[k + 1]],
            ]
            renderer.add_poly(verts, fc_front, mesh_ec, lw=0.07, zo=2)
            
    # (C) Right Face (X = x1)
    n_right = np.array([1.0, 0, 0])
    dot_right_key = max(0.0, float(np.dot(n_right, LIGHT_DIR)))
    dot_right_spec = max(0.0, float(np.dot(n_right, HALF_VEC))) ** 18
    
    for j in range(ny):
        ym = 0.5 * (ys[j] + ys[j + 1])
        grad_y = 0.88 + 0.24 * ((ym - y0) / dy)
        for k in range(nz):
            zm = 0.5 * (zs[k] + zs[k + 1])
            ao_z = 0.74 + 0.26 * ((zm - z0) / dz)
            intensity = (0.28 + 0.56 * dot_right_key + 0.16 * dot_right_spec) * ao_z * grad_y
            intensity = np.clip(intensity, 0.0, 1.0)
            fc_right = np.clip(cool_plate_rgb * intensity + 0.05 * dot_right_spec, 0.0, 1.0)
            verts = [
                [x1, ys[j],     zs[k]],
                [x1, ys[j + 1], zs[k]],
                [x1, ys[j + 1], zs[k + 1]],
                [x1, ys[j],     zs[k + 1]],
            ]
            renderer.add_poly(verts, fc_right, mesh_ec, lw=0.07, zo=2)

    # (D) Machined Perimeter Edge Highlights
    edge_highlight_col = "#EAF2F9"
    ax.plot([x0, x1], [y0, y0], [z1, z1], color=edge_highlight_col, lw=0.9, alpha=0.95, zorder=3)
    ax.plot([x1, x1], [y0, y1], [z1, z1], color=edge_highlight_col, lw=0.9, alpha=0.95, zorder=3)
    ax.plot([x1, x1], [y0, y0], [z0, z1], color=edge_highlight_col, lw=0.8, alpha=0.90, zorder=3)


# ── 3. CURLED FLASH ANNULUS COLLAR (NO SHARP CORNERS) ────────────────────── #

def draw_refined_annulus_collar_layer(renderer, cx, cy, z_base, rod_r,
                                      collar_scale=1.0, pass_type="all",
                                      nth=80, ns=28):
    """
    Renders soft, organically curled flash annulus collar with zero sharp corners:
    - Continuous C1-smooth rounded toroidal profile
    - Thermal metallic gradation: warm shear root -> silvery alloy body -> brilliant crest
    - Dual-pass depth stratification for accurate front/back occlusion
    """
    if collar_scale < 0.05:
        return
        
    base_col  = np.array([168, 192, 214]) / 255.0
    warm_col  = np.array([215, 202, 168]) / 255.0
    rim_col   = np.array([238, 246, 254]) / 255.0
    cool_col  = np.array([125, 152, 178]) / 255.0
    
    delta_r  = 6.6 * collar_scale
    h_crest  = 5.4 * collar_scale
    r_crest  = 1.35 * collar_scale
    
    theta = np.linspace(0, 2 * np.pi, nth + 1)
    s_vals = np.linspace(0, 1.0, ns + 1)
    
    cam_az = np.radians(-48)
    cam_dir_xy = np.array([np.cos(cam_az), np.sin(cam_az)])
    cam_vec = np.array([np.cos(cam_az) * np.cos(np.radians(29)),
                        np.sin(cam_az) * np.cos(np.radians(29)),
                        np.sin(np.radians(29))])
    cam_vec = cam_vec / np.linalg.norm(cam_vec)
    
    zo = 5 if pass_type == "back" else 7

    def smooth_profile(s):
        r_outer_max = rod_r + delta_r
        z_outer_tan = z_base + (h_crest - r_crest)
        if s <= 0.46:
            xi = s / 0.46
            sin_xi = np.sin(xi * np.pi * 0.5)
            cos_xi = np.cos(xi * np.pi * 0.5)
            r = rod_r + delta_r * (sin_xi ** 1.15)
            z = z_base + (h_crest - r_crest) * (sin_xi ** 1.45)
            dr_ds = (delta_r * 1.15 * (sin_xi ** 0.15) * cos_xi * (np.pi * 0.5)) / 0.46
            dz_ds = ((h_crest - r_crest) * 1.45 * (sin_xi ** 0.45) * cos_xi * (np.pi * 0.5)) / 0.46
        elif s <= 0.74:
            phi = (s - 0.46) / 0.28 * np.pi
            r_center = r_outer_max - r_crest
            z_center = z_outer_tan
            r = r_center + r_crest * np.cos(phi)
            z = z_center + r_crest * np.sin(phi)
            dr_ds = (-r_crest * np.sin(phi) * np.pi) / 0.28
            dz_ds = (r_crest * np.cos(phi) * np.pi) / 0.28
        else:
            psi = (s - 0.74) / 0.26
            r_in_tan = r_outer_max - 2 * r_crest
            r_in_end = rod_r + 0.15
            z_in_end = z_base + 0.8 * collar_scale
            cos_psi = 0.5 * (1.0 - np.cos(psi * np.pi))
            sin_psi = 0.5 * np.sin(psi * np.pi) * np.pi
            r = r_in_tan * (1.0 - cos_psi) + r_in_end * cos_psi
            z = z_outer_tan * (1.0 - (psi ** 1.25)) + z_in_end * (psi ** 1.25)
            dr_ds = ((-r_in_tan + r_in_end) * sin_psi) / 0.26
            dz_ds = (-(z_outer_tan - z_in_end) * 1.25 * (psi ** 0.25)) / 0.26
        return r, z, dr_ds, dz_ds

    for i in range(nth):
        t0, t1 = theta[i], theta[i + 1]
        t_mid = 0.5 * (t0 + t1)
        out_n_xy = np.array([np.cos(t_mid), np.sin(t_mid)])
        facing = np.dot(out_n_xy, cam_dir_xy)
        
        if pass_type == "back" and facing >= 0.0:
            continue
        elif pass_type == "front" and facing < 0.0:
            continue

        for j in range(ns):
            s0, s1 = s_vals[j], s_vals[j + 1]
            sm = 0.5 * (s0 + s1)
            
            r0, z0_p, _, _ = smooth_profile(s0)
            r1, z1_p, dr_ds, dz_ds = smooth_profile(s1)
            
            norm_3d = np.array([dz_ds * np.cos(t_mid), dz_ds * np.sin(t_mid), -dr_ds])
            n_len = np.linalg.norm(norm_3d)
            norm_3d = norm_3d / n_len if n_len > 1e-6 else np.array([0, 0, 1])
                
            if np.dot(norm_3d, cam_vec) < -0.05:
                continue
                
            dot_key = max(0.0, float(np.dot(norm_3d, LIGHT_DIR)))
            dot_spec = max(0.0, float(np.dot(norm_3d, HALF_VEC))) ** 24
            
            if sm < 0.30:
                w_f = (1.0 - sm / 0.30)
                c_grad = warm_col * w_f + base_col * (1.0 - w_f)
            elif sm <= 0.74:
                r_f = max(0.0, (sm - 0.38) / 0.36)
                c_grad = base_col * (1.0 - r_f) + rim_col * r_f
            else:
                in_f = (sm - 0.74) / 0.26
                c_grad = rim_col * (1.0 - in_f) + base_col * in_f
                
            shear_wave = 1.0 + 0.025 * np.sin(7 * t_mid - 10 * sm)
            ao = 0.72 + 0.28 * (1.0 - (sm - 0.74) / 0.26) if sm > 0.74 else 1.0
            
            blend = np.clip(dot_key, 0.0, 1.0)
            base_shaded = cool_col * (1.0 - blend) + c_grad * blend
            intensity = (0.38 + 0.50 * dot_key + 0.12 * dot_spec) * shear_wave * ao
            intensity = np.clip(intensity, 0.0, 1.0)
            fc = np.clip(base_shaded * intensity + 0.16 * dot_spec, 0.0, 1.0)
            
            p00 = [cx + r0 * np.cos(t0), cy + r0 * np.sin(t0), z0_p]
            p10 = [cx + r1 * np.cos(t0), cy + r1 * np.sin(t0), z1_p]
            p11 = [cx + r1 * np.cos(t1), cy + r1 * np.sin(t1), z1_p]
            p01 = [cx + r0 * np.cos(t1), cy + r0 * np.sin(t1), z0_p]
            
            renderer.add_poly([p00, p10, p11, p01], fc, "none", lw=0.0, zo=zo)


# ── 4. SOLID CONSUMABLE ROD WITH VISCOPLASTIC MUSHROOMING & ROTATIONAL RESISTANCE ── #

def compute_material_deformation_ability(heat_temp):
    """
    Computes the temperature-dependent plastic deformation ability (0.0 to 1.0).
    
    Physics:
    - When the rotating rod is pressed against the stationary base plate, rotation
      is heavily resisted (dry/Coulomb friction and frictional torque).
    - However, at low temperatures (T < 450 K), the metal retains high flow stress
      and yield strength (rigid/elastic regime). Even under heavy axial plunge load,
      the material CANNOT deform outward into a mushroom shape.
    - Between 450 K and 540 K, thermal recovery and dynamic recrystallization activate,
      sharply lowering the flow stress and enabling viscoplastic deformation.
    - Once the material reaches this deformation ability, the combination of high axial
      load and rotational shear resistance forces the softened material radially outward,
      forming the characteristic mushroom flash bulge.
    """
    t_onset = 450.0   # Plastic deformation onset [K] (~177 °C)
    t_full  = 540.0   # Full viscoplastic deformation ability [K] (~267 °C)
    if heat_temp <= t_onset:
        return 0.0
    elif heat_temp >= t_full:
        return 1.0
    x = (heat_temp - t_onset) / (t_full - t_onset)
    return float(x * x * (3.0 - 2.0 * x))  # Smoothstep S-curve


def _compute_mushroom_radius(z, z0, rod_height, radius, mushroom_scale):
    """
    Computes the radial profile of the rod at height z, including outward
    viscoplastic mushrooming formed by contact pressure and rotational resistance.
    
    The rod is initially a straight cylinder. When pushed against the base plate,
    rotation becomes difficult. Once the material reaches its deformation ability,
    rotational shear and axial compression force the material outward radially.
    
    mushroom_scale: 0.0 = no deformation (straight cylinder), 1.0 = fully developed mushroom.
    """
    if mushroom_scale < 0.005:
        return radius  # Undeformed straight cylinder
    
    # Mushroom zone is confined to the bottom ~18% of the rod
    mushroom_zone = 0.18 * rod_height
    dz = z - z0
    if dz > mushroom_zone or dz < 0.0:
        return radius
    
    # Normalized height coordinate: 0 at transition boundary, 1 at bottom contact tip
    xi = 1.0 - (dz / mushroom_zone)
    
    # Outward plastic flow: combination of smooth interface flare and shear bulge
    flange = (xi ** 2) * (3.0 - 2.0 * xi)      # Outward flange expansion at contact
    swell  = 0.40 * (np.sin(np.pi * xi) ** 1.4)  # Viscoplastic shear bulge
    
    # Maximum radial expansion up to ~26% (e.g., 12.5 mm -> 15.8 mm)
    max_bulge = radius * 0.26 * mushroom_scale
    return radius + max_bulge * (flange + swell)


def draw_solid_rod(renderer, cx, cy, z0, z1, radius, rot_angle=0.0,
                   nth=72, nz=28, contact_pressure=0.0, heat_temp=293.15,
                   mushroom_scale=None):
    """
    Renders the rotating consumable tool rod with physically driven mushrooming:
    - Straight cylindrical shank throughout most of the tool
    - Viscoplastic mushrooming at the bottom: forms ONLY when the material
      reaches its deformation ability (T >= 450 K) under contact pressure
      and rotational drag.
    - Torsional shear twist in the mushroom zone: shows that rotation is
      resisted at the contact interface, causing the material to lag and shear
      radially outward.
    - Permanent plastic deformation: when tool retracts, the mushroom shape is retained.
    
    Parameters:
        contact_pressure: Normalized contact load (0-1).
        heat_temp: Interface temperature [K]. Controls deformation ability onset.
        mushroom_scale: Optional override for cumulative plastic mushroom scale (0-1).
                        If None, computed from contact_pressure * deformation_ability(heat_temp).
    """
    base_rgb  = np.array([142, 178, 204]) / 255.0
    warm_rgb  = np.array([158, 182, 198]) / 255.0
    cool_rgb  = np.array([118, 155, 186]) / 255.0
    hot_rgb   = np.array([215, 135, 55]) / 255.0    # Heated deformation zone tint
    mesh_ec   = "#0E1F2E"
    
    theta = np.linspace(0, 2 * np.pi, nth + 1) + rot_angle
    zvals = np.linspace(z0, z1, nz + 1)
    rod_height = z1 - z0
    
    cam_az = np.radians(-48)
    cam_dir_xy = np.array([np.cos(cam_az), np.sin(cam_az)])
    
    # Compute or use provided mushroom scale
    if mushroom_scale is None:
        def_ability = compute_material_deformation_ability(heat_temp)
        mushroom_scale = np.clip(contact_pressure, 0.0, 1.0) * def_ability
    else:
        mushroom_scale = np.clip(mushroom_scale, 0.0, 1.0)
    
    # Pre-compute radii at each z-level for the mushroom profile
    radii = np.array([_compute_mushroom_radius(z, z0, rod_height, radius, mushroom_scale)
                      for z in zvals])
    
    # Torsional shear lag twist: interface resists rotation, so material lags in azimuth
    def get_torsional_twist(z):
        if mushroom_scale < 0.005:
            return 0.0
        h_f = (z - z0) / rod_height
        if h_f >= 0.18:
            return 0.0
        xi = 1.0 - (h_f / 0.18)
        # Azimuthal lag up to ~0.15 rad (~8.6 deg) at the contact face
        return -0.15 * (xi ** 1.8) * mushroom_scale
    
    twists = np.array([get_torsional_twist(z) for z in zvals])
    
    for i in range(nth):
        t0_base, t1_base = theta[i], theta[i + 1]
        t_mid_base = 0.5 * (t0_base + t1_base)
        
        out_normal_xy = np.array([np.cos(t_mid_base), np.sin(t_mid_base)])
        facing = np.dot(out_normal_xy, cam_dir_xy)
        if facing < -0.05:
            continue
        
        norm_3d = np.array([np.cos(t_mid_base), np.sin(t_mid_base), 0.0])
        dot_key = max(0.0, float(np.dot(norm_3d, LIGHT_DIR)))
        dot_spec = max(0.0, float(np.dot(norm_3d, HALF_VEC))) ** 28
        fresnel = np.clip(facing, 0.0, 1.0) ** 0.60
        
        blend = np.clip(dot_key, 0.0, 1.0)
        base_color = cool_rgb * (1.0 - blend) + warm_rgb * blend
        
        for j in range(nz):
            zb, zt = zvals[j], zvals[j + 1]
            zm = 0.5 * (zb + zt)
            rb, rt = radii[j], radii[j + 1]
            tw_b, tw_t = twists[j], twists[j + 1]
            
            t0b, t1b = t0_base + tw_b, t1_base + tw_b
            t0t, t1t = t0_base + tw_t, t1_base + tw_t
            
            # Mid angle with torsional shear for spindle index stripe
            t_mid_seg = 0.5 * (0.5 * (t0b + t1b) + 0.5 * (t0t + t1t))
            angle_mod = (t_mid_seg % (2 * np.pi))
            is_stripe = (angle_mod < 0.22) or (abs(angle_mod - np.pi) < 0.22)
            
            height_frac = (zm - z0) / rod_height
            ao = 0.84 + 0.16 * np.clip(height_frac / 0.15, 0.0, 1.0)
            
            intensity = (0.34 + 0.52 * dot_key + 0.14 * dot_spec) * fresnel * ao
            intensity = np.clip(intensity, 0.0, 1.0)
            
            fc = np.clip(base_color * intensity + 0.12 * dot_spec, 0.0, 1.0)
            
            # Tint the mushroom zone with a warm/hot color (viscoplastic shear heating)
            if mushroom_scale > 0.01 and height_frac < 0.18:
                heat_blend = mushroom_scale * (1.0 - height_frac / 0.18) * 0.48
                fc = fc * (1.0 - heat_blend) + hot_rgb * heat_blend
                fc = np.clip(fc, 0.0, 1.0)
            
            if is_stripe:
                fc = np.clip(fc * 0.70 + np.array([0.95, 0.35, 0.1]) * 0.30, 0.0, 1.0)
            
            verts = [
                [cx + rb * np.cos(t0b), cy + rb * np.sin(t0b), zb],
                [cx + rb * np.cos(t1b), cy + rb * np.sin(t1b), zb],
                [cx + rt * np.cos(t1t), cy + rt * np.sin(t1t), zt],
                [cx + rt * np.cos(t0t), cy + rt * np.sin(t0t), zt],
            ]
            renderer.add_poly(verts, fc, mesh_ec, lw=0.07, zo=6)
    
    # Bottom disk cap (visible when mushroomed or retracted above plate)
    if mushroom_scale > 0.05 or z0 > 20.1:
        bottom_r = radii[0]
        nr_bottom = 5
        rvals_bot = np.linspace(0, bottom_r, nr_bottom + 1)
        for i in range(nth):
            t0 = theta[i] + twists[0]
            t1 = theta[i + 1] + twists[0]
            t_mid = 0.5 * (t0 + t1)
            out_n = np.array([np.cos(t_mid), np.sin(t_mid)])
            if np.dot(out_n, cam_dir_xy) < -0.05:
                continue
            for j in range(nr_bottom):
                r0b, r1b = rvals_bot[j], rvals_bot[j + 1]
                r_frac = r1b / bottom_r
                bot_intensity = 0.38 - 0.08 * r_frac ** 2
                n_bot = np.array([0, 0, -1])
                dot_bot = max(0.0, float(np.dot(n_bot, LIGHT_DIR)))
                fc_bot = np.clip(base_rgb * (bot_intensity + 0.15 * dot_bot), 0.0, 1.0)
                fc_bot = fc_bot * (1.0 - mushroom_scale * 0.35) + hot_rgb * (mushroom_scale * 0.35)
                fc_bot = np.clip(fc_bot, 0.0, 1.0)
                verts = [
                    [cx + r0b * np.cos(t0), cy + r0b * np.sin(t0), z0],
                    [cx + r1b * np.cos(t0), cy + r1b * np.sin(t0), z0],
                    [cx + r1b * np.cos(t1), cy + r1b * np.sin(t1), z0],
                    [cx + r0b * np.cos(t1), cy + r0b * np.sin(t1), z0],
                ]
                renderer.add_poly(verts, fc_bot, mesh_ec, lw=0.04, zo=5)

    # Chamfered top rim ring
    chamfer_h = rod_height * 0.015
    chamfer_r = radius * 0.96
    rim_rgb = np.array([165, 192, 212]) / 255.0
    
    for i in range(nth):
        t0, t1 = theta[i], theta[i + 1]
        t_mid = 0.5 * (t0 + t1)
        out_n = np.array([np.cos(t_mid), np.sin(t_mid)])
        if np.dot(out_n, cam_dir_xy) < -0.05:
            continue
        
        norm_3d = np.array([np.cos(t_mid) * 0.7, np.sin(t_mid) * 0.7, 0.7])
        norm_3d = norm_3d / np.linalg.norm(norm_3d)
        dot_l = max(0.0, float(np.dot(norm_3d, LIGHT_DIR)))
        fc_rim = np.clip(rim_rgb * (0.45 + 0.55 * dot_l), 0.0, 1.0)
        
        verts = [
            [cx + radius * np.cos(t0),    cy + radius * np.sin(t0),    z1 - chamfer_h],
            [cx + radius * np.cos(t1),    cy + radius * np.sin(t1),    z1 - chamfer_h],
            [cx + chamfer_r * np.cos(t1), cy + chamfer_r * np.sin(t1), z1],
            [cx + chamfer_r * np.cos(t0), cy + chamfer_r * np.sin(t0), z1],
        ]
        renderer.add_poly(verts, fc_rim, mesh_ec, lw=0.06, zo=8)
        
    # Top disk cap
    nr = 7
    rvals = np.linspace(0, chamfer_r, nr + 1)
    for i in range(nth):
        t0, t1 = theta[i], theta[i + 1]
        for j in range(nr):
            r0, r1 = rvals[j], rvals[j + 1]
            r_frac = rvals[j + 1] / chamfer_r
            top_intensity = 0.72 - 0.12 * r_frac**2
            n_top = np.array([0, 0, 1])
            dot_top = max(0.0, float(np.dot(n_top, LIGHT_DIR)))
            fc_top = np.clip(base_rgb * (top_intensity + 0.28 * dot_top), 0.0, 1.0)
            
            verts = [
                [cx + r0 * np.cos(t0), cy + r0 * np.sin(t0), z1],
                [cx + r1 * np.cos(t0), cy + r1 * np.sin(t0), z1],
                [cx + r1 * np.cos(t1), cy + r1 * np.sin(t1), z1],
                [cx + r0 * np.cos(t1), cy + r0 * np.sin(t1), z1],
            ]
            renderer.add_poly(verts, fc_top, mesh_ec, lw=0.05, zo=9)


# ── 5. PROGRESSIVE FRICTION SURFACING DEPOSIT BEAD ───────────────────────── #

def draw_refined_fs_layer(renderer, rod_cx, rod_cy, rod_r, plate_t,
                          y_start=50.0, dep_length=0.0, ny=60, nx=40,
                          peak_temp=700.0):
    """
    Renders high-realism metallic Friction Surfacing deposit layer:
    - Crowned trapezoidal cross-section with advancing/retreating asymmetry
    - 3D rotational semicircular shear ripples that catch directional key light
    - Rich metallic bronze-gold alloy color grading
    - Hot thermal glow at the deposition front right under the rotating tool
    - Solid bonded starter cross-section at trailing edge
    """
    if dep_length <= 1.0:
        return
        
    base_rgb  = np.array([224, 166, 44]) / 255.0   # Solid bronze-gold alloy
    warm_rgb  = np.array([252, 212, 112]) / 255.0  # Specular sheen
    cool_rgb  = np.array([168, 116, 26]) / 255.0   # Shaded flank
    glow_hot  = np.array([245, 120, 25]) / 255.0   # Hot glowing trailing edge
    
    dep_w_half = rod_r * 0.98
    dep_height = 4.4
    y_end      = y_start + dep_length
    
    ys = np.linspace(y_start, y_end, ny + 1)
    u_vals = np.linspace(-1.0, 1.0, nx + 1)

    def taper_y(y):
        frac = (y - y_start) / max(1.0, (y_end - y_start))
        ramp = np.clip(frac / 0.08, 0.0, 1.0)
        return 3 * ramp**2 - 2 * ramp**3

    def cross_section_profile(u):
        u_adj = np.where(u >= 0, u * 1.04, u * 0.96)
        val = np.maximum(0.0, 1.0 - np.abs(u_adj)**3.2)
        return val ** 0.58

    z_base = plate_t
    lambda_rip = 3.6

    for j in range(ny):
        y0, y1 = ys[j], ys[j + 1]
        ty0, ty1 = taper_y(y0), taper_y(y1)
        
        arc_r0 = np.sqrt((u_vals * dep_w_half)**2 + (y0 - rod_cy)**2)
        arc_r1 = np.sqrt((u_vals * dep_w_half)**2 + (y1 - rod_cy)**2)
        
        ripple0 = 1.0 + 0.042 * np.cos(2 * np.pi * arc_r0 / lambda_rip)
        ripple1 = 1.0 + 0.042 * np.cos(2 * np.pi * arc_r1 / lambda_rip)

        dist_to_tool = abs(y1 - y_end)
        thermal_glow = np.exp(-dist_to_tool / 14.0) * np.clip((peak_temp - 500.0) / 220.0, 0.0, 1.0)

        for i in range(nx):
            u0, u1 = u_vals[i], u_vals[i + 1]
            u_mid = 0.5 * (u0 + u1)
            
            h00 = dep_height * ty0 * cross_section_profile(u0) * ripple0[i]
            h10 = dep_height * ty0 * cross_section_profile(u1) * ripple0[i + 1]
            h11 = dep_height * ty1 * cross_section_profile(u1) * ripple1[i + 1]
            h01 = dep_height * ty1 * cross_section_profile(u0) * ripple1[i]
            
            p00 = [rod_cx + u0 * dep_w_half * ty0, y0, z_base + h00]
            p10 = [rod_cx + u1 * dep_w_half * ty0, y0, z_base + h10]
            p11 = [rod_cx + u1 * dep_w_half * ty1, y1, z_base + h11]
            p01 = [rod_cx + u0 * dep_w_half * ty1, y1, z_base + h01]
            
            v_u = np.array(p10) - np.array(p00)
            v_y = np.array(p01) - np.array(p00)
            norm = np.cross(v_u, v_y)
            n_len = np.linalg.norm(norm)
            norm = norm / n_len if n_len > 1e-6 else np.array([0, 0, 1])
                
            dot_key = max(0.0, float(np.dot(norm, LIGHT_DIR)))
            dot_spec = max(0.0, float(np.dot(norm, HALF_VEC))) ** 24
            
            edge_dist = 1.0 - abs(u_mid)
            ao_edge = 0.82 + 0.18 * np.clip(edge_dist / 0.25, 0.0, 1.0)
            
            r_mid_val = 0.5 * (arc_r0[i] + arc_r1[i])
            rip_shine = 0.06 * max(0.0, float(np.sin(2 * np.pi * r_mid_val / lambda_rip)))
            
            blend = np.clip(dot_key, 0.0, 1.0)
            base_col = cool_rgb * (1.0 - blend) + (base_rgb * 0.4 + warm_rgb * 0.6) * blend
            
            if thermal_glow > 0.02:
                base_col = base_col * (1.0 - thermal_glow * 0.85) + glow_hot * (thermal_glow * 0.85)
                
            intensity = (0.38 + 0.50 * dot_key + 0.12 * dot_spec + rip_shine) * ao_edge
            intensity = np.clip(intensity, 0.0, 1.0)
            fc = np.clip(base_col * intensity + 0.18 * dot_spec, 0.0, 1.0)
            
            verts = [p00, p10, p11, p01]
            renderer.add_poly(verts, fc, fc, lw=0.0, zo=4)

    # Solid Bonded Front Face (Trailing Edge Starter Cross-Section)
    ty_start = taper_y(ys[1])
    if ty_start > 0.01:
        n_cap = np.array([0.0, -1.0, 0.0])
        dot_cap_k = max(0.0, float(np.dot(n_cap, LIGHT_DIR)))
        dot_cap_s = max(0.0, float(np.dot(n_cap, HALF_VEC))) ** 18
        
        for i in range(nx):
            u0, u1 = u_vals[i], u_vals[i + 1]
            um = 0.5 * (u0 + u1)
            h0 = dep_height * ty_start * cross_section_profile(u0)
            h1 = dep_height * ty_start * cross_section_profile(u1)
            edge_dist = 1.0 - abs(um)
            ao_cap = 0.85 + 0.15 * np.clip(edge_dist / 0.20, 0.0, 1.0)
            fc_cap = np.clip((cool_rgb * 0.3 + base_rgb * 0.7) * (0.42 + 0.52 * dot_cap_k + 0.06 * dot_cap_s) * ao_cap, 0.0, 1.0)
            
            verts = [
                [rod_cx + u0 * dep_w_half * ty_start, ys[1], z_base],
                [rod_cx + u1 * dep_w_half * ty_start, ys[1], z_base],
                [rod_cx + u1 * dep_w_half * ty_start, ys[1], z_base + h1],
                [rod_cx + u0 * dep_w_half * ty_start, ys[1], z_base + h0],
            ]
            renderer.add_poly(verts, fc_cap, fc_cap, lw=0.0, zo=4)


# ── 6. PRECISION DIMENSION ANNOTATIONS ────────────────────────────────────── #

def draw_plate_dimensions(ax, x0, y0, z0, dx, dy, dz):
    """
    Draws engineering standard dimension lines matching process_schematic.py:
    - Width (along X, front edge): 120 mm
    - Length (along Y, right edge): 300 mm
    - Thickness (along Z, front-left corner): 20 mm
    """
    dim_color = "#112233"
    ext_color = "#445566"
    
    # (A) Width Dimension (X direction)
    y_dim = y0 - 12
    ax.plot([x0, x0], [y0, y_dim - 2.5], [0, 0], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    ax.plot([x0 + dx, x0 + dx], [y0, y_dim - 2.5], [0, 0], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    ax.plot([x0, x0 + dx], [y_dim, y_dim], [0, 0], color=dim_color, lw=1.1, zorder=9)
    ax.plot([x0, x0], [y_dim - 2.0, y_dim + 2.0], [0, 0], color=dim_color, lw=1.2, zorder=9)
    ax.plot([x0 + dx, x0 + dx], [y_dim - 2.0, y_dim + 2.0], [0, 0], color=dim_color, lw=1.2, zorder=9)
    
    ax.text(x0, y_dim - 3.5, 0, "0", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="center", va="top", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    ax.text(x0 + dx, y_dim - 3.5, 0, f"{dx:.0f} mm", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="center", va="top", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    ax.text(x0 + dx / 2, y_dim - 7.0, 0, "Width", color=dim_color, fontsize=8.5, fontweight="bold",
            ha="center", va="top", zorder=10,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#B0BAC6", linewidth=0.6, alpha=0.95))

    # (B) Length Dimension (Y direction)
    x_dim = x0 + dx + 12
    ax.plot([x0 + dx, x_dim + 2.5], [y0, y0], [0, 0], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    ax.plot([x0 + dx, x_dim + 2.5], [y0 + dy, y0 + dy], [0, 0], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    ax.plot([x_dim, x_dim], [y0, y0 + dy], [0, 0], color=dim_color, lw=1.1, zorder=9)
    ax.plot([x_dim - 2.0, x_dim + 2.0], [y0, y0], [0, 0], color=dim_color, lw=1.2, zorder=9)
    ax.plot([x_dim - 2.0, x_dim + 2.0], [y0 + dy, y0 + dy], [0, 0], color=dim_color, lw=1.2, zorder=9)
    
    ax.text(x_dim + 3.5, y0, 0, "0", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="left", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    ax.text(x_dim + 3.5, y0 + dy, 0, f"{dy:.0f} mm", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="left", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    ax.text(x_dim + 6.5, y0 + dy / 2, 0, "Length", color=dim_color, fontsize=8.5, fontweight="bold",
            ha="left", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#B0BAC6", linewidth=0.6, alpha=0.95))

    # (C) Thickness Dimension (Z direction)
    x_thk = x0 - 9
    y_thk = y0 - 9
    ax.plot([x0, x_thk - 2.5], [y0, y_thk], [0, 0], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    ax.plot([x0, x_thk - 2.5], [y0, y_thk], [dz, dz], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    ax.plot([x_thk, x_thk], [y_thk, y_thk], [0, dz], color=dim_color, lw=1.1, zorder=9)
    ax.plot([x_thk - 2.0, x_thk + 2.0], [y_thk, y_thk], [0, 0], color=dim_color, lw=1.2, zorder=9)
    ax.plot([x_thk - 2.0, x_thk + 2.0], [y_thk, y_thk], [dz, dz], color=dim_color, lw=1.2, zorder=9)
    
    ax.text(x_thk - 3.5, y_thk - 3.5, 0, "0", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="right", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    ax.text(x_thk - 3.5, y_thk - 3.5, dz, f"{dz:.0f} mm", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="right", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    ax.text(x_thk - 4.5, y_thk - 4.5, dz / 2, "Thickness", color=dim_color, fontsize=8, fontweight="bold",
            ha="right", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#B0BAC6", linewidth=0.6, alpha=0.95))
