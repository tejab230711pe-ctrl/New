
[Mesh]
 type = GeneratedMesh
 dim = 3
[]
[Problem]
 solve = false
[]
[Executioner]
 type = Transient
 num_steps = 1
 dt = 1
[]
[Outputs]
 csv = true
[]

[AuxVariables]
 [T]
  initial_condition = 293.15
 []
 [velocity]
  family = LAGRANGE_VEC
  order = FIRST
 []
 [solid_k]
  family = MONOMIAL
  order = CONSTANT
 []
 [solid_cp]
  family = MONOMIAL
  order = CONSTANT
 []
 [solid_rho]
  family = MONOMIAL
  order = CONSTANT
 []
 [flow_k]
  family = MONOMIAL
  order = CONSTANT
 []
 [flow_cp]
  family = MONOMIAL
  order = CONSTANT
 []
 [flow_rho]
  family = MONOMIAL
  order = CONSTANT
 []
[]
[Materials]
  [aa5083_k]

    type = ParsedMaterial
    property_name = thermal_conductivity
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 112.5 + (122.7 - 112.5)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 122.7 + (142.3 - 122.7)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 142.3 + (177.2 - 142.3)*((T - 273.15) - 280.0)/300.0, 177.2)))'
  []
  [aa5083_rho]

    type = ParsedMaterial
    property_name = density
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 2673.9 + (2642.7 - 2673.9)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 2642.7 + (2611.5 - 2642.7)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 2611.5 + (2549.2 - 2611.5)*((T - 273.15) - 280.0)/300.0, 2549.2)))'
  []
  [aa5083_cp]

    type = ParsedMaterial
    property_name = specific_heat
    coupled_variables = 'T'
    expression = 'if((T - 273.15) <= 80.0, 924.1 + (984.2 - 924.1)*((T - 273.15) + 20.0)/100.0,
                  if((T - 273.15) <= 280.0, 984.2 + (1081.2 - 984.2)*((T - 273.15) - 80.0)/200.0,
                  if((T - 273.15) <= 580.0, 1081.2 + (1261.4 - 1081.2)*((T - 273.15) - 280.0)/300.0, 1261.4)))'
  []
 [flow]
  type = AA5083ALEViscoplasticMaterial
  temperature = T
  velocity = velocity
 []
[]
[AuxKernels]
 [solid_k]
  type = MaterialRealAux
  variable = solid_k
  property = thermal_conductivity
 []
 [solid_cp]
  type = MaterialRealAux
  variable = solid_cp
  property = specific_heat
 []
 [solid_rho]
  type = MaterialRealAux
  variable = solid_rho
  property = density
 []
 [flow_k]
  type = ADMaterialRealAux
  variable = flow_k
  property = k
 []
 [flow_cp]
  type = ADMaterialRealAux
  variable = flow_cp
  property = cp
 []
 [flow_rho]
  type = ADMaterialRealAux
  variable = flow_rho
  property = rho
 []
[]
[Postprocessors]
 [solid_k]
  type = ElementAverageValue
  variable = solid_k
 []
 [solid_cp]
  type = ElementAverageValue
  variable = solid_cp
 []
 [solid_rho]
  type = ElementAverageValue
  variable = solid_rho
 []
 [flow_k]
  type = ElementAverageValue
  variable = flow_k
 []
 [flow_cp]
  type = ElementAverageValue
  variable = flow_cp
 []
 [flow_rho]
  type = ElementAverageValue
  variable = flow_rho
 []
[]
