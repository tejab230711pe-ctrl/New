#include "NonnegativePlasticHeatEnergy.h"

#include "MooseMesh.h"
#include "MooseVariable.h"

#include <algorithm>

registerMooseObject("RotatingDiskDepositionApp", NonnegativePlasticHeatEnergy);

InputParameters
NonnegativePlasticHeatEnergy::validParams()
{
  InputParameters params = Kernel::validParams();
  params.addRequiredCoupledVar("displacements", "Mechanical displacement variables.");
  params.addParam<std::string>("base_name", "", "Material property base name.");
  params.addParam<Real>("coeff", 1.0, "Taylor-Quinney conversion coefficient.");
  params.addClassDescription("Plastic heat source clamped to non-negative mechanical dissipation.");
  return params;
}

NonnegativePlasticHeatEnergy::NonnegativePlasticHeatEnergy(const InputParameters & parameters)
  : Kernel(parameters),
    _coeff(getParam<Real>("coeff")),
    _plastic_heat(getMaterialProperty<Real>(
        (isParamValid("base_name") ? getParam<std::string>("base_name") + "_" : "") +
        "plastic_heat")),
    _dplastic_heat_dstrain(getMaterialProperty<RankTwoTensor>(
        (isParamValid("base_name") ? getParam<std::string>("base_name") + "_" : "") +
        "dplastic_heat_dstrain")),
    _disp_var(coupledComponents("displacements"))
{
  if (_disp_var.size() != _mesh.dimension())
    mooseError("NonnegativePlasticHeatEnergy requires one displacement per mesh dimension.");
  for (const auto i : index_range(_disp_var))
    _disp_var[i] = coupled("displacements", i);
}

Real
NonnegativePlasticHeatEnergy::computeQpResidual()
{
  return -_test[_i][_qp] * _coeff * std::max(0.0, _plastic_heat[_qp]);
}

Real
NonnegativePlasticHeatEnergy::computeQpJacobian()
{
  return computeQpOffDiagJacobian(_var.number());
}

Real
NonnegativePlasticHeatEnergy::computeQpOffDiagJacobian(unsigned int jvar)
{
  // The derivative is active only on the physically dissipative branch.
  if (_plastic_heat[_qp] <= 0.0)
    return 0.0;
  for (const auto i : index_range(_disp_var))
    if (jvar == _disp_var[i])
      return -_test[_i][_qp] * _coeff *
             (_dplastic_heat_dstrain[_qp] * _grad_phi[_j][_qp])(i);
  return 0.0;
}
