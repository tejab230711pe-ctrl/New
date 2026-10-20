#pragma once

#include "TemperatureDependentHardeningStressUpdate.h"

#include <array>

/**
 * Temperature-dependent J2 update that can start a remeshed AFSD stage from
 * plastic state fields sampled from the preceding Exodus file.
 *
 * The six plastic-strain functions are ordered xx, yy, zz, xy, yz, zx.  The
 * scalar effective strain is the hardening history used by the return mapping.
 */
class RemeshTemperatureDependentHardeningStressUpdate
  : public TemperatureDependentHardeningStressUpdate
{
public:
  static InputParameters validParams();

  RemeshTemperatureDependentHardeningStressUpdate(const InputParameters & parameters);

protected:
  void initQpStatefulProperties() override;

  const Function * _initial_effective_plastic_strain;
  std::array<const Function *, 6> _initial_plastic_strain;
};
