#include "RotatingDiskDepositionApp.h"
#include "MooseMain.h"

// Begin the main program for RotatingDiskDepositionApp
int
main(int argc, char * argv[])
{
  return Moose::main<RotatingDiskDepositionApp>(argc, argv);
}
