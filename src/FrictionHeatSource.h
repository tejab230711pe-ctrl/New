#pragma once

#include "Kernel.h"
#include "UserObject.h"
#include "MaterialProperty.h"
#include "Moose.h"

/**
 * FrictionHeatSource kernel
 * -------------------------
 * Adds the friction‑generated heat as a source term in the heat‑conduction
 * equation.  The heat rate Q (W/m^3) is calculated as:
 *   mu(T)  – temperature dependent friction coefficient (from AA5083ThermalProperties)
 *   p      – contact pressure (coupled scalar variable)
 *   R      – contact radius (parameter, usually the rod radius)
 *   rpm    – spindle speed (parameter, rev/min)
 *   omega  = 2π * rpm / 60  (rad/s)
 *   torque = mu * p * 2π * R^3 / 3
 *   power  = torque * omega
 *   Q      = heat_governor(T) * power
 *
 * The kernel contributes Q * test() to the residual of the heat equation.
 */
class FrictionHeatSource : public Kernel
{
public:
  static InputParameters validParams();

  FrictionHeatSource(const InputParameters & parameters);

protected:
  virtual Real computeQpResidual() override;

  // Coupled temperature variable (used for mu(T) and governor)
  const VariableValue & _temperature;

  // Coupled contact pressure variable (scalar field)
  const VariableValue & _contact_pressure;

  // UserObject providing material properties (including mu(T))
  const AA5083ThermalProperties & _mat_props;

  // Parameters
  const Real _radius;        // contact radius (m)
  const Real _rpm;           // revolutions per minute
  const Real _heat_governor; // scalar multiplier (0‑1) – can be a parameter or a function later
};
