#pragma once

#include "ADKernel.h"

/** Adds q = 2 mu D:D to the ALE energy equation. */
class ALEViscoplasticDissipationHeat : public ADKernel
{
public:
  static InputParameters validParams();
  ALEViscoplasticDissipationHeat(const InputParameters & parameters);

protected:
  ADReal computeQpResidual() override;

  const ADVectorVariableGradient & _grad_velocity;
  const ADMaterialProperty<Real> & _mu;
  const Real _taylor_quinney;
};
