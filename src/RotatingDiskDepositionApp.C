#include "RotatingDiskDepositionApp.h"
#include "AppFactory.h"
#include "MooseSyntax.h"
#include "ModulesApp.h"

InputParameters
RotatingDiskDepositionApp::validParams()
{
  InputParameters params = MooseApp::validParams();
  params.set<bool>("automatic_automatic_scaling") = false;
  params.set<bool>("use_legacy_material_output") = false;
  params.set<bool>("use_legacy_initial_residual_evaluation_behavior") = false;
  return params;
}

RotatingDiskDepositionApp::RotatingDiskDepositionApp(const InputParameters & parameters)
  : MooseApp(parameters)
{
  RotatingDiskDepositionApp::registerAll(_factory, _action_factory, _syntax);
}

void
RotatingDiskDepositionApp::registerApps()
{
  registerApp(RotatingDiskDepositionApp);
}

void
RotatingDiskDepositionApp::registerAll(Factory & factory, ActionFactory & action_factory, Syntax & syntax)
{
  Registry::registerObjectsTo(factory, {"RotatingDiskDepositionApp"});
  Registry::registerActionsTo(action_factory, {"RotatingDiskDepositionApp"});
  ModulesApp::registerAllObjects<RotatingDiskDepositionApp>(factory, action_factory, syntax);
}
