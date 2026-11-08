#include "AFSDDisplaceBoundaryBC.h"
#include "INSADDisplaceBoundaryBC.h"
#include "SystemBase.h"
#include "ImplicitEuler.h"
#include "BDF2.h"

registerMooseObject("RotatingDiskDepositionApp", AFSDDisplaceBoundaryBC);

InputParameters
AFSDDisplaceBoundaryBC::validParams()
{
  auto params = INSADDisplaceBoundaryBC::validParams();
  params.addClassDescription("Material free-surface motion using the BE/BDF2 nodal derivative "
                            "also used by the ALE fluid and energy kernels");
  return params;
}

AFSDDisplaceBoundaryBC::AFSDDisplaceBoundaryBC(const InputParameters & parameters)
  : ADNodalBC(parameters),
    _velocity(getFunctor<ADRealVectorValue>("velocity")),
    _nodal_dot(_var.nodalValueDot()),
    _dot_coefficient(_var.duDotDu()),
    _component(getParam<unsigned short>("component")),
    _subdomain(_mesh.getSubdomainID(getParam<SubdomainName>("associated_subdomain")))
{
  if (_component > 2)
    paramError("component", "Displacement component must be 0, 1 or 2");
  const auto & integrator = _sys.getTimeIntegrator(_var.number());
  if (!dynamic_cast<const ImplicitEuler *>(&integrator) && !dynamic_cast<const BDF2 *>(&integrator))
    mooseError("AFSDDisplaceBoundaryBC supports only implicit Euler or BDF2");
}

ADReal
AFSDDisplaceBoundaryBC::computeQpResidual()
{
  const std::set<SubdomainID> subdomains = {_subdomain};
  const Moose::NodeArg node{_current_node, &subdomains};
  // The stored nodal derivative contains the integrator's complete history.
  // Restore its exact AD derivative with respect to the current nodal value.
  const ADReal dot = _nodal_dot + _dot_coefficient[0] * (_u - MetaPhysicL::raw_value(_u));
  return _dt * (dot - _velocity(node, determineState())(_component));
}
