#include "MushyFraction.h"
#include "AA5083ThermalProperties.h"
#include "MooseError.h"

registerMooseObject("RotatingDiskDepositionApp", MushyFraction);

InputParameters
MushyFraction::validParams()
{
  InputParameters params = Material::validParams();
  params.addRequiredCoupledVar("temperature", "Temperature variable (K)");
  params.addRequiredParam<UserObjectName>("material_props", "UserObject supplying base material properties");
  // Constants (same as in original script)
  params.addParam<Real>("Tsol", 864.15, "Solidus temperature (K)");
  params.addParam<Real>("Tfraction_low_factor", 0.6, "Fraction for low plastic temperature");
  params.addParam<Real>("Tfraction_high_factor", 0.9, "Fraction for high plastic temperature");
  params.addParam<Real>("Lf", 387000.0, "Latent heat of fusion (J/kg)");
  params.addParam<Real>("k_liquid", 177.2, "Thermal conductivity of liquid phase (W/m/K)");
  return params;
}

MushyFraction::MushyFraction(const InputParameters & parameters)
  : Material(parameters),
    _temperature(coupledValue("temperature")),
    _mat_props(getUserObject<AA5083ThermalProperties>("material_props")),
    _mushy_fraction(declareProperty<Real>("mushy_fraction")),
    _dmush_dT(declareProperty<Real>("dmush_dT")),
    _cp_eff(declareProperty<Real>("cp_eff")),
    _k_eff(declareProperty<Real>("k_eff")),
    _Tsol(getParam<Real>("Tsol")),
    _Lf(getParam<Real>("Lf")),
    _k_liquid(getParam<Real>("k_liquid"))
{
  const Real Tair = 293.15;
  const Real delta = _Tsol - Tair;
  _TplasticLow  = 273.15 + getParam<Real>("Tfraction_low_factor") * delta;
  _TplasticHigh = 273.15 + getParam<Real>("Tfraction_high_factor") * delta;
  _dTmush = _TplasticHigh - _TplasticLow;
}

void
MushyFraction::computeProperties()
{
  for (std::size_t qp = 0; qp < _q_point.size(); ++qp)
  {
    const Real T = _temperature[qp];

    // Compute mushy fraction f(T)
    Real f = 0.0;
    Real df_dT = 0.0;

    if (T <= _TplasticLow)
    {
      f = 0.0;
      df_dT = 0.0;
    }
    else if (T < _TplasticHigh)
    {
      f = (T - _TplasticLow) / _dTmush;
      df_dT = 1.0 / _dTmush;
    }
    else
    {
      f = 1.0;
      df_dT = 0.0;
    }

    _mushy_fraction[qp] = f;
    _dmush_dT[qp] = df_dT;

    // Effective heat capacity cp_eff = cp(T) + Lf * df/dT
    const Real cp_base = _mat_props.cp(T);
    _cp_eff[qp] = cp_base + _Lf * df_dT;

    // Effective thermal conductivity k_eff = (1-f)*k(T) + f*k_liquid
    const Real k_base = _mat_props.k(T);
    _k_eff[qp] = (1.0 - f) * k_base + f * _k_liquid;
  }
}
