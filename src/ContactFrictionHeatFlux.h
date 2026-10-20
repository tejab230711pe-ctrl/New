#pragma once

#include "IntegratedBC.h"

class AA5083ThermalProperties;
class Function;

/**
 * Frictional heat flux at the rotating rod/workpiece contact interface.
 *
 * The contact action supplies contact_pressure from the solved mechanical
 * contact state.  This BC converts that pressure to a surface heat flux
 * q = eta * mu(T) * p * omega * r.  Apply it to the secondary (rod) contact
 * surface; its heat_partition selects the tool-side share of the dissipation.
 */
class ContactFrictionHeatFlux : public IntegratedBC
{
public:
  static InputParameters validParams();
  ContactFrictionHeatFlux(const InputParameters & parameters);

protected:
  Real computeQpResidual() override;

private:
  const VariableValue & _temperature;
  const VariableValue & _contact_pressure;
  const AA5083ThermalProperties & _material_props;
  const Real _omega;
  const Real _heat_partition;
  const Real _efficiency;
  const Real _center_x;
  const Function & _tool_center_y;
};
