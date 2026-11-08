#pragma once
#include "INSADStabilized3Eqn.h"

/** Add variable-viscosity stress divergence for the affine P1 tetrahedral flow. */
class AFSDStabilized3Eqn : public INSADStabilized3Eqn
{
public:
  static InputParameters validParams();
  AFSDStabilized3Eqn(const InputParameters & parameters);
protected:
  void computeQpProperties() override;
  const ADMaterialProperty<RealVectorValue> & _grad_mu_temperature;
};
