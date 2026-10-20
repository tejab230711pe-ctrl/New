[Mesh]
  [plate_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 8
    ny = 10
    nz = 2
    xmin = -0.060
    xmax =  0.060
    ymin =  0.000
    ymax =  0.300
    zmin =  0.000
    zmax =  0.020
  []
  [plate_id]
    type = SubdomainBoundingBoxGenerator
    input = plate_mesh
    bottom_left = '-0.060 0.000 0.000'
    top_right = '0.060 0.300 0.020'
    block_id = 0
    block_name = 'plate'
  []

  [rod_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 4
    ny = 4
    nz = 5
    xmin = -0.0125
    xmax =  0.0125
    ymin =  0.0375
    ymax =  0.0625
    zmin =  0.025
    zmax =  0.075
  []
  [rod_id]
    type = SubdomainBoundingBoxGenerator
    input = rod_mesh
    bottom_left = '-0.0125 0.0375 0.025'
    top_right = '0.0125 0.0625 0.075'
    block_id = 1
    block_name = 'rod'
  []

  [bead_mesh]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 4
    ny = 10
    nz = 2
    xmin = -0.0125
    xmax =  0.0125
    ymin =  0.050
    ymax =  0.250
    zmin =  0.020
    zmax =  0.023
  []
  [bead_id]
    type = SubdomainBoundingBoxGenerator
    input = bead_mesh
    bottom_left = '-0.0125 0.050 0.020'
    top_right = '0.0125 0.250 0.023'
    block_id = 2
    block_name = 'bead'
  []

  [combine]
    type = CombinerGenerator
    inputs = 'plate_id rod_id bead_id'
  []

  [break_boundary]
    type = BreakBoundaryOnSubdomainGenerator
    input = combine
  []
[]
