#include "MovingAxisTorqueReaction.h"
#include "Function.h"

registerMooseObject("RotatingDiskDepositionApp", MovingAxisTorqueReaction);

InputParameters
MovingAxisTorqueReaction::validParams()
{
  InputParameters params = TorqueReaction::validParams();
  params.addRequiredParam<FunctionName>("center_y", "Absolute spindle-axis Y coordinate versus time");
  params.addClassDescription("Signed sum of reaction moments about a translating axis, evaluated "
                             "on the displaced mesh. Opposing moments cancel.");
  return params;
}

MovingAxisTorqueReaction::MovingAxisTorqueReaction(const InputParameters & parameters)
  : TorqueReaction(parameters), _center_y(getFunction("center_y"))
{
  if (_direction_vector.norm() == 0.0)
    paramError("direction_vector", "must be nonzero");
  if (_nrt != 2 && _nrt != 3)
    paramError("reaction_force_variables", "requires two or three reaction components");
}

void
MovingAxisTorqueReaction::execute()
{
  Point center = _axis_origin;
  center(1) = _center_y.value(_t, *_current_node);
  const Point arm = (*_current_node) - center;
  const Point force((*_react[0])[_qp], (*_react[1])[_qp],
                    _nrt == 3 ? (*_react[2])[_qp] : 0.0);
  _sum += arm.cross(force) * _direction_vector / _direction_vector.norm();
}
