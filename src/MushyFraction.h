#pragma once

#include "Material.h"
#include "AA5083ThermalProperties.h"
#include "Moose.h"

/**
 * MushyFraction material
 * ----------------------
 * Computes temperature-dependent mushy-zone fraction f(T) and its derivative
 * df/dT, as well as the effective specific heat and thermal conductivity used
 * in the heat-conduction equation:
 *   f(T)   = 0                               if T <= TplasticLow
 *          = (T - TplasticLow) / dTmush      if TplasticLow < T < TplasticHigh
 *          = 1                               if T >= TplasticHigh
 *   df/dT = 0 outside the mushy interval, otherwise 1/dTmush
 *   cp_eff = cp(T) + Lf * df/dT
 *   k_eff  = (1-f) * k(T) + f * k_liquid
 */
class MushyFraction : public Material
{
public:
  static InputParameters validParams();

  MushyFraction(const InputParameters & parameters);

protected:
  virtual void computeProperties() override;

  // Coupled temperature variable (in Kelvin)
  const VariableValue & _temperature;

  // UserObject that supplies base material properties
  const AA5083ThermalProperties & _mat_props;

  // Material property handles
  MaterialProperty<Real> & _mushy_fraction;
  MaterialProperty<Real> & _dmush_dT;
  MaterialProperty<Real> & _cp_eff;
  MaterialProperty<Real> & _k_eff;

  // Constants
  Real _Tsol;
  Real _TplasticLow;
  Real _TplasticHigh;
  Real _dTmush;
  Real _Lf;          // latent heat (J/kg)
  Real _k_liquid;    // conductivity of liquid phase (W/m·K)
};
