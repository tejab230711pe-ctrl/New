#include "AA5083ALEViscoplasticMaterial.h"

#include "metaphysicl/raw_type.h"

#include <cmath>

registerMooseObject("RotatingDiskDepositionApp", AA5083ALEViscoplasticMaterial);

InputParameters
AA5083ALEViscoplasticMaterial::validParams()
{
  InputParameters params = Material::validParams();
  params.addClassDescription("Regularised AA5083 hyperbolic-sine viscoplastic material for a "
                             "sharp-interface ALE flow region.");
  params.addRequiredCoupledVar("temperature", "Temperature in kelvin");
  params.addRequiredCoupledVar("velocity", "ALE material velocity");
  params.addRangeCheckedParam<Real>("taylor_quinney", 0.90,
                                   "taylor_quinney >= 0 & taylor_quinney <= 1",
                                   "Fraction of viscous dissipation converted to heat");
  params.addParam<Real>("activation_energy", 174700.0, "Hot-deformation activation energy (J/mol)");
  params.addParam<Real>("sinh_alpha_per_mpa", 0.015, "Hyperbolic-sine stress coefficient (1/MPa)");
  params.addParam<Real>("stress_exponent", 5.23, "Hyperbolic-sine stress exponent");
  params.addParam<Real>("log_preexponential", 24.98, "Natural log of hot-deformation prefactor");
  params.addParam<Real>("gas_constant", 8.314, "Universal gas constant (J/mol/K)");
  params.addParam<Real>("strain_rate_regularization", 1.e-3, "Minimum equivalent strain rate (1/s)");
  params.addParam<Real>("mu_min", 1.e4, "Lower apparent-viscosity bound (Pa s)");
  params.addParam<Real>("mu_max", 1.e10, "Upper apparent-viscosity bound (Pa s)");
  params.addParam<Real>("plastic_start_temperature", 623.15, "Plasticisation onset (K)");
  params.addParam<Real>("plastic_end_temperature", 798.15, "Fully plasticised temperature (K)");
  return params;
}

AA5083ALEViscoplasticMaterial::AA5083ALEViscoplasticMaterial(const InputParameters & parameters)
  : Material(parameters),
    _temperature(adCoupledValue("temperature")),
    _grad_temperature(adCoupledGradient("temperature")),
    _grad_velocity(adCoupledVectorGradient("velocity")),
    _rho(declareADProperty<Real>("rho")),
    _cp(declareADProperty<Real>("cp")),
    _k(declareADProperty<Real>("k")),
    _mu(declareADProperty<Real>("mu")),
    _grad_k(declareADProperty<RealVectorValue>("grad_k")),
    _grad_mu_temperature(declareADProperty<RealVectorValue>("grad_mu_temperature")),
    _heat(declareADProperty<Real>("viscoplastic_heat")),
    _plastic_fraction(declareADProperty<Real>("plastic_fraction")),
    _effective_strain_rate(declareADProperty<Real>("effective_strain_rate")),
    _taylor_quinney(getParam<Real>("taylor_quinney")),
    _activation_energy(getParam<Real>("activation_energy")),
    _sinh_alpha_per_pa(getParam<Real>("sinh_alpha_per_mpa") * 1.e-6),
    _stress_exponent(getParam<Real>("stress_exponent")),
    _log_preexponential(getParam<Real>("log_preexponential")),
    _gas_constant(getParam<Real>("gas_constant")),
    _strain_rate_regularization(getParam<Real>("strain_rate_regularization")),
    _mu_min(getParam<Real>("mu_min")),
    _mu_max(getParam<Real>("mu_max")),
    _plastic_start_temperature(getParam<Real>("plastic_start_temperature")),
    _plastic_end_temperature(getParam<Real>("plastic_end_temperature"))
{
  if (_plastic_end_temperature <= _plastic_start_temperature)
    paramError("plastic_end_temperature", "must exceed plastic_start_temperature");
  if (_mu_min <= 0.0 || _mu_max < _mu_min || _strain_rate_regularization <= 0.0)
    paramError("mu_min", "viscosity bounds and strain-rate regularisation must be positive");
}

void
AA5083ALEViscoplasticMaterial::computeQpProperties()
{
  using std::asinh;
  using std::exp;
  using std::sqrt;
  using std::log;

  const ADReal T = _temperature[_qp];
  const ADReal theta = (T - _plastic_start_temperature) /
                       (_plastic_end_temperature - _plastic_start_temperature);
  // Smoothstep, clamped using raw values only at the two physically inactive ends.
  const Real theta_raw = MetaPhysicL::raw_value(theta);
  if (theta_raw <= 0.0)
    _plastic_fraction[_qp] = 0.0;
  else if (theta_raw >= 1.0)
    _plastic_fraction[_qp] = 1.0;
  else
    _plastic_fraction[_qp] = theta * theta * (3.0 - 2.0 * theta);

  const ADRealTensorValue D = 0.5 * (_grad_velocity[_qp] + _grad_velocity[_qp].transpose());
  // J2 equivalent rate: sqrt(2/3 D:D) for incompressible flow. This
  // convention is required by mu = sigma_equivalent / (3 * rate).
  const ADReal rate = sqrt((2.0 / 3.0) * D.contract(D) +
                           _strain_rate_regularization * _strain_rate_regularization);
  _effective_strain_rate[_qp] = rate;

  // ln(Z) = ln(edot) + Q/(R T), sigma = asinh((Z/A)^(1/n))/alpha.
  // The apparent viscosity sigma/(3 edot) is bounded to regularise the cold
  // edge of the flow domain and preserve a solvable ALE system.
  const ADReal log_z = log(rate) + _activation_energy / (_gas_constant * T);
  const ADReal argument = exp((log_z - _log_preexponential) / _stress_exponent);
  const ADReal unbounded_mu = asinh(argument) / (_sinh_alpha_per_pa * 3.0 * rate);
  const Real raw_mu = MetaPhysicL::raw_value(unbounded_mu);
  _mu[_qp] = raw_mu < _mu_min ? _mu_min : (raw_mu > _mu_max ? _mu_max : unbounded_mu);

  // On affine FIRST-order tetrahedra D and its invariant are spatially
  // constant. The complete within-element viscosity gradient is then this
  // temperature term. Higher-order/curved elements additionally need grad(rate).
  if (raw_mu < _mu_min || raw_mu > _mu_max)
    _grad_mu_temperature[_qp] = ADRealVectorValue();
  else
  {
    const ADReal dmu_dT = -argument / sqrt(1.0 + argument * argument) *
        _activation_energy / (_stress_exponent * _gas_constant * T * T *
                              _sinh_alpha_per_pa * 3.0 * rate);
    _grad_mu_temperature[_qp] = dmu_dT * _grad_temperature[_qp];
  }

  _heat[_qp] = 2.0 * _taylor_quinney * _mu[_qp] * D.contract(D);

  // AA5083 solid-state thermal properties over the intended AFSD range.
  _rho[_qp] = 2650.0;
  _cp[_qp] = 900.0 + 0.45 * (T - 293.15);
  _k[_qp] = 122.0 + 0.08 * (T - 293.15);
  _grad_k[_qp] = 0.08 * _grad_temperature[_qp];
}
