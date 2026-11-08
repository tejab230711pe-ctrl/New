#include "PenaltyContactHeatPowerAux.h"
#include "PenaltySlipDissipation.h"
#include "PenetrationLocator.h"
#include "PenetrationInfo.h"

registerMooseObject("RotatingDiskDepositionApp", PenaltyContactHeatPowerAux);

InputParameters
PenaltyContactHeatPowerAux::validParams()
{
  auto params = PenetrationAux::validParams();
  params.addRequiredRangeCheckedParam<Real>("contact_stiffness", "contact_stiffness > 0",
      "Same N/m stiffness as Contact penalty; only fixed, unnormalized penalty is supported");
  params.addRangeCheckedParam<Real>("efficiency", 0.9, "efficiency >= 0 & efficiency <= 1",
                                    "Irreversible friction work converted to heat");
  params.addParam<bool>("report_negative", false,
                       "Report the magnitude of discarded negative power instead of heating");
  params.set<ExecFlagEnum>("execute_on") = EXEC_NONLINEAR;
  params.addClassDescription("Nodal watts from solved Coulomb penalty slip, excluding reversible "
                            "tangential spring motion; use with CoupledForceNodalKernel");
  return params;
}

PenaltyContactHeatPowerAux::PenaltyContactHeatPowerAux(const InputParameters & parameters)
  : PenetrationAux(parameters),
    _stiffness(getParam<Real>("contact_stiffness")),
    _efficiency(getParam<Real>("efficiency")),
    _report_negative(getParam<bool>("report_negative"))
{
  if (!_nodal)
    paramError("variable", "Contact heat power requires a nodal auxiliary variable");
  if (boundaryNames().size() != 1)
    paramError("boundary", "Use one secondary contact boundary per heat-power object");
}

Real
PenaltyContactHeatPowerAux::computeValue()
{
  const auto it = _penetration_locator._penetration_info.find(_current_node->id());
  if (_dt <= 0 || it == _penetration_locator._penetration_info.end() || !it->second ||
      !it->second->isCaptured())
    return 0.;
  const auto & info = *it->second;
  const auto array = [](const auto & v) { return std::array<double, 3>{v(0), v(1), v(2)}; };
  const Real power = _efficiency / _dt *
      penaltySlipDissipation(array(info._contact_force), array(info._contact_force_old),
                             array(info._incremental_slip), array(info._normal), _stiffness);
  return _report_negative ? std::max(0., -power) : std::max(0., power);
}
