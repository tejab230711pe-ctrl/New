#include "ALEViscoplasticDissipationHeat.h"

registerMooseObject("RotatingDiskDepositionApp", ALEViscoplasticDissipationHeat);

InputParameters
ALEViscoplasticDissipationHeat::validParams()
{
  InputParameters params = ADKernel::validParams();
  params.addRequiredCoupledVar("velocity", "ALE material velocity");
  params.addParam<MaterialPropertyName>("mu_name", "mu", "Dynamic-viscosity property");
  params.addParam<Real>("taylor_quinney", 0.90, "Fraction of viscoplastic work converted to heat");
  return params;
}

ALEViscoplasticDissipationHeat::ALEViscoplasticDissipationHeat(const InputParameters & parameters)
  : ADKernel(parameters),
    _grad_velocity(adCoupledVectorGradient("velocity")),
    _mu(getADMaterialProperty<Real>(getParam<MaterialPropertyName>("mu_name"))),
    _taylor_quinney(getParam<Real>("taylor_quinney"))
{
}

ADReal
ALEViscoplasticDissipationHeat::computeQpResidual()
{
  const ADRealTensorValue D = 0.5 * (_grad_velocity[_qp] + _grad_velocity[_qp].transpose());
  const ADReal dissipation = 2.0 * _taylor_quinney * _mu[_qp] * D.doubleContraction(D);
  return -_test[_i][_qp] * dissipation;
}
