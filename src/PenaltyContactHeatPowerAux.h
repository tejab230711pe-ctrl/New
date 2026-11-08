#pragma once
#include "PenetrationAux.h"

/** Nodal heat power from the irreversible slip of Coulomb penalty contact. */
class PenaltyContactHeatPowerAux : public PenetrationAux
{
public:
  static InputParameters validParams();
  PenaltyContactHeatPowerAux(const InputParameters & parameters);
protected:
  Real computeValue() override;
  const Real _stiffness;
  const Real _efficiency;
  const bool _report_negative;
};
