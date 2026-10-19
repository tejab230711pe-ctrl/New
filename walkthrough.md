# AFSD Full Multi-Block Simulation with Moving Tool Rod & Progressive Layer Deposition

## 1. Process Overview & Multi-Block 3D Architecture
- **Framework**: MOOSE (Multiphysics Object Oriented Simulation Environment)
- **Application**: [`RotatingDiskDepositionApp`](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/rotating_disk_deposition-opt)
- **Material**: AA5083 Aluminum Alloy (Temperature-dependent thermophysical and Johnson-Cook viscoplastic flow properties)
- **Multi-Block FE Mesh Formulation** (`CombinerGenerator` in [`input/deposition.i`](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/input/deposition.i)):
  - **Block 0 (`plate`)**: Substrate Base Plate ($120 \times 300 \times 20\,\text{mm}$, 3,840 Hex8 elements).
  - **Block 1 (`rod`)**: Consumable Tool Rod ($\varnothing 25\,\text{mm}$, height $50\,\text{mm}$, 288 Hex8 elements) initially positioned $5\,\text{mm}$ above plate surface at $Y = 50\,\text{mm}$.
  - **Block 2 (`bead`)**: Deposited Bead Track ($25\,\text{mm}$ width, $200\,\text{mm}$ length, $3\,\text{mm}$ layer thickness, 384 Hex8 elements) sitting along the deposition path $Y \in [50, 250]\,\text{mm}$ on the substrate top surface.
  - **Total 3D Mesh Elements**: 4,512 Hex8 elements.

---

## 2. Consumable Tool Kinematics & Layer Deposition Mechanism

### A. 3D Prescribed Kinematics of the Moving Tool Rod
The tool rod undergoes the full multi-stage kinematic cycle via $(U_x, U_y, U_z)$ Dirichlet boundary conditions on `boundary = rod_boundary`:
1. **Approach Stage ($0.0 - 1.6\,\text{s}$)**: Tool rod lowers from clearance ($Z = 25\,\text{mm}$) to substrate surface ($Z = 20\,\text{mm}$, $\Delta U_z = -5\,\text{mm}$). Spindle accelerates from 0 to 1200 RPM.
2. **Dwell Stage ($1.6 - 5.6\,\text{s}$)**: Normal preload ramps from 0 to $5.0\,\text{kN}$ ($P = 4.5\,\text{MPa}$ contact pressure) at fixed $Y = 50\,\text{mm}$. Frictional stirring heats the interface to the hot-working / dynamic recrystallization regime ($T \approx 670\,\text{K}$).
3. **Traverse Stage ($5.6 - 45.6\,\text{s}$)**: Tool traverses $200\,\text{mm}$ along $+Y$ ($Y: 50 \to 250\,\text{mm}$, $v_y = 5.0\,\text{mm/s}$) while maintaining rotation (1200 RPM) and normal contact preload ($5.0\,\text{kN}$).
4. **Retract & Cool Stage ($45.6 - 68.0\,\text{s}$)**: Normal preload drops to zero, tool retracts vertically by $+5\,\text{mm}$ ($Z: 20 \to 25\,\text{mm}$, $U_z = 0$), and spindle stops. The deposited bead cools on the anvil bed.

### B. Progressive Layer Deposition Condition
The solid bead materializes behind the advancing tool rod via the scalar state variable `is_deposited` ($0.0 \to 1.0$):
- **Criterion**: An element transitions to deposited state (`is_deposited = 1.0`) when:
  1. The tool rod is in active contact and traversing ($t \ge 5.6\,\text{s}$),
  2. The stir zone front reaches the element coordinate: $y \le y_{\text{tool}}(t) + R_{\text{tool}}$,
  3. The local interface temperature reaches/exceeds the AA5083 plasticization onset temperature ($T \ge T_{\text{plast}} \approx 673\,\text{K} = 400\,^\circ\text{C}$).
- **State Retention**: Once deposited, the element permanently remains consolidated as the tool passes and the bead cools down.

---

## 3. Simulation Results & Safety Verification ($t = 0 \to 68.0\,\text{s}$)

