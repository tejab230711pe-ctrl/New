#pragma once

#include "TorqueReaction.h"

/** Signed resultant torque about a translating spindle axis. */
class MovingAxisTorqueReaction : public TorqueReaction
{
public:
  static InputParameters validParams();
  MovingAxisTorqueReaction(const InputParameters & parameters);
  void execute() override;

protected:
  const Function & _center_y;
};
