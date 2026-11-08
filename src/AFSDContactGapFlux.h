#pragma once
#include "GapFluxModelBase.h"

/** Constant contact conductance, assembled conservatively by MOOSE mortar. */
class AFSDContactGapFlux : public GapFluxModelBase
{
public:
  static InputParameters validParams();
  AFSDContactGapFlux(const InputParameters & parameters);
  ADReal computeFlux() const override;
protected:
  const Real _conductance;
  const ADVariableValue & _primary_T;
  const ADVariableValue & _secondary_T;
};
