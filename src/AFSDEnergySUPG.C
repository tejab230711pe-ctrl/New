#include "AFSDEnergySUPG.h"
registerMooseObject("RotatingDiskDepositionApp", AFSDEnergySUPG);

InputParameters
AFSDEnergySUPG::validParams()
{
  auto params = INSADEnergySUPG::validParams();
  params.addParam<MaterialPropertyName>("heat_property", "viscoplastic_heat",
                                      "Positive volumetric heating used by the energy kernel");
  params.addClassDescription("INS energy SUPG with consistent viscoplastic heat source.");
  return params;
}
AFSDEnergySUPG::AFSDEnergySUPG(const InputParameters & parameters)
  : INSADEnergySUPG(parameters), _heat(getADMaterialProperty<Real>("heat_property"))
{
}
ADReal
AFSDEnergySUPG::precomputeQpStrongResidual()
{
  return INSADEnergySUPG::precomputeQpStrongResidual() - _heat[_qp];
}
