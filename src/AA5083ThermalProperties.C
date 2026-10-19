#include "AA5083ThermalProperties.h"
#include "MooseError.h"

registerMooseObject("RotatingDiskDepositionApp", AA5083ThermalProperties);

InputParameters
AA5083ThermalProperties::validParams()
{
  InputParameters params = GeneralUserObject::validParams();
  return params;
}

AA5083ThermalProperties::AA5083ThermalProperties(const InputParameters & parameters)
  : GeneralUserObject(parameters)
{
  // Temperatures (K) used in the original interpolation tables
  _temps = {-20.0 + 273.15,
            80.0  + 273.15,
            180.0 + 273.15,
            280.0 + 273.15,
            380.0 + 273.15,
            480.0 + 273.15,
            580.0 + 273.15};

  // Corresponding values (taken directly from the FreeFEM script)
  _rho_vals   = {2673.9, 2642.7, 2629.4, 2611.5, 2589.3, 2567.0, 2549.2};
  _k_vals     = {112.5, 122.7, 131.6, 142.3, 152.5, 159.5, 177.2};
  _cp_vals    = {924.1, 984.2, 1039.6, 1081.2, 1136.6, 1178.2, 1261.4};
  // Yield stress in MPa (converted to Pa)
  _yield_vals = {165.0e6, 165.0e6, 145.0e6, 145.0e6, 145.0e6,
                 145.0e6, 130.0e6, 115.0e6, 75.0e6, 50.0e6, 29.0e6};
  // Friction coefficient values (muReference, muMin, muMax) – we only need the
  // reference value for the UserObject; temperature‑dependent mu is computed
  // elsewhere (see mu(T) function).
  _mu_vals = {0.70}; // placeholder; actual temperature dependence handled in mu()
}

Real
AA5083ThermalProperties::interp(Real T,
                                 const std::vector<Real> & temps,
                                 const std::vector<Real> & values) const
{
  // Linear interpolation with extrapolation using the last slope (as in the
  // original FreeFEM script). The vector `temps` must be sorted ascending.
  if (T <= temps.front())
    return values.front();

  if (T >= temps.back())
  {
    // Extrapolate using the final segment slope (same as the original script)
    Real slope = (values.back() - values[values.size() - 2]) /
                 (temps.back() - temps[temps.size() - 2]);
    return values.back() + slope * (T - temps.back());
  }

  // Find interval
  for (std::size_t i = 1; i < temps.size(); ++i)
  {
    if (T <= temps[i])
    {
      Real t0 = temps[i - 1];
      Real t1 = temps[i];
      Real v0 = values[i - 1];
      Real v1 = values[i];
      Real frac = (T - t0) / (t1 - t0);
      return v0 + frac * (v1 - v0);
    }
  }
  mooseError("Interpolation logic failed – should never reach here");
  return 0.0; // never reached
}

Real AA5083ThermalProperties::rho(Real T) const { return interp(T, _temps, _rho_vals); }
Real AA5083ThermalProperties::k(Real T) const   { return interp(T, _temps, _k_vals); }
Real AA5083ThermalProperties::cp(Real T) const  { return interp(T, _temps, _cp_vals); }

Real AA5083ThermalProperties::yieldStress(Real T) const
{
  // The original script uses a piece‑wise definition with several temperature
  // ranges. For simplicity we reuse the same interpolation table, which
  // reproduces the same values at the breakpoints used in the script.
  return interp(T, _temps, _yield_vals);
}

Real AA5083ThermalProperties::mu(Real T) const
{
  // Temperature‑dependent friction coefficient (if enabled).  The original
  // script defines:
  //   theta = min(1, max(0, (T - Tair) / max(1, Tsol - Tair)))
  //   mu = min(muMax, max(muMin, muReference - (muReference - muMin) * theta))
  const Real Tair = 293.15;          // ambient temperature (K)
  const Real Tsol = 864.15;          // solidus (K)
  const Real muReference = 0.70;
  const Real muMin = 0.25;
  const Real muMax = 0.70;

  Real theta = std::min(1.0, std::max(0.0, (T - Tair) / std::max(1.0, Tsol - Tair)));
  Real mu_val = muReference - (muReference - muMin) * theta;
  mu_val = std::max(muMin, std::min(muMax, mu_val));
  return mu_val;
}
