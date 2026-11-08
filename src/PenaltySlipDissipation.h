#pragma once
#include <algorithm>
#include <array>

// Return-map dissipation for unnormalized, fixed-stiffness Coulomb penalty
// contact. Forces use MOOSE's internal contact-force sign convention.
// Subtract the recoverable tangential spring increment before computing heat.
inline double
penaltySlipDissipation(const std::array<double, 3> & force,
                       const std::array<double, 3> & old_force,
                       const std::array<double, 3> & slip,
                       const std::array<double, 3> & normal,
                       double stiffness)
{
  double fn = 0., old_fn = 0., sn = 0.;
  for (unsigned i = 0; i < 3; ++i)
  {
    fn += force[i] * normal[i];
    old_fn += old_force[i] * normal[i];
    sn += slip[i] * normal[i];
  }
  double work = 0.;
  for (unsigned i = 0; i < 3; ++i)
  {
    const double t = force[i] - fn * normal[i];
    const double old_t = old_force[i] - old_fn * normal[i];
    const double plastic_slip = slip[i] - sn * normal[i] - (t - old_t) / stiffness;
    work += t * plastic_slip;
  }
  return work;
}
