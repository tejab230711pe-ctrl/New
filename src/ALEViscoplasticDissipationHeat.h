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

  const ADMaterialProperty<Real> & _heat;
};
