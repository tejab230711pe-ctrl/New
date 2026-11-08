#include "AFSDContactGapFlux.h"
registerMooseObject("RotatingDiskDepositionApp", AFSDContactGapFlux);

InputParameters
AFSDContactGapFlux::validParams()
{
  InputParameters params = GapFluxModelBase::validParams();
  params.addClassDescription("Constant conductance on overlapping mortar contact surfaces; zero across an open gap.");
  params.addRequiredCoupledVar("temperature", "Temperature on both contact surfaces");
  params.addRequiredRangeCheckedParam<Real>("conductance", "conductance > 0", "Closed-contact conductance in W/(m^2 K)");
  return params;
}

AFSDContactGapFlux::AFSDContactGapFlux(const InputParameters & parameters)
  : GapFluxModelBase(parameters),
    _conductance(getParam<Real>("conductance")),
    _primary_T(adCoupledNeighborValue("temperature")),
    _secondary_T(adCoupledValue("temperature"))
{
}

ADReal
AFSDContactGapFlux::computeFlux() const
{
  if (_gap_width > 0)
    return 0.;
  return _conductance * (_primary_T[_qp] - _secondary_T[_qp]);
}
