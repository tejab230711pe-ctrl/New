#pragma once

#include "Kernel.h"
#include "UserObject.h"
#include "MaterialProperty.h"
#include "Moose.h"

/**
 * NormalServo kernel
 * -----------------
 * Implements the preload spring force used during dwell and traverse phases.
 * The body force added to the momentum equation is:
 *   f = stiffness * ramp(t) * preload_force * direction
 * where:
 *   - `stiffness` is the normal‑servo base stiffness (Pa/m).
 *   - `preload_force` is the magnitude of the preload (N).
 *   - `ramp(t)` is a linear ramp from 0 to 1 over `ramp_time` seconds.
 * The direction is taken as the negative Z‑direction (consistent with the
 * original script where a positive Z is downward). The kernel assumes a scalar
 * displacement variable (e.g., Uz) is coupled.
 */
class NormalServo : public Kernel
{
public:
  static InputParameters validParams();

  NormalServo(const InputParameters & parameters);

protected:
  virtual Real computeQpResidual() override;

  // Coupled displacement variable (e.g., Uz)
  const VariableValue & _disp;

  // Parameters
  const Real _stiffness;     // normal‑servo base stiffness (Pa/m)
  const Real _preload_force; // preload magnitude (N)
  const Real _ramp_time;     // time over which preload ramps up (s)
  const Real _current_time;  // supplied by the executioner (time)
};
