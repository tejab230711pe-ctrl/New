#!/usr/bin/env python3
"""Compare the AD viscosity spatial gradient with an independent finite difference."""
import math
from pathlib import Path
import tempfile
from check_process_mechanics import BASE, run, close

DECK = '''
[Functions]
 [temperature]
  type = ParsedFunction
  expression = '723.15 + .001*x'
 []
 [vx]
  type = ParsedFunction
  expression = '6*y'
 []
[]
[AuxVariables]
 [T]
 []
 [velocity]
  family = LAGRANGE_VEC
  order = FIRST
 []
 [gradient]
  family = MONOMIAL
  order = CONSTANT
 []
[]
[ICs]
 [T]
  type = FunctionIC
  variable = T
  function = temperature
 []
 [velocity]
  type = VectorFunctionIC
  variable = velocity
  function_x = vx
  function_y = 0
  function_z = 0
 []
[]
[Materials]
 [flow]
  type = AA5083ALEViscoplasticMaterial
  temperature = T
  velocity = velocity
  CLAMP
 []
[]
[AuxKernels]
 [gradient]
  type = ADMaterialRealVectorValueAux
  variable = gradient
  property = grad_mu_temperature
  component = 0
 []
[]
[Postprocessors]
 [gradient]
  type = ElementAverageValue
  variable = gradient
 []
[]
'''


def viscosity(temperature):
    rate = math.hypot(6/math.sqrt(3), 1e-3)
    return math.asinh(math.exp((math.log(rate)+174700/(8.314*temperature)-24.98)/5.23))/(.015e-6*3*rate)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='afsd-grad-mu-') as temporary:
        folder = Path(temporary)
        result = run(folder, 'gradient', BASE+DECK.replace('CLAMP',''))
        step = .001
        expected = .001*(viscosity(723.1505+step)-viscosity(723.1505-step))/(2*step)
        close(result['gradient'], expected, 'temperature viscosity gradient', atol=1e-7)
        result = run(folder, 'clamped', BASE+DECK.replace('CLAMP','mu_min = 1e4\n  mu_max = 1e4'))
        close(result['gradient'],0.,'clamped viscosity gradient')
        print('PASS viscosity gradient: finite difference and constant clipped branch')
