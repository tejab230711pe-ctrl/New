#pragma once

#include "GeneralUserObject.h"
#include "MaterialProperty.h"
#include "Moose.h"

/**
 * AA5083ThermalProperties
 * -----------------------
 * GeneralUserObject supplying temperature-dependent material properties
 * (density, conductivity, specific heat, yield stress, friction coefficient).
 */
class AA5083ThermalProperties : public GeneralUserObject
{
public:
  static InputParameters validParams();

  AA5083ThermalProperties(const InputParameters & parameters);

  virtual void initialize() override {}
  virtual void execute() override {}
  virtual void finalize() override {}

  // Material property getters
  Real rho(Real T) const;
  Real k(Real T) const;
  Real cp(Real T) const;
  Real yieldStress(Real T) const;
  Real mu(Real T) const;

protected:
  // Linear interpolation helper
  Real interp(Real T, const std::vector<Real> & temps,
              const std::vector<Real> & values) const;

  std::vector<Real> _temps;
  std::vector<Real> _rho_vals;
  std::vector<Real> _k_vals;
  std::vector<Real> _cp_vals;
  std::vector<Real> _yield_vals;
  std::vector<Real> _mu_vals;

  const Real _Tliq = 911.15; // K
};
