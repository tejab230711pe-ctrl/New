#include "AFSDStabilized3Eqn.h"

registerMooseObject("RotatingDiskDepositionApp", AFSDStabilized3Eqn);

InputParameters
AFSDStabilized3Eqn::validParams()
{
  auto params = INSADStabilized3Eqn::validParams();
  params.addClassDescription("Temperature-dependent viscosity in the traction-form SUPG/PSPG "
                            "strong residual; restricted to Cartesian affine P1 TET4 velocity");
  return params;
}

AFSDStabilized3Eqn::AFSDStabilized3Eqn(const InputParameters & parameters)
  : INSADStabilized3Eqn(parameters),
    _grad_mu_temperature(getADMaterialProperty<RealVectorValue>("grad_mu_temperature"))
{
}

void
AFSDStabilized3Eqn::computeQpProperties()
{
  INSADStabilized3Eqn::computeQpProperties();
  if (_current_elem->type() != libMesh::TET4 || _velocity_var->feType().order != libMesh::FIRST ||
      _coord_sys != Moose::COORD_XYZ || _viscous_form != NS::ViscousForm::Traction)
    mooseError("AFSDStabilized3Eqn requires Cartesian TET4, FIRST-order velocity, traction viscosity");
  // -div(mu*(grad(v)+grad(v)^T)) contains this term even when Hessian(v)=0.
  const ADRealVectorValue correction =
      -(_grad_velocity[_qp] + _grad_velocity[_qp].transpose()) * _grad_mu_temperature[_qp];
  _viscous_strong_residual[_qp] += correction;
  _momentum_strong_residual[_qp] += correction;
}
