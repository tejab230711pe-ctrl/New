#include "RemeshTemperatureDependentHardeningStressUpdate.h"

#include "Function.h"

#include <algorithm>

registerMooseObject("RotatingDiskDepositionApp", RemeshTemperatureDependentHardeningStressUpdate);

InputParameters
RemeshTemperatureDependentHardeningStressUpdate::validParams()
{
  InputParameters params = TemperatureDependentHardeningStressUpdate::validParams();
  params.addClassDescription(
      "AA5083 temperature-dependent J2 plasticity with explicit Exodus-to-remesh state transfer.");
  params.addParam<FunctionName>(
      "initial_effective_plastic_strain",
      "Optional SolutionFunction for effective_plastic_strain from the preceding remesh stage.");
  params.addParam<std::vector<FunctionName>>(
      "initial_plastic_strain_functions",
      "Optional six SolutionFunctions for plastic strain in xx yy zz xy yz zx order.");
  return params;
}

RemeshTemperatureDependentHardeningStressUpdate::RemeshTemperatureDependentHardeningStressUpdate(
    const InputParameters & parameters)
  : TemperatureDependentHardeningStressUpdate(parameters),
    _initial_effective_plastic_strain(nullptr),
    _initial_plastic_strain{{nullptr, nullptr, nullptr, nullptr, nullptr, nullptr}}
{
  if (isParamSetByUser("initial_effective_plastic_strain"))
    _initial_effective_plastic_strain = &getFunction("initial_effective_plastic_strain");

  const std::vector<FunctionName> names =
      isParamSetByUser("initial_plastic_strain_functions")
          ? getParam<std::vector<FunctionName>>("initial_plastic_strain_functions")
          : std::vector<FunctionName>{};
  if (!names.empty() && names.size() != _initial_plastic_strain.size())
    paramError("initial_plastic_strain_functions",
               "Exactly six functions are required, ordered xx yy zz xy yz zx.");

  for (const auto i : index_range(names))
    _initial_plastic_strain[i] = &getFunctionByName(names[i]);
}

void
RemeshTemperatureDependentHardeningStressUpdate::initQpStatefulProperties()
{
  TemperatureDependentHardeningStressUpdate::initQpStatefulProperties();

  // Stage one has no predecessor and naturally remains at the virgin state.
  if (!_initial_effective_plastic_strain)
    return;

  const Point & point = _q_point[_qp];
  const Real effective_strain =
      std::max(0.0, _initial_effective_plastic_strain->value(_t, point));

  _effective_inelastic_strain[_qp] = effective_strain;

  // Reconstruct the tensorial state so the next return-mapping increment is
  // based on the transferred plastic deformation rather than a virgin tensor.
  if (_initial_plastic_strain[0])
  {
    RankTwoTensor & plastic_strain = _plastic_strain[_qp];
    plastic_strain(0, 0) = _initial_plastic_strain[0]->value(_t, point);
    plastic_strain(1, 1) = _initial_plastic_strain[1]->value(_t, point);
    plastic_strain(2, 2) = _initial_plastic_strain[2]->value(_t, point);
    plastic_strain(0, 1) = plastic_strain(1, 0) = _initial_plastic_strain[3]->value(_t, point);
    plastic_strain(1, 2) = plastic_strain(2, 1) = _initial_plastic_strain[4]->value(_t, point);
    plastic_strain(0, 2) = plastic_strain(2, 0) = _initial_plastic_strain[5]->value(_t, point);
  }

  // hardening_variable is the temperature-dependent stress increment used by
  // the next radial return.  Recreate it from the imported effective strain.
  initializeHardeningFunctions();
  computeYieldStress(RankFourTensor());
  _hardening_variable[_qp] = computeHardeningValue(effective_strain);
}
