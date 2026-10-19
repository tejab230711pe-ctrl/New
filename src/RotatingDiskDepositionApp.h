#pragma once

#include "MooseApp.h"

class RotatingDiskDepositionApp : public MooseApp
{
public:
  static InputParameters validParams();

  RotatingDiskDepositionApp(const InputParameters & parameters);

  static void registerApps();
  static void registerAll(Factory & factory, ActionFactory & action_factory, Syntax & syntax);
};
