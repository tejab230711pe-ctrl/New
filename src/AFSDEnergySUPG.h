#pragma once
#include "INSADEnergySUPG.h"

/** Include viscoplastic heating in the same strong residual used by SUPG. */
class AFSDEnergySUPG : public INSADEnergySUPG
{
public:
  static InputParameters validParams();
  AFSDEnergySUPG(const InputParameters & parameters);
protected:
  ADReal precomputeQpStrongResidual() override;
  const ADMaterialProperty<Real> & _heat;
};
