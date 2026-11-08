#include "PenaltySlipDissipation.h"
#include <cassert>
#include <cmath>
#include <iostream>

int main()
{
  using V = std::array<double, 3>;
  const V n{0, 0, 1}, zero{0, 0, 0};
  const auto check = [](double actual, double expected) {
    assert(std::abs(actual - expected) < 1.e-12);
  };
  // Pure normal approach generates no tangential dissipation.
  check(penaltySlipDissipation(V{0, 0, -10}, zero, V{0, 0, -.1}, n, 100), 0);
  // Sticking spring loading and unloading recover energy, producing no heat.
  check(penaltySlipDissipation(V{2, 0, -10}, zero, V{.02, 0, 0}, n, 100), 0);
  check(penaltySlipDissipation(zero, V{2, 0, -10}, V{-.02, 0, 0}, n, 100), 0);
  // Trial force 5 N, returned force 3 N: plastic slip .02 m, heat work .06 J.
  check(penaltySlipDissipation(V{3, 0, -10}, zero, V{.05, 0, 0}, n, 100), .06);
  // Continued sliding and reversal include the spring reload correctly.
  check(penaltySlipDissipation(V{3, 0, -10}, V{3, 0, -10}, V{.02, 0, 0}, n, 100), .06);
  check(penaltySlipDissipation(V{-3, 0, -10}, V{3, 0, -10}, V{-.08, 0, 0}, n, 100), .06);
  // Rotate the same problem: dissipation must not depend on the normal axis.
  check(penaltySlipDissipation(V{-10, 3, 0}, zero, V{0, .05, 0}, V{1, 0, 0}, 100), .06);
  std::cout << "PASS penalty slip: sticking, unloading, sliding, reversal, rotated normal\n";
}
