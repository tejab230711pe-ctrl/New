#pragma once

#include "Material.h"

/**
 * Temperature- and rate-dependent AA5083 material for the connected ALE flow
 * domain used after the solid-contact dwell.  It supplies the MOOSE INSAD
 * properties (rho, cp, k and mu) and a smooth plasticization indicator.
 *
 * The constitutive form is a regularised hyperbolic-sine hot-deformation law.
 * It deliberately has no liquid fraction or latent heat: AFSD is treated as a
 * solid-state viscoplastic process.
 */
class AA5083ALEViscoplasticMaterial : public Material
{
public:
  static InputParameters validParams();
  AA5083ALEViscoplasticMaterial(const InputParameters & parameters);

protected:
  void computeQpProperties() override;

  const ADVariableValue & _temperature;
  const ADVariableGradient & _grad_temperature;
  const ADVectorVariableGradient & _grad_velocity;

  ADMaterialProperty<Real> & _rho;
  ADMaterialProperty<Real> & _cp;
  ADMaterialProperty<Real> & _k;
  ADMaterialProperty<Real> & _mu;
  ADMaterialProperty<RealVectorValue> & _grad_k;
  ADMaterialProperty<Real> & _heat;
  ADMaterialProperty<Real> & _plastic_fraction;
  ADMaterialProperty<Real> & _effective_strain_rate;

  const Real _taylor_quinney;
  const Real _activation_energy;
  const Real _sinh_alpha_per_pa;
  const Real _stress_exponent;
  const Real _log_preexponential;
  const Real _gas_constant;
  const Real _strain_rate_regularization;
  const Real _mu_min;
  const Real _mu_max;
  const Real _plastic_start_temperature;
  const Real _plastic_end_temperature;
};
