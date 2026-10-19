# Implementation Plan

## Goal
Enable the `MomentumBalance` kernel by building the MOOSE framework (and the application) with the **TensorMechanics** module, then re‑run the deposition simulation.

## User Review Required
> [!IMPORTANT] This will require compiling MOOSE from source (or rebuilding the existing MOOSE installation) and may take several minutes. Please confirm you have sufficient disk space and that you are okay with a fresh build.

## Open Questions
- Do you already have the MOOSE source repository available on this machine? If not, we will need to clone it (≈ 1 GB).
- Preferred location for the MOOSE source/build (e.g., `$HOME/moose` or inside the project folder)?
- Should the resulting executable replace the current `moose-opt` in your conda environment, or do you prefer a separate binary (e.g., `RotatingDiskDepositionApp`)?

## Proposed Changes
1. **Obtain MOOSE source** (if missing):
   ```bash
   git clone https://github.com/idaholab/moose.git $HOME/moose
   cd $HOME/moose
   ```
2. **Configure MOOSE with TensorMechanics**:
   ```bash
   ./configure --with-modules=TensorMechanics
   make -j$(nproc)   # builds the framework and the moose-opt executable
   ```
   This generates `framework/lib/libmoose.so` and the `moose-opt` binary that knows about `MomentumBalance`.
3. **Set environment for the application**:
   ```bash
   export MOOSE_DIR=$HOME/moose   # point to the source root
   export PATH=$HOME/moose/scripts:$PATH   # optional for convenience
   ```
4. **Re‑configure the deposition application** (using the CMakeLists we edited earlier):
   ```bash
   cd /home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6
   cmake -DMOOSE_MODULES=TensorMechanics -DMOOSE_DIR=$HOME/moose .
   make -j$(nproc)
   ```
   This will produce an executable (e.g., `RotatingDiskDepositionApp`).
5. **Update the run script** to use the newly built binary:
   ```bash
   # edit /home/teja/Videos/run_simulation.sh
   /home/teja/.gemini/antigravity-ide/brain/a28796a1-f5f2-42d5-ad41-3bb346f082b6/RotatingDiskDepositionApp -i "$INPUT_FILE"
   ```
6. **Run the simulation**:
   ```bash
   cd /home/teja/Videos
   ./run_simulation.sh
   ```
   Verify the job finishes with exit code 0 and that the output files are created.

## Verification Plan
- **Automated:** After building, execute `./run_simulation.sh` and capture the exit status. Success = 0.
- **Manual:** Inspect console output for the absence of the `MomentumBalance` registration error. Open the Exodus/CSV results to confirm temperature and displacement fields are present.

> [!NOTE] If you already have a pre‑built MOOSE binary that includes TensorMechanics, you can skip steps 1‑2 and just set `MOOSE_DIR` to that source tree.
