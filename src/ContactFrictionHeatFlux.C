#include "ContactFrictionHeatFlux.h"
#include "Function.h"

registerMooseObject("RotatingDiskDepositionApp", ContactFrictionHeatFlux);

InputParameters
ContactFrictionHeatFlux::validParams()
{
  InputParameters params = IntegratedBC::validParams();
  params.addRequiredCoupledVar("contact_pressure", "Solved normal pressure from [Contact]");
  params.addRequiredParam<Real>("rpm", "Spindle speed (rev/min)");
  params.addRequiredParam<Real>("friction_coefficient",
                                "Coulomb coefficient; must match [Contact]/friction_coefficient");
  params.addParam<Real>("heat_partition", 0.5, "Fraction of interface heat assigned to this side");
  params.addParam<Real>("efficiency", 0.9, "Fraction of friction work converted to heat");
  params.addParam<Real>("center_x", 0.0, "Spindle centre x coordinate (m)");
  params.addRequiredParam<FunctionName>("tool_center_y", "Time-dependent spindle centre y coordinate");
  return params;
}

ContactFrictionHeatFlux::ContactFrictionHeatFlux(const InputParameters & parameters)
  : IntegratedBC(parameters),
    _contact_pressure(coupledValue("contact_pressure")),
    _omega(2.0 * libMesh::pi * getParam<Real>("rpm") / 60.0),
    _friction_coefficient(getParam<Real>("friction_coefficient")),
    _heat_partition(getParam<Real>("heat_partition")),
    _efficiency(getParam<Real>("efficiency")),
    _center_x(getParam<Real>("center_x")),
    _tool_center_y(getFunction("tool_center_y"))
{
}

Real
ContactFrictionHeatFlux::computeQpResidual()
{
  const Real radius = std::hypot(_q_point[_qp](0) - _center_x,
                                 _q_point[_qp](1) - _tool_center_y.value(_t, _q_point[_qp]));
  const Real pressure = std::max(0.0, _contact_pressure[_qp]);
  const Real flux = _heat_partition * _efficiency * _friction_coefficient * pressure * _omega * radius;
  // A positive source adds heat to the temperature equation.
  return -_test[_i][_qp] * flux;
}
