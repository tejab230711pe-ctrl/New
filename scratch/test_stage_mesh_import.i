# Read-only smoke test for a remeshed AFSD stage.  It deliberately contains no
# physics and verifies that MOOSE can import Gmsh's physical volume/surface IDs.
[Mesh]
  type = FileMesh
  file = ../remesh_stages/feed_5mm/stage_01.msh
[]

[Variables]
  [mesh_probe]
    order = FIRST
    family = LAGRANGE
  []
[]

[Kernels]
  [mesh_probe_diffusion]
    type = Diffusion
    variable = mesh_probe
  []
[]

[Executioner]
  type = Steady
  solve_type = NEWTON
[]

[Outputs]
  exodus = true
  file_base = scratch/stage_mesh_import
[]
