#!/usr/bin/env python3
"""
Publication-Quality Isometric Solid FEM Schematic (Refined Q1 Journal Standard):
- Engineering-accurate Friction Surfacing (FS) deposit layer:
  * Pronounced semicircular frictional shear banding / ripples
  * Realistic Advancing Side (AS) vs. Retreating Side (RS) flash asymmetry
  * Solid bonded cross-section at trailing edge
- 100% Opaque solid base plate and consumable rod with crisp finite element mesh.
- Smooth mushroomed plasticized annulus collar with rotational flow curvature.
- Subtle substrate contact shadow.
- Precision dimension lines for Base Plate Length, Width, and Thickness (in mm).
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════════════ #
#                            LIGHTING MODEL                                   #
# ═══════════════════════════════════════════════════════════════════════════ #

# Directional key light from upper-left-front (normalized vector)
LIGHT_DIR = np.array([-0.38, -0.52, 0.76])
LIGHT_DIR = LIGHT_DIR / np.linalg.norm(LIGHT_DIR)

# Fill light from upper-right
FILL_LIGHT = np.array([0.5, 0.3, 0.8])
FILL_LIGHT = FILL_LIGHT / np.linalg.norm(FILL_LIGHT)

def apply_lighting(base_rgb, normal, ambient=0.40, diffuse=0.52, fill=0.08, specular=0.10):
    """
    Calculate shaded RGB color given surface normal, key light, fill light,
    and subtle specular highlight.
    """
    norm = np.array(normal, dtype=float)
    n_len = np.linalg.norm(norm)
    if n_len > 1e-6:
        norm = norm / n_len
    else:
        norm = np.array([0, 0, 1])
    
    # Key light dot
    dot_key = max(0.0, float(np.dot(norm, LIGHT_DIR)))
    # Fill light dot
    dot_fill = max(0.0, float(np.dot(norm, FILL_LIGHT)))
    
    # Halfway specular
    view_dir = np.array([0.5, -0.6, 0.6])
    view_dir = view_dir / np.linalg.norm(view_dir)
    half_vec = (LIGHT_DIR + view_dir)
    half_vec = half_vec / np.linalg.norm(half_vec)
    dot_spec = max(0.0, float(np.dot(norm, half_vec))) ** 16
    
    intensity = ambient + diffuse * dot_key + fill * dot_fill + specular * dot_spec
    intensity = np.clip(intensity, 0.0, 1.0)
    
    base = np.array(base_rgb, dtype=float)
    return np.clip(base * intensity, 0.0, 1.0)


def _add_poly(ax, verts, fc, ec, alpha=1.0, lw=0.12, zo=1):
    poly = Poly3DCollection([verts], alpha=alpha, facecolor=fc, edgecolor=ec,
                            linewidths=lw, zorder=zo)
    ax.add_collection3d(poly)


# ── 1. SOFT CONTACT SHADOW UNDER BASE PLATE ──────────────────────────────── #

def draw_contact_shadow(ax, x0, y0, dx, dy, offset=12, z_plane=-6):
    """Renders a soft, realistic ground contact shadow under the plate."""
    xs = np.linspace(x0 - 4, x0 + dx + 10, 16)
    ys = np.linspace(y0 - 6, y0 + dy + 8, 18)
    shadow_col = [0.72, 0.75, 0.80]
    
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = x0 + dx / 2, y0 + dy / 2
            d = np.sqrt(((xs[i] - cx) / (dx * 0.6))**2 + ((ys[j] - cy) / (dy * 0.6))**2)
            alpha_s = np.clip(0.35 * (1.0 - d**1.5), 0.0, 0.35)
            if alpha_s > 0.02:
                verts = [
                    [xs[i],     ys[j],     z_plane],
                    [xs[i + 1], ys[j],     z_plane],
                    [xs[i + 1], ys[j + 1], z_plane],
                    [xs[i],     ys[j + 1], z_plane],
                ]
                _add_poly(ax, verts, shadow_col, shadow_col, alpha=alpha_s, lw=0.0, zo=0)


# ── 2. SOLID BASE PLATE (REALISTIC METALLIC RENDERING) ──────────────────── #

def draw_solid_plate(ax, x0, y0, z0, dx, dy, dz, nx=32, ny=38, nz=6, rcx=0, rcy=40, rod_r=12.5):
    """
    Renders a high-realism metallic base plate with:
      - Per-quad Blinn-Phong specular sheen and directional lighting gradient
      - Ambient occlusion near the base plate bottom and around the tool contact zone
      - Machined chamfer edge highlights on visible top boundaries
      - Crisp fine FE mesh lines (#0E1F2E)
    """
    x1, y1, z1 = x0 + dx, y0 + dy, z0 + dz
    
    # Base alloy colors (Al1100 / mild steel backing)
    base_plate_rgb = np.array([168, 192, 216]) / 255.0  # Precision steel blue
    warm_plate_rgb = np.array([184, 204, 224]) / 255.0  # Warm highlight
    cool_plate_rgb = np.array([142, 168, 194]) / 255.0  # Cool shadow
    mesh_ec = "#0E1F2E"                                  # Crisp dark navy mesh lines
    
    # Lighting & view vectors
    light_dir = LIGHT_DIR
    cam_az = np.radians(-48)
    view_dir = np.array([np.cos(cam_az), np.sin(cam_az), 0.45])
    view_dir = view_dir / np.linalg.norm(view_dir)
    half_vec = (light_dir + view_dir)
    half_vec = half_vec / np.linalg.norm(half_vec)
    
    # ── (A) Top Face (Z = z1, Normal = [0, 0, 1]) ───────────────────────── #
    n_top = np.array([0, 0, 1.0])
    dot_top_key = max(0.0, float(np.dot(n_top, light_dir)))
    dot_top_spec = max(0.0, float(np.dot(n_top, half_vec))) ** 24
    
    xs = np.linspace(x0, x1, nx + 1)
    ys = np.linspace(y0, y1, ny + 1)
    
    for i in range(nx):
        for j in range(ny):
            xm = 0.5 * (xs[i] + xs[i + 1])
            ym = 0.5 * (ys[j] + ys[j + 1])
            
            # Distance to tool center for contact ambient occlusion
            d_tool = np.sqrt((xm - rcx)**2 + (ym - rcy)**2)
            ao_tool = 0.85 + 0.15 * np.clip((d_tool - rod_r) / 14.0, 0.0, 1.0)
            
            # Subtle directional lighting gradient across the large plate surface
            grad_x = 0.94 + 0.12 * ((x1 - xm) / dx)
            grad_y = 0.94 + 0.12 * ((y1 - ym) / dy)
            surf_grad = grad_x * grad_y
            
            intensity = (0.38 + 0.48 * dot_top_key + 0.14 * dot_top_spec) * ao_tool * surf_grad
            intensity = np.clip(intensity, 0.0, 1.0)
            
            # Warm-cool tint blend
            blend = np.clip(dot_top_key * surf_grad, 0.0, 1.0)
            base_col = cool_plate_rgb * (1.0 - blend) + warm_plate_rgb * blend
            fc_top = np.clip(base_col * intensity + 0.08 * dot_top_spec, 0.0, 1.0)
            
            verts = [
                [xs[i],     ys[j],     z1],
                [xs[i + 1], ys[j],     z1],
                [xs[i + 1], ys[j + 1], z1],
                [xs[i],     ys[j + 1], z1],
            ]
            _add_poly(ax, verts, fc_top, mesh_ec, alpha=1.0, lw=0.08, zo=2)
            
    # ── (B) Front Face (Y = y0, Normal = [0, -1, 0]) ─────────────────────── #
    n_front = np.array([0, -1.0, 0])
    dot_front_key = max(0.0, float(np.dot(n_front, light_dir)))
    dot_front_spec = max(0.0, float(np.dot(n_front, half_vec))) ** 18
    zs = np.linspace(z0, z1, nz + 1)
    
    for i in range(nx):
        xm = 0.5 * (xs[i] + xs[i + 1])
        grad_x = 0.92 + 0.16 * ((x1 - xm) / dx)
        for k in range(nz):
            zm = 0.5 * (zs[k] + zs[k + 1])
            # Ambient occlusion: darker near ground contact shadow
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
            _add_poly(ax, verts, fc_front, mesh_ec, alpha=1.0, lw=0.08, zo=2)
            
    # ── (C) Right Face (X = x1, Normal = [1, 0, 0]) ──────────────────────── #
    n_right = np.array([1.0, 0, 0])
    dot_right_key = max(0.0, float(np.dot(n_right, light_dir)))
    dot_right_spec = max(0.0, float(np.dot(n_right, half_vec))) ** 18
    
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
            _add_poly(ax, verts, fc_right, mesh_ec, alpha=1.0, lw=0.08, zo=2)

    # ── (D) Machined Perimeter Edge Highlights ──────────────────────────── #
    edge_highlight_col = "#EAF2F9"
    # Front-top edge
    ax.plot([x0, x1], [y0, y0], [z1, z1], color=edge_highlight_col, lw=0.9, alpha=0.95, zorder=3)
    # Right-top edge
    ax.plot([x1, x1], [y0, y1], [z1, z1], color=edge_highlight_col, lw=0.9, alpha=0.95, zorder=3)
    # Front-right vertical corner edge
    ax.plot([x1, x1], [y0, y0], [z0, z1], color=edge_highlight_col, lw=0.8, alpha=0.90, zorder=3)


# ── 3. REALISTIC 360° SOFT CURLED FLASH ANNULUS COLLAR (NO SHARP CORNERS) ─ #

def draw_refined_annulus_collar_layer(ax, cx, cy, z_base, rod_r, pass_type="all", nth=96, ns=36):
    """
    Renders an authentic, soft, organically curled flash annulus collar with zero sharp corners:
      - Continuous C1-smooth rounded toroidal cross-section (outer flare -> soft rounded crest -> inner bowl)
      - Perfectly rounded top bead lip with soft rolling specular highlights
      - Thermal metallic color gradation: warm friction shear root -> silvery alloy body -> brilliant crest
      - Rotational shear striations with dual-pass 360° depth stratification
    """
    # Curated metallic alloy color palette
    base_col  = np.array([168, 192, 214]) / 255.0  # Silvery Al1100 alloy
    warm_col  = np.array([215, 202, 168]) / 255.0  # Warm friction-heated shear root
    rim_col   = np.array([238, 246, 254]) / 255.0  # Polished specular rim highlight
    cool_col  = np.array([125, 152, 178]) / 255.0  # Ambient shadow tint
    
    delta_r  = 6.6    # Radial flare expansion (mm)
    h_crest  = 5.4    # Height of rounded crest (mm)
    r_crest  = 1.35   # Soft rounded crest fillet radius (mm)
    
    theta = np.linspace(0, 2 * np.pi, nth + 1)
    s_vals = np.linspace(0, 1.0, ns + 1)
    
    cam_az = np.radians(-48)
    cam_dir_xy = np.array([np.cos(cam_az), np.sin(cam_az)])
    light_dir = LIGHT_DIR
    view_dir = np.array([np.cos(cam_az), np.sin(cam_az), 0.45])
    view_dir = view_dir / np.linalg.norm(view_dir)
    half_vec = (light_dir + view_dir)
    half_vec = half_vec / np.linalg.norm(half_vec)
    
    zo = 5 if pass_type == "back" else 7
    
    def smooth_profile(s):
        """
        Continuous, soft C1 cross-section without any sharp corners.
        Returns: r(s), z(s), dr_ds, dz_ds
        """
        r_outer_max = rod_r + delta_r
        z_outer_tan = z_base + (h_crest - r_crest)
        
        if s <= 0.46:
            # (1) Outer convex flare curving smoothly upward & outward
            xi = s / 0.46
            sin_xi = np.sin(xi * np.pi * 0.5)
            cos_xi = np.cos(xi * np.pi * 0.5)
            r = rod_r + delta_r * (sin_xi ** 1.15)
            z = z_base + (h_crest - r_crest) * (sin_xi ** 1.45)
            dr_ds = (delta_r * 1.15 * (sin_xi ** 0.15) * cos_xi * (np.pi * 0.5)) / 0.46
            dz_ds = ((h_crest - r_crest) * 1.45 * (sin_xi ** 0.45) * cos_xi * (np.pi * 0.5)) / 0.46
        elif s <= 0.74:
            # (2) Soft, continuous rounded semicircle crest (no sharp corners!)
            phi = (s - 0.46) / 0.28 * np.pi  # 0 to pi
            r_center = r_outer_max - r_crest
            z_center = z_outer_tan
            r = r_center + r_crest * np.cos(phi)
            z = z_center + r_crest * np.sin(phi)
            dr_ds = (-r_crest * np.sin(phi) * np.pi) / 0.28
            dz_ds = (r_crest * np.cos(phi) * np.pi) / 0.28
        else:
            # (3) Inner concave bowl descending smoothly back to rod interface
            psi = (s - 0.74) / 0.26
            r_in_tan = r_outer_max - 2 * r_crest
            r_in_end = rod_r + 0.15
            z_in_end = z_base + 0.8
            
            cos_psi = 0.5 * (1.0 - np.cos(psi * np.pi))
            sin_psi = 0.5 * np.sin(psi * np.pi) * np.pi
            r = r_in_tan * (1.0 - cos_psi) + r_in_end * cos_psi
            z = z_outer_tan * (1.0 - (psi ** 1.25)) + z_in_end * (psi ** 1.25)
            dr_ds = ((-r_in_tan + r_in_end) * sin_psi) / 0.26
            dz_ds = (-(z_outer_tan - z_in_end) * 1.25 * (psi ** 0.25)) / 0.26
            
        return r, z, dr_ds, dz_ds

    cam_vec = np.array([np.cos(cam_az) * np.cos(np.radians(29)),
                        np.sin(cam_az) * np.cos(np.radians(29)),
                        np.sin(np.radians(29))])
    cam_vec = cam_vec / np.linalg.norm(cam_vec)

    for i in range(nth):
        t0, t1 = theta[i], theta[i + 1]
        t_mid = 0.5 * (t0 + t1)
        out_n_xy = np.array([np.cos(t_mid), np.sin(t_mid)])
        facing = np.dot(out_n_xy, cam_dir_xy)
        
        # Layer filtering for 360° back-to-front depth stratification
        if pass_type == "back" and facing >= 0.0:
            continue
        elif pass_type == "front" and facing < 0.0:
            continue

        for j in range(ns):
            s0, s1 = s_vals[j], s_vals[j + 1]
            sm = 0.5 * (s0 + s1)
            
            r0, z0_p, _, _ = smooth_profile(s0)
            r1, z1_p, dr_ds, dz_ds = smooth_profile(s1)
            
            # Exact outward analytical surface normal into air
            norm_3d = np.array([dz_ds * np.cos(t_mid), dz_ds * np.sin(t_mid), -dr_ds])
            n_len = np.linalg.norm(norm_3d)
            if n_len > 1e-6:
                norm_3d = norm_3d / n_len
            else:
                norm_3d = np.array([0, 0, 1])
                
            # Camera backface culling (only draw surfaces facing camera)
            if np.dot(norm_3d, cam_vec) < -0.05:
                continue
                
            dot_key = max(0.0, float(np.dot(norm_3d, light_dir)))
            dot_spec = max(0.0, float(np.dot(norm_3d, half_vec))) ** 24
            
            # Soft thermal color grading across continuous parameter s
            if sm < 0.30:
                # Warm friction root
                w_f = (1.0 - sm / 0.30)
                c_grad = warm_col * w_f + base_col * (1.0 - w_f)
            elif sm <= 0.74:
                # Silvery alloy body transitioning to bright rounded crest
                r_f = max(0.0, (sm - 0.38) / 0.36)
                c_grad = base_col * (1.0 - r_f) + rim_col * r_f
            else:
                # Inner cavity shaded alloy
                in_f = (sm - 0.74) / 0.26
                c_grad = rim_col * (1.0 - in_f) + base_col * in_f
                
            # Soft rotational shear flow texture
            shear_wave = 1.0 + 0.025 * np.sin(7 * t_mid - 10 * sm)
            
            # Ambient cavity shading for inner bowl
            if sm > 0.74:
                ao = 0.72 + 0.28 * (1.0 - (sm - 0.74) / 0.26)
            else:
                ao = 1.0
                
            blend = np.clip(dot_key, 0.0, 1.0)
            base_shaded = cool_col * (1.0 - blend) + c_grad * blend
            intensity = (0.38 + 0.50 * dot_key + 0.12 * dot_spec) * shear_wave * ao
            intensity = np.clip(intensity, 0.0, 1.0)
            
            fc = np.clip(base_shaded * intensity + 0.16 * dot_spec, 0.0, 1.0)
            
            p00 = [cx + r0 * np.cos(t0), cy + r0 * np.sin(t0), z0_p]
            p10 = [cx + r1 * np.cos(t0), cy + r1 * np.sin(t0), z1_p]
            p11 = [cx + r1 * np.cos(t1), cy + r1 * np.sin(t1), z1_p]
            p01 = [cx + r0 * np.cos(t1), cy + r0 * np.sin(t1), z0_p]
            
            verts = [p00, p10, p11, p01]
            _add_poly(ax, verts, fc, "none", alpha=1.0, lw=0.0, zo=zo)


# ── 4. SOLID CONSUMABLE ROD (REALISTIC METALLIC RENDERING) ──────────────── #

def draw_solid_rod(ax, cx, cy, z0, z1, radius, nth=80, nz=32):
    """
    Renders a high-realism consumable rod with:
      - Per-quad Lambertian + Blinn-Phong specular shading
      - Fresnel edge darkening at silhouette angles
      - Base ambient occlusion (darker near plate junction)
      - Warm-cool metallic color shift across the surface
      - Chamfered top rim ring and radial top cap
      - Fine FE mesh lines
    """
    base_rgb  = np.array([142, 178, 204]) / 255.0  # Al1100 alloy base
    warm_rgb  = np.array([158, 182, 198]) / 255.0  # Warm highlight tint
    cool_rgb  = np.array([118, 155, 186]) / 255.0  # Cool shadow tint
    mesh_ec   = "#0E1F2E"                          # Crisp dark mesh lines
    
    theta = np.linspace(0, 2 * np.pi, nth + 1)
    zvals = np.linspace(z0, z1, nz + 1)
    rod_height = z1 - z0
    
    cam_az = np.radians(-48)
    cam_dir_xy = np.array([np.cos(cam_az), np.sin(cam_az)])
    light_dir = LIGHT_DIR
    view_dir = np.array([np.cos(cam_az), np.sin(cam_az), 0.45])
    view_dir = view_dir / np.linalg.norm(view_dir)
    half_vec = (light_dir + view_dir)
    half_vec = half_vec / np.linalg.norm(half_vec)
    
    # ── Cylinder body (front-facing quads only) ─────────────────────────── #
    for i in range(nth):
        t0, t1 = theta[i], theta[i + 1]
        t_mid = 0.5 * (t0 + t1)
        
        out_normal_xy = np.array([np.cos(t_mid), np.sin(t_mid)])
        facing = np.dot(out_normal_xy, cam_dir_xy)
        if facing < -0.05:
            continue
        
        norm_3d = np.array([np.cos(t_mid), np.sin(t_mid), 0.0])
        dot_key = max(0.0, float(np.dot(norm_3d, light_dir)))
        dot_spec = max(0.0, float(np.dot(norm_3d, half_vec))) ** 28
        fresnel = np.clip(facing, 0.0, 1.0) ** 0.60
        
        blend = np.clip(dot_key, 0.0, 1.0)
        base_color = cool_rgb * (1.0 - blend) + warm_rgb * blend
        
        for j in range(nz):
            zb, zt = zvals[j], zvals[j + 1]
            zm = 0.5 * (zb + zt)
            
            height_frac = (zm - z0) / rod_height
            ao = 0.84 + 0.16 * np.clip(height_frac / 0.15, 0.0, 1.0)
            
            intensity = (0.34 + 0.52 * dot_key + 0.14 * dot_spec) * fresnel * ao
            intensity = np.clip(intensity, 0.0, 1.0)
            
            fc = np.clip(base_color * intensity + 0.12 * dot_spec, 0.0, 1.0)
            
            verts = [
                [cx + radius * np.cos(t0), cy + radius * np.sin(t0), zb],
                [cx + radius * np.cos(t1), cy + radius * np.sin(t1), zb],
                [cx + radius * np.cos(t1), cy + radius * np.sin(t1), zt],
                [cx + radius * np.cos(t0), cy + radius * np.sin(t0), zt],
            ]
            _add_poly(ax, verts, fc, mesh_ec, alpha=1.0, lw=0.08, zo=7)
    
    # ── Chamfered top rim ring ──────────────────────────────────────────── #
    chamfer_h = rod_height * 0.012
    chamfer_r = radius * 0.97
    rim_rgb = np.array([165, 192, 212]) / 255.0
    
    for i in range(nth):
        t0, t1 = theta[i], theta[i + 1]
        t_mid = 0.5 * (t0 + t1)
        out_n = np.array([np.cos(t_mid), np.sin(t_mid)])
        if np.dot(out_n, cam_dir_xy) < -0.05:
            continue
        
        norm_3d = np.array([np.cos(t_mid) * 0.7, np.sin(t_mid) * 0.7, 0.7])
        norm_3d = norm_3d / np.linalg.norm(norm_3d)
        dot_l = max(0.0, float(np.dot(norm_3d, light_dir)))
        fc_rim = np.clip(rim_rgb * (0.45 + 0.55 * dot_l), 0.0, 1.0)
        
        verts = [
            [cx + radius * np.cos(t0),    cy + radius * np.sin(t0),    z1 - chamfer_h],
            [cx + radius * np.cos(t1),    cy + radius * np.sin(t1),    z1 - chamfer_h],
            [cx + chamfer_r * np.cos(t1), cy + chamfer_r * np.sin(t1), z1],
            [cx + chamfer_r * np.cos(t0), cy + chamfer_r * np.sin(t0), z1],
        ]
        _add_poly(ax, verts, fc_rim, mesh_ec, alpha=1.0, lw=0.06, zo=8)
    
    # ── Top disk cap with radial gradient ───────────────────────────────── #
    nr = 10
    rvals = np.linspace(0, chamfer_r, nr + 1)
    
    for i in range(nth):
        t0, t1 = theta[i], theta[i + 1]
        for j in range(nr):
            r0, r1 = rvals[j], rvals[j + 1]
            r_frac = rvals[j + 1] / chamfer_r
            
            top_intensity = 0.72 - 0.12 * r_frac**2
            n_top = np.array([0, 0, 1])
            dot_top = max(0.0, float(np.dot(n_top, light_dir)))
            fc_top = np.clip(base_rgb * (top_intensity + 0.28 * dot_top), 0.0, 1.0)
            
            verts = [
                [cx + r0 * np.cos(t0), cy + r0 * np.sin(t0), z1],
                [cx + r1 * np.cos(t0), cy + r1 * np.sin(t0), z1],
                [cx + r1 * np.cos(t1), cy + r1 * np.sin(t1), z1],
                [cx + r0 * np.cos(t1), cy + r0 * np.sin(t1), z1],
            ]
            _add_poly(ax, verts, fc_top, mesh_ec, alpha=1.0, lw=0.06, zo=9)


# ── 4. HIGH-REALISM FRICTION SURFACING LAYER (NO MESH) ──────────────────── #

def draw_refined_fs_layer(ax, rod_cx, rod_cy, rod_r, plate_t,
                          dep_length=58, ny=90, nx=48):
    """
    Renders an authentic, high-realism metallic Friction Surfacing deposit layer:
      - Crowned trapezoidal cross-section with advancing/retreating asymmetry
      - 3D rotational semicircular shear ripples that catch directional key light
      - Blinn-Phong metallic specular highlight band along the crowned apex
      - Rich metallic bronze-gold alloy color grading
      - Contact boundary ambient occlusion at substrate junction
      - Solid bonded starter cross-section
    """
    base_rgb  = np.array([224, 166, 44]) / 255.0  # Rich metallic bronze-gold
    warm_rgb  = np.array([252, 212, 112]) / 255.0 # Specular highlight sheen
    cool_rgb  = np.array([168, 116, 26]) / 255.0  # Shaded flank / root tint
    
    dep_w_half = rod_r * 0.98   # Half-width (~24.5 mm)
    dep_height = 4.4            # Layer thickness (~4.4 mm)
    y_start    = rod_cy - dep_length
    y_end      = rod_cy - 1.2   # Under tool trailing shear boundary
    
    ys = np.linspace(y_start, y_end, ny + 1)
    u_vals = np.linspace(-1.0, 1.0, nx + 1)
    
    cam_az = np.radians(-48)
    cam_dir_xy = np.array([np.cos(cam_az), np.sin(cam_az)])
    light_dir = LIGHT_DIR
    view_dir = np.array([np.cos(cam_az), np.sin(cam_az), 0.45])
    view_dir = view_dir / np.linalg.norm(view_dir)
    half_vec = (light_dir + view_dir)
    half_vec = half_vec / np.linalg.norm(half_vec)

    def taper_y(y):
        frac = (y - y_start) / (y_end - y_start)
        ramp = np.clip(frac / 0.08, 0.0, 1.0)
        return 3 * ramp**2 - 2 * ramp**3

    def cross_section_profile(u):
        u_adj = np.where(u >= 0, u * 1.04, u * 0.96)
        val = np.maximum(0.0, 1.0 - np.abs(u_adj)**3.2)
        return val ** 0.58

    z_base = plate_t

    for j in range(ny):
        y0, y1 = ys[j], ys[j + 1]
        ty0, ty1 = taper_y(y0), taper_y(y1)
        
        arc_r0 = np.sqrt((u_vals * dep_w_half)**2 + (y0 - rod_cy)**2)
        arc_r1 = np.sqrt((u_vals * dep_w_half)**2 + (y1 - rod_cy)**2)
        
        lambda_rip = 3.6
        ripple0 = 1.0 + 0.042 * np.cos(2 * np.pi * arc_r0 / lambda_rip)
        ripple1 = 1.0 + 0.042 * np.cos(2 * np.pi * arc_r1 / lambda_rip)

        for i in range(nx):
            u0, u1 = u_vals[i], u_vals[i + 1]
            u_mid = 0.5 * (u0 + u1)
            y_mid = 0.5 * (y0 + y1)
            
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
            if n_len > 1e-6:
                norm = norm / n_len
            else:
                norm = np.array([0, 0, 1])
                
            dot_key = max(0.0, float(np.dot(norm, light_dir)))
            dot_spec = max(0.0, float(np.dot(norm, half_vec))) ** 24
            
            edge_dist = 1.0 - abs(u_mid)
            ao_edge = 0.82 + 0.18 * np.clip(edge_dist / 0.25, 0.0, 1.0)
            
            r_mid_val = 0.5 * (arc_r0[i] + arc_r1[i])
            rip_shine = 0.06 * max(0.0, float(np.sin(2 * np.pi * r_mid_val / lambda_rip)))
            
            blend = np.clip(dot_key, 0.0, 1.0)
            base_col = cool_rgb * (1.0 - blend) + (base_rgb * 0.4 + warm_rgb * 0.6) * blend
            
            intensity = (0.38 + 0.50 * dot_key + 0.12 * dot_spec + rip_shine) * ao_edge
            intensity = np.clip(intensity, 0.0, 1.0)
            
            fc = np.clip(base_col * intensity + 0.18 * dot_spec, 0.0, 1.0)
            
            verts = [p00, p10, p11, p01]
            _add_poly(ax, verts, fc, fc, alpha=1.0, lw=0.0, zo=4)

    # ── Solid Bonded Front Face (Trailing Edge Cross-Section) ───────────── #
    ty_start = taper_y(ys[1])
    if ty_start > 0.01:
        n_cap = np.array([0.0, -1.0, 0.0])
        dot_cap_k = max(0.0, float(np.dot(n_cap, light_dir)))
        dot_cap_s = max(0.0, float(np.dot(n_cap, half_vec))) ** 18
        
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
            _add_poly(ax, verts, fc_cap, fc_cap, alpha=1.0, lw=0.0, zo=4)


# ── 5. ASYMMETRIC LATERAL FLASH RIDGES (NO MESH) ────────────────────────── #

def draw_refined_flash_ridges(ax, rod_cx, rod_cy, rod_r, plate_t,
                              dep_length=58, side=1, ny=65, nz_f=10):
    base_flash_rgb = np.array([214, 174, 88]) / 255.0
    
    dep_w_half = rod_r * 0.98
    y_start, y_end = rod_cy - dep_length, rod_cy - 1.2
    ys = np.linspace(y_start, y_end, ny + 1)
    
    flash_h   = 3.0 if side == 1 else 2.6
    flash_out = 4.4 if side == 1 else 3.8
    ts = np.linspace(0, 1, nz_f + 1)

    def taper_y(y):
        frac = (y - y_start) / (y_end - y_start)
        ramp = np.clip(frac / 0.07, 0.0, 1.0)
        return 3 * ramp**2 - 2 * ramp**3

    for j in range(ny):
        y0, y1 = ys[j], ys[j + 1]
        ty0, ty1 = taper_y(y0), taper_y(y1)
        
        for k in range(nz_f):
            s0, s1 = ts[k], ts[k + 1]
            s_mid = 0.5 * (s0 + s1)
            
            norm = [side * np.sin(s_mid * np.pi * 0.72), 0.0, np.cos(s_mid * np.pi * 0.72)]
            fc = apply_lighting(base_flash_rgb, norm, ambient=0.42, diffuse=0.58)
            
            def flash_coord(s, ty, y):
                bx = rod_cx + side * dep_w_half * ty
                dx = side * flash_out * ty * (s**1.85)
                dz = flash_h * ty * np.sin(s * np.pi * 0.68)
                return [bx + dx, y, plate_t + dz]
                
            p00 = flash_coord(s0, ty0, y0)
            p10 = flash_coord(s1, ty0, y0)
            p11 = flash_coord(s1, ty1, y1)
            p01 = flash_coord(s0, ty1, y1)
            
            _add_poly(ax, [p00, p10, p11, p01], fc, fc, alpha=1.0, lw=0.0, zo=4)


# ── 6. REALISTIC MUSHROOMED ANNULAR COLLAR (NO MESH) ────────────────────── #

def draw_refined_annulus_collar(ax, cx, cy, z_base, rod_r, nth=120, nr_ann=26):
    """
    Renders a state-of-the-art viscoplastic annulus collar:
      - Realistic rolled mushroom profile with a thick, outward-curling flash lip
      - Thermal heat-tint color transition: silvery rod alloy at root blending into
        warm plasticized friction heat-tint at the outer curling edge
      - Logarithmic spiral rotational shear striations matching 1000 RPM tool flow
      - High mesh resolution (120 x 26) with Blinn-Phong specular highlights
      - Contact ambient occlusion in root crevices and under curled lip
      - Smooth backface culling for 100% solid opacity
    """
    # Thermal gradient color endpoints
    silver_root_rgb = np.array([172, 196, 218]) / 255.0  # Al1100 rod junction
    warm_crown_rgb  = np.array([218, 202, 158]) / 255.0  # Hot plasticized alloy
    gold_edge_rgb   = np.array([225, 178, 62]) / 255.0   # Heat-tinted deposit transition
    cool_shadow_rgb = np.array([135, 158, 180]) / 255.0  # Shadow ambient
    
    # Lighting & view vectors
    light_dir = LIGHT_DIR
    cam_az = np.radians(-48)
    cam_dir_xy = np.array([np.cos(cam_az), np.sin(cam_az)])
    view_dir = np.array([np.cos(cam_az), np.sin(cam_az), 0.45])
    view_dir = view_dir / np.linalg.norm(view_dir)
    half_vec = (light_dir + view_dir)
    half_vec = half_vec / np.linalg.norm(half_vec)
    
    r_inner   = rod_r
    r_max_ext = rod_r + 7.2    # Maximum outward curl extent (~19.7 mm)
    collar_h  = 5.4            # Height of plasticized collar root (~5.4 mm)
    
    theta  = np.linspace(0, 2 * np.pi, nth + 1)
    s_vals = np.linspace(0.0, 1.0, nr_ann + 1)

    def collar_surface(t, s):
        # s=0 is at upper rod junction (z = z_base + collar_h, r = r_inner)
        # s=0.55 is at the rounded outer crown
        # s=1.0 is at the curled landing / substrate contact
        
        # Radial outward expansion
        r_curve = np.sin(0.5 * np.pi * (s ** 0.82))
        r = r_inner + (r_max_ext - r_inner) * r_curve
        
        # Vertical height curve: starts at collar_h, bulges over, rolls down to plate
        # Smooth cubic hermite / cosine blend
        h_main = collar_h * (np.cos(0.5 * np.pi * (s ** 1.15)) ** 1.3)
        # Lip curl: slight upward flare near s=0.7 before rounding down to 0.4 mm
        lip_roll = 0.35 * np.sin(np.pi * (s ** 1.4)) * (1.0 - s)
        
        # Logarithmic spiral shear flow striations (rotational tool deformation)
        spiral_phase = 18.0 * t - 5.0 * np.log(1.0 + 4.0 * s)
        ripple = 0.055 * np.cos(spiral_phase) * np.sin(np.pi * (s ** 0.65))
        
        z = z_base + np.maximum(0.2, h_main + lip_roll + ripple)
        return [cx + r * np.cos(t), cy + r * np.sin(t), z]

    for i in range(nth):
        t0, t1 = theta[i], theta[i + 1]
        t_mid = 0.5 * (t0 + t1)
        
        # Outward radial normal in XY plane
        out_n_xy = np.array([np.cos(t_mid), np.sin(t_mid)])
        
        # Back-face culling with generous margin for full visibility of rounded crown
        if np.dot(out_n_xy, cam_dir_xy) < -0.18:
            continue
            
        for k in range(nr_ann):
            s0, s1 = s_vals[k], s_vals[k + 1]
            s_mid = 0.5 * (s0 + s1)
            
            p00 = np.array(collar_surface(t0, s0))
            p10 = np.array(collar_surface(t1, s0))
            p11 = np.array(collar_surface(t1, s1))
            p01 = np.array(collar_surface(t0, s1))
            
            # Parametric tangent vectors -> accurate 3D outward normal
            v_s     = p01 - p00
            v_theta = p10 - p00
            norm = np.cross(v_s, v_theta)
            n_len = np.linalg.norm(norm)
            if n_len > 1e-6:
                norm = norm / n_len
            else:
                norm = np.array([np.cos(t_mid) * 0.65, np.sin(t_mid) * 0.65, 0.75])
                norm = norm / np.linalg.norm(norm)
            
            # Lambertian key lighting
            dot_key = max(0.0, float(np.dot(norm, light_dir)))
            
            # Blinn-Phong specular highlight along the rolled crown
            dot_spec = max(0.0, float(np.dot(norm, half_vec))) ** 26
            
            # Ambient occlusion: root crevice at rod (s->0) and under lip (s->1)
            ao = 0.86 + 0.14 * np.sin(np.pi * (s_mid ** 0.85))
            
            # Composite lighting intensity
            intensity = (0.34 + 0.52 * dot_key + 0.16 * dot_spec) * ao
            intensity = np.clip(intensity, 0.0, 1.0)
            
            # ── 3-way thermal color gradient across collar ──
            # s in [0, 0.5]: Silver -> Warm plasticized crown
            # s in [0.5, 1.0]: Warm crown -> Heat-tinted deposit gold
            if s_mid < 0.5:
                f_c = s_mid / 0.5
                base_c = silver_root_rgb * (1.0 - f_c) + warm_crown_rgb * f_c
            else:
                f_c = (s_mid - 0.5) / 0.5
                base_c = warm_crown_rgb * (1.0 - f_c) + gold_edge_rgb * f_c
                
            # Warm-cool lighting tint
            blend_l = np.clip(dot_key, 0.0, 1.0)
            tinted_c = cool_shadow_rgb * (1.0 - blend_l) + base_c * blend_l
            fc = np.clip(tinted_c * intensity + 0.18 * dot_spec, 0.0, 1.0)
            
            verts = [p00.tolist(), p10.tolist(), p11.tolist(), p01.tolist()]
            _add_poly(ax, verts, fc, fc, alpha=1.0, lw=0.0, zo=5)


# ── 7. PRECISION BASE PLATE DIMENSION SCALES (LENGTH, WIDTH, THICKNESS) ──── #

def draw_plate_dimensions(ax, x0, y0, z0, dx, dy, dz):
    """
    Draws engineering standard dimension lines for:
    - Width (along X, front edge)
    - Length (along Y, right side - unobstructed)
    - Thickness (along Z, front-left corner)
    """
    dim_color = "#112233"
    ext_color = "#445566"
    
    # ── (A) Width Dimension (X direction, front edge) ───────────────────── #
    y_dim = y0 - 10
    # Extension lines
    ax.plot([x0, x0], [y0, y_dim - 2.5], [0, 0], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    ax.plot([x0 + dx, x0 + dx], [y0, y_dim - 2.5], [0, 0], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    # Main dimension line
    ax.plot([x0, x0 + dx], [y_dim, y_dim], [0, 0], color=dim_color, lw=1.1, zorder=9)
    # End ticks
    ax.plot([x0, x0], [y_dim - 2.0, y_dim + 2.0], [0, 0], color=dim_color, lw=1.2, zorder=9)
    ax.plot([x0 + dx, x0 + dx], [y_dim - 2.0, y_dim + 2.0], [0, 0], color=dim_color, lw=1.2, zorder=9)
    # Origin and End tick labels
    ax.text(x0, y_dim - 3.5, 0, "0", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="center", va="top", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    ax.text(x0 + dx, y_dim - 3.5, 0, "250 mm", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="center", va="top", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    # Title badge in center
    ax.text(x0 + dx / 2, y_dim - 6.5, 0,
            "Width", color=dim_color, fontsize=8.5, fontweight="bold",
            ha="center", va="top", zorder=10,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#B0BAC6", linewidth=0.6, alpha=0.95))

    # ── (B) Length Dimension (Y direction, right edge - unobstructed) ───── #
    x_dim = x0 + dx + 10
    # Extension lines
    ax.plot([x0 + dx, x_dim + 2.5], [y0, y0], [0, 0], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    ax.plot([x0 + dx, x_dim + 2.5], [y0 + dy, y0 + dy], [0, 0], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    # Main dimension line
    ax.plot([x_dim, x_dim], [y0, y0 + dy], [0, 0], color=dim_color, lw=1.1, zorder=9)
    # End ticks
    ax.plot([x_dim - 2.0, x_dim + 2.0], [y0, y0], [0, 0], color=dim_color, lw=1.2, zorder=9)
    ax.plot([x_dim - 2.0, x_dim + 2.0], [y0 + dy, y0 + dy], [0, 0], color=dim_color, lw=1.2, zorder=9)
    # Origin and End tick labels
    ax.text(x_dim + 3.5, y0, 0, "0", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="left", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    ax.text(x_dim + 3.5, y0 + dy, 0, "300 mm", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="left", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    # Title badge in center
    ax.text(x_dim + 6.0, y0 + dy / 2, 0,
            "Length", color=dim_color, fontsize=8.5, fontweight="bold",
            ha="left", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#B0BAC6", linewidth=0.6, alpha=0.95))

    # ── (C) Thickness Dimension (Z direction, front-left corner) ─────────── #
    x_thk = x0 - 8
    y_thk = y0 - 8
    # Extension lines
    ax.plot([x0, x_thk - 2.5], [y0, y_thk], [0, 0], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    ax.plot([x0, x_thk - 2.5], [y0, y_thk], [dz, dz], color=ext_color, lw=0.6, linestyle="--", alpha=0.7, zorder=8)
    # Main dimension line
    ax.plot([x_thk, x_thk], [y_thk, y_thk], [0, dz], color=dim_color, lw=1.1, zorder=9)
    # End ticks
    ax.plot([x_thk - 2.0, x_thk + 2.0], [y_thk, y_thk], [0, 0], color=dim_color, lw=1.2, zorder=9)
    ax.plot([x_thk - 2.0, x_thk + 2.0], [y_thk, y_thk], [dz, dz], color=dim_color, lw=1.2, zorder=9)
    # Origin and End tick labels
    ax.text(x_thk - 3.5, y_thk - 3.5, 0, "0", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="right", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    ax.text(x_thk - 3.5, y_thk - 3.5, dz, "20 mm", color=dim_color, fontsize=7.5, fontweight="bold",
            ha="right", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#B0BAC6", linewidth=0.5, alpha=0.95))
    # Title badge in center
    ax.text(x_thk - 4.5, y_thk - 4.5, dz / 2,
            "Thickness", color=dim_color, fontsize=8, fontweight="bold",
            ha="right", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="#B0BAC6", linewidth=0.6, alpha=0.95))


# ═══════════════════════════════════════════════════════════════════════════ #
#                                MAIN                                         #
# ═══════════════════════════════════════════════════════════════════════════ #

def create_schematic():
    # Plate dimensions (mm)
    plate_w, plate_l, plate_t = 100, 120, 12
    px0 = -plate_w / 2
    py0 = -20

    # Rod dimensions (mm)
    rod_r, rod_h = 12.5, 80
    rcx, rcy = 0, 40
    rz0 = plate_t
    rz1 = rz0 + rod_h

    # Figure with well-proportioned framing
    fig = plt.figure(figsize=(9, 8), dpi=300)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0], projection="3d",
                      computed_zorder=False)
    ax.view_init(elev=29, azim=-48)
    ax.set_box_aspect([1.40, 1.40, 0.95])

    # 0. Soft Ground Contact Shadow
    print("  Rendering ground contact shadow ...")
    draw_contact_shadow(ax, px0, py0, plate_w, plate_l, z_plane=-2)

    # 1. 100% Solid Base Plate with Fine FE Mesh (Realistic Metallic Shading)
    print("  Rendering solid base plate with fine mesh ...")
    draw_solid_plate(ax, px0, py0, 0, plate_w, plate_l, plate_t,
                     nx=32, ny=38, nz=6, rcx=rcx, rcy=rcy, rod_r=rod_r)

    # 2. High-Realism Friction Surfacing Layer (No Mesh)
    print("  Rendering high-realism FS deposit layer (no mesh) ...")
    draw_refined_fs_layer(ax, rcx, rcy, rod_r, plate_t,
                          dep_length=58, ny=90, nx=48)

    # 3. Curled Flash Annulus Collar - Back Half (Behind Rod)
    print("  Rendering annulus collar (back half) ...")
    draw_refined_annulus_collar_layer(ax, rcx, rcy, plate_t, rod_r,
                                      pass_type="back", nth=96, ns=36)

    # 4. Solid Consumable Rod with Fine FE Mesh
    print("  Rendering solid consumable rod with fine mesh ...")
    draw_solid_rod(ax, rcx, rcy, rz0, rz1, rod_r,
                   nth=80, nz=32)

    # 5. Curled Flash Annulus Collar - Front Half (In Front of Rod)
    print("  Rendering annulus collar (front half) ...")
    draw_refined_annulus_collar_layer(ax, rcx, rcy, plate_t, rod_r,
                                      pass_type="front", nth=96, ns=36)

    # Balanced camera limits — centered cleanly on the friction surfacing assembly
    ax.set_xlim(-78, 78)
    ax.set_ylim(-45, 111)
    ax.set_zlim(-6, 115)
    for a in [ax.xaxis, ax.yaxis, ax.zaxis]:
        a.set_ticks([])
        a.pane.fill = False
        a.pane.set_edgecolor("white")
        a.line.set_color("white")
    ax.grid(False)

    # Save high-resolution PNG
    fig_path = os.path.join(OUT_DIR, "process_schematic_isometric.png")
    fig.savefig(fig_path, dpi=300, bbox_inches="tight",
                facecolor="white", edgecolor="none", pad_inches=0.05)
    print(f"\n  [OK] Successfully saved -> {fig_path}")
    plt.close(fig)


if __name__ == "__main__":
    create_schematic()
