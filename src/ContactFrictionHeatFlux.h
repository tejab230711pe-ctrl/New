#pragma once

#include "IntegratedBC.h"

class AA5083ThermalProperties;
class Function;

/**
 * Frictional heat flux at the rotating rod/workpiece contact interface.
 *
 * The contact action supplies contact_pressure from the solved mechanical
 * contact state.  This BC converts that pressure to a surface heat flux
 * q = eta * mu_contact * p * omega * r.  mu_contact is deliberately the
 * same coefficient used by the Coulomb contact constraint, so the thermal
 * source exactly represents that solved mechanical dissipation.
 */
class ContactFrictionHeatFlux : public IntegratedBC
{
public:
  static InputParameters validParams();
  ContactFrictionHeatFlux(const InputParameters & parameters);

protected:
  Real computeQpResidual() override;

private:
  const VariableValue & _contact_pressure;
  const Real _omega;
  const Real _friction_coefficient;
  const Real _heat_partition;
  const Real _efficiency;
  const Real _center_x;
  const Function & _tool_center_y;
};
