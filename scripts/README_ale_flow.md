# Sharp-interface ALE flow workflow

`input/deposition.i` remains the solid-contact dwell model.  After it reaches
the user-defined plasticization condition, a rezone must construct a connected
AA5083 flow domain and transfer temperature plus mechanical state into it.
`input/afsd_ale_flow_stage.i` is the starting flow-stage deck.

It uses MOOSE's moving-mesh ALE Navier--Stokes kernels and custom AA5083
viscoplastic properties.  It has no latent heat or melting model.  The exposed
side faces are material boundaries; a production rezone driver must attach
`INSADDisplaceBoundaryBC` to each selected exposed face and transfer the
displaced free-surface geometry to Gmsh before the next stage.

This limitation is fundamental: a 3D ALE mesh can deform a connected material
region but cannot create new elements across a rod/plate contact.  Therefore a
rezone is required before a free surface reaches the boundary or mesh quality
falls below the selected threshold.  The rezone must retain flash as geometry;
it must not delete it or replace it with a percentage.
