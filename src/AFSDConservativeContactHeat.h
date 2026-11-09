#pragma once
#include "ADMortarConstraint.h"

/** Finite closed-contact conductance integrated once on a shared mortar mesh. */
class AFSDConservativeContactHeat : public ADMortarConstraint
{
public:
  static InputParameters validParams();
  AFSDConservativeContactHeat(const InputParameters & parameters);
protected:
  ADReal computeQpResidual(Moose::MortarType type) override;
  const Real _conductance;
};
