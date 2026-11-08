#pragma once
#include "ADNodalBC.h"

/** Material surface motion with the same BE/BDF2 derivative as the ALE kernels. */
class AFSDDisplaceBoundaryBC : public ADNodalBC
{
public:
  static InputParameters validParams();
  AFSDDisplaceBoundaryBC(const InputParameters & parameters);
protected:
  ADReal computeQpResidual() override;
  const Moose::Functor<ADRealVectorValue> & _velocity;
  const Real & _nodal_dot;
  const VariableValue & _dot_coefficient;
  const unsigned short _component;
  const SubdomainID _subdomain;
};