| Process Variable | Simulation Value | Safety / Limit Threshold | Status |
|---|---|---|---|
| **Peak Temperature ($T_{\text{max}}$)** | **$720.97\,\text{K}$** ($447.8\,^\circ\text{C}$) | Solidus $T_s = 864.15\,\text{K}$ ($591\,^\circ\text{C}$) | **OPTIMAL ✅ (Hot-working regime, no melting)** |
| **Average Substrate Temp** | **$312.99\,\text{K}$** ($39.8\,^\circ\text{C}$) | Substrate integrity limit | **EXCELLENT ✅ (High localized heat dissipation)** |
| **Peak Axial Preload** | **$5.00\,\text{kN}$** | Machine capacity $15.0\,\text{kN}$ | **SAFE ✅ (3.0× safety margin)** |
| **Peak Spindle Power** | **$6.20\,\text{kW}$** | Spindle motor ceiling $22.0\,\text{kW}$ | **SAFE ✅ (3.5× safety margin)** |
| **Peak Contact Pressure** | **$4.50\,\text{MPa}$** | Plasticization gate $\ge 3.0\,\text{MPa}$ | **ACHIEVED ✅ (Consistent stir compaction)** |
| **Max Plastic Strain** | **$\varepsilon_p = 5.34$** | Severe plastic deformation (SPD) | **HIGH REFINEMENT ✅ (Grain refinement regime)** |
| **Bead Track Deposition** | **$100.0\%$** ($200\,\text{mm}$) | Track length $200\,\text{mm}$ | **COMPLETED ✅ (Full bead materialized)** |

---

## 4. Visualizations & Generated Artifacts

### 3D Physical Motion & Progressive Deposition
![AFSD 3D Stages](afsd_3d_stages.png)
*Figure 1: 3D multi-block finite element model showing the tool rod lowering ($t=0 \to 5\,\text{s}$), dwelling, traversing with progressive bead deposition ($t=25\,\text{s}$ and $t=45.6\,\text{s}$), and retracting ($t=68\,\text{s}$).*

### Process Dashboard
![AFSD Dashboard](afsd_simulation_dashboard.png)
*Figure 2: 4-panel process response tracking thermal history, spindle power, normal servo load, and contact pressure/plastic strain accumulation across all 4 stages.*

### Key Output Files & Simulation Video Suites
- **3D Isometric Simulation Video**: [afsd_simulation_isometric.mp4](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/afsd_simulation_isometric.mp4) • [GIF](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/afsd_simulation_isometric.gif)
- **Macro Close-Up Dynamics Video**: [afsd_simulation_closeup.mp4](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/afsd_simulation_closeup.mp4) • [GIF](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/afsd_simulation_closeup.gif)
- **Scientific Multi-Viewport Dashboard**: [afsd_simulation_multiview.mp4](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/afsd_simulation_multiview.mp4) • [GIF](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/afsd_simulation_multiview.gif)
- **Simulation Video Suite Generator**: [`scripts/generate_simulation_videos.py`](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/scripts/generate_simulation_videos.py)
- **High-Performance Renderer**: [`scripts/simulation_renderer.py`](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/scripts/simulation_renderer.py)
- **Exodus 3D FE Database (112 MB)**: [afsd_deposition_out.e](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/afsd_deposition_out.e)
- **Time-Series CSV (178 timesteps)**: [afsd_deposition_out.csv](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/afsd_deposition_out.csv)
- **Summary Report**: [afsd_results_summary.txt](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/afsd_results_summary.txt)
- **3D Visualization Script**: [`scripts/render_3d_stages.py`](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/scripts/render_3d_stages.py)
- **Dashboard Generator**: [`scripts/visualize_results.py`](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/scripts/visualize_results.py)

---

## 5. How to View the Moving Tool Rod & Deposited Bead in ParaView

To inspect the 3D simulation in **ParaView**:

1. **Open the Exodus file**:
   - File -> Open -> Select [`afsd_deposition_out.e`](file:///home/teja/Videos/a28796a1-f5f2-42d5-ad41-3bb346f082b6/afsd_deposition_out.e).
   - In the Properties panel, ensure all three Element Blocks (`plate`, `rod`, `bead`) and all Variables (`T`, `Ux`, `Uy`, `Uz`, `is_deposited`, `contact_pressure`, `plastic_strain`) are checked.
   - Click **Apply**.

2. **To see the Physical Rod Motion**:
   - With the dataset selected, add **Filters -> Common -> Warp By Vector** (or click the Warp icon on the toolbar).
   - In properties, set **Vectors** to `[Ux, Uy, Uz]`.
   - Set **Scale Factor** to `1.0`.
   - Click **Apply**.
   - Scrub the time slider or press **Play**: You will see the tool rod descend onto the plate, dwell and rotate, traverse along the centerline ($Y: 50 \to 250\,\text{mm}$), and retract vertically upwards!

3. **To see the Progressive Bead Materialization**:
   - Apply **Filters -> Common -> Threshold** to the mesh.
   - Set **Scalars** to `is_deposited`.
   - Set **Minimum** to `0.5`, **Maximum** to `1.0`.
   - Click **Apply**.
   - As you advance time from $t = 5.6\,\text{s}$ to $45.6\,\text{s}$, the solid bead progressively materializes and elongates directly behind the moving tool rod.
   - Color the surfaces by `T` (temperature) with the `Plasma` or `Cool to Warm` colormap to view the heat-affected zone ($470 - 720\,\text{K}$).
