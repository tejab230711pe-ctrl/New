#include "ALEViscoplasticDissipationHeat.h"

registerMooseObject("RotatingDiskDepositionApp", ALEViscoplasticDissipationHeat);

InputParameters
ALEViscoplasticDissipationHeat::validParams()
{
  InputParameters params = ADKernel::validParams();
  params.addParam<MaterialPropertyName>("heat_property", "viscoplastic_heat",
                                      "Positive volumetric dissipation supplied by the flow material");
  return params;
}

ALEViscoplasticDissipationHeat::ALEViscoplasticDissipationHeat(const InputParameters & parameters)
  : ADKernel(parameters), _heat(getADMaterialProperty<Real>("heat_property"))
{
}

ADReal
ALEViscoplasticDissipationHeat::computeQpResidual()
{
  return -_test[_i][_qp] * _heat[_qp];
}
