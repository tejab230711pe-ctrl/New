#include "RemeshSolutionIC.h"

#include "MooseMesh.h"
#include "SystemBase.h"

registerMooseObject("RotatingDiskDepositionApp", RemeshSolutionIC);

InputParameters
RemeshSolutionIC::validParams()
{
  InputParameters params = SolutionIC::validParams();
  params.addRequiredParam<std::vector<SubdomainName>>(
      "transfer_blocks",
      "Current-mesh blocks inherited from the predecessor Exodus solution.");
  params.addRequiredParam<Real>(
      "outside_value",
      "Initial value for points in new material absent from the predecessor mesh.");
  params.addClassDescription(
      "Transfers a remeshed field only on inherited blocks and initializes fresh material safely.");
  return params;
}

RemeshSolutionIC::RemeshSolutionIC(const InputParameters & parameters)
  : SolutionIC(parameters),
    _transfer_block_names(getParam<std::vector<SubdomainName>>("transfer_blocks")),
    _outside_value(getParam<Real>("outside_value"))
{
}

void
RemeshSolutionIC::initialSetup()
{
  SolutionIC::initialSetup();

  for (const auto & block : _transfer_block_names)
    _transfer_block_ids.insert(_sys.mesh().getSubdomainID(block));
}

Real
RemeshSolutionIC::value(const Point & p)
{
  // InitialCondition projection visits shared nodes while processing every
  // adjacent element.  The element context, unlike point coordinates alone,
  // unambiguously distinguishes an inherited bead/plate from newly born bead
  // material at the same interface.
  if (!_current_elem || !_transfer_block_ids.count(_current_elem->subdomain_id()))
    return _outside_value;

  return SolutionIC::value(p);
}
