#pragma once

#include "SolutionIC.h"

#include <set>

/**
 * Exodus initial condition for a remeshed AFSD stage.
 *
 * A continuous field variable is projected over all current-mesh elements by
 * MOOSE, including fresh deposit elements that intentionally did not exist in
 * the predecessor Exodus mesh.  SolutionIC would abort for those points.
 * This variant samples the predecessor only on explicitly named inherited
 * blocks and supplies a physical virgin-state value everywhere else.
 */
class RemeshSolutionIC : public SolutionIC
{
public:
  static InputParameters validParams();

  RemeshSolutionIC(const InputParameters & parameters);

  void initialSetup() override;

  Real value(const Point & p) override;

private:
  /// Current-mesh blocks which existed in the predecessor result.
  const std::vector<SubdomainName> _transfer_block_names;
  std::set<SubdomainID> _transfer_block_ids;

  /// Value for genuinely new material that has no predecessor state.
  const Real _outside_value;
};
