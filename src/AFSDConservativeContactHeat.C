#include "AFSDConservativeContactHeat.h"
registerMooseObject("RotatingDiskDepositionApp", AFSDConservativeContactHeat);

InputParameters
AFSDConservativeContactHeat::validParams()
{
  auto params = ADMortarConstraint::validParams();
  params.addClassDescription("Equal-and-opposite finite contact heat exchange on a shared mortar interface, without a thermal multiplier unknown.");
  params.addRequiredRangeCheckedParam<Real>("conductance", "conductance > 0", "Closed-contact conductance in W/(m^2 K)");
  params.set<bool>("compute_lm_residuals") = false;
  return params;
}

AFSDConservativeContactHeat::AFSDConservativeContactHeat(const InputParameters & parameters)
  : ADMortarConstraint(parameters), _conductance(getParam<Real>("conductance"))
{
  if (isParamValid("variable") || getParam<bool>("compute_lm_residuals"))
    paramError("variable", "This finite-conductance model has no thermal Lagrange multiplier");
}

ADReal
AFSDConservativeContactHeat::computeQpResidual(Moose::MortarType type)
{
  const Real gap = (_phys_points_primary[_qp] - _phys_points_secondary[_qp]) * _normals[_qp];
  if (gap > 0.)
    return 0.;
  const ADReal flux = _conductance * (_u_secondary[_qp] - _u_primary[_qp]);
  switch (type)
  {
    case Moose::MortarType::Secondary:
      return flux * _test_secondary[_i][_qp];
    case Moose::MortarType::Primary:
      return -flux * _test_primary[_i][_qp];
    default:
      return 0.;
  }
}
