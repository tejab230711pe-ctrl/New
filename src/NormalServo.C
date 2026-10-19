#include "NormalServo.h"
#include "MooseError.h"

registerMooseObject("RotatingDiskDepositionApp", NormalServo);

InputParameters
NormalServo::validParams()
{
  InputParameters params = Kernel::validParams();
  params.addRequiredCoupledVar("disp", "Displacement variable (e.g., Uz) in the normal direction");
  params.addRequiredParam<Real>("stiffness", "Normal‑servo base stiffness (Pa/m)");
  params.addRequiredParam<Real>("preload_force", "Magnitude of the preload force (N)");
  params.addRequiredParam<Real>("ramp_time", "Duration over which the preload ramps from 0 to full (s)");
  // The current simulation time is automatically available via the Executioner; we expose it as a parameter for simplicity
  params.addParam<Real>("current_time", 0.0, "Current time (s) – will be updated each timestep by the input file");
  return params;
}

NormalServo::NormalServo(const InputParameters & parameters)
  : Kernel(parameters),
    _disp(coupledValue("disp")),
    _stiffness(getParam<Real>("stiffness")),
    _preload_force(getParam<Real>("preload_force")),
    _ramp_time(getParam<Real>("ramp_time")),
    _current_time(getParam<Real>("current_time"))
{}

Real
NormalServo::computeQpResidual()
{
  // Linear ramp from 0 to 1 over ramp_time seconds
  Real ramp = 0.0;
  if (_ramp_time > 0.0)
    ramp = std::min(1.0, _current_time / _ramp_time);

  // Body force magnitude (N/m^3) = stiffness * preload_force * ramp
  // The original script applies the preload as a force (N) on the normal direction.
  // In a distributed FE sense we divide by the element volume implicitly via the kernel
  // formulation, so we multiply by the test function.
  Real force = _stiffness * _preload_force * ramp;

  // Apply in the negative Z direction; assuming the coupled displacement variable is Uz.
  // The sign convention from the FreeFEM script is a positive preload (upward) when the
  // normal is defined as negative Z, therefore we add a negative sign here.
  Real body_force = -force;

  // Residual contribution: body_force * test()
  return body_force * _test[_i][_qp];
}
