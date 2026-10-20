#include "ContactFrictionHeatFlux.h"
#include "AA5083ThermalProperties.h"

registerMooseObject("RotatingDiskDepositionApp", ContactFrictionHeatFlux);

InputParameters
ContactFrictionHeatFlux::validParams()
{
  InputParameters params = IntegratedBC::validParams();
  params.addRequiredCoupledVar("temperature", "Interface temperature used for mu(T)");
  params.addRequiredCoupledVar("contact_pressure", "Solved normal pressure from [Contact]");
  params.addRequiredParam<UserObjectName>("material_props", "AA5083 property UserObject");
  params.addRequiredParam<Real>("rpm", "Spindle speed (rev/min)");
  params.addParam<Real>("heat_partition", 0.5, "Fraction of interface heat assigned to this side");
  params.addParam<Real>("efficiency", 0.9, "Fraction of friction work converted to heat");
  params.addParam<Real>("center_x", 0.0, "Spindle centre x coordinate (m)");
  params.addParam<Real>("center_y", 0.05, "Spindle centre y coordinate (m)");
  return params;
}

ContactFrictionHeatFlux::ContactFrictionHeatFlux(const InputParameters & parameters)
  : IntegratedBC(parameters),
    _temperature(coupledValue("temperature")),
    _contact_pressure(coupledValue("contact_pressure")),
    _material_props(getUserObject<AA5083ThermalProperties>("material_props")),
    _omega(2.0 * libMesh::pi * getParam<Real>("rpm") / 60.0),
    _heat_partition(getParam<Real>("heat_partition")),
    _efficiency(getParam<Real>("efficiency")),
    _center_x(getParam<Real>("center_x")),
    _center_y(getParam<Real>("center_y"))
{
}

Real
ContactFrictionHeatFlux::computeQpResidual()
{
  const Real radius = std::hypot(_q_point[_qp](0) - _center_x, _q_point[_qp](1) - _center_y);
  const Real pressure = std::max(0.0, _contact_pressure[_qp]);
  const Real flux = _heat_partition * _efficiency * _material_props.mu(_temperature[_qp]) *
                    pressure * _omega * radius;
  // A positive source adds heat to the temperature equation.
  return -_test[_i][_qp] * flux;
}
