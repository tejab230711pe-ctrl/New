#pragma once

#include "Kernel.h"
#include "RankTwoTensor.h"

/**
 * Converts only non-negative plastic dissipation to heat.
 *
 * The standard PlasticHeatEnergy kernel assumes a sign-consistent plastic
 * work increment.  During penalty-contact re-zoning a transient projected
 * plastic tensor may instead give negative work, which is unphysical as a
 * heat source and can cool AA5083 below ambient.  This kernel enforces the
 * thermodynamic requirement D_p = max(0, sigma:Delta(eps_p)/dt).
 */
class NonnegativePlasticHeatEnergy : public Kernel
{
public:
  static InputParameters validParams();
  NonnegativePlasticHeatEnergy(const InputParameters & parameters);

protected:
  Real computeQpResidual() override;
  Real computeQpJacobian() override;
  Real computeQpOffDiagJacobian(unsigned int jvar) override;

private:
  const Real _coeff;
  const MaterialProperty<Real> & _plastic_heat;
  const MaterialProperty<RankTwoTensor> & _dplastic_heat_dstrain;
  std::vector<unsigned int> _disp_var;
};
