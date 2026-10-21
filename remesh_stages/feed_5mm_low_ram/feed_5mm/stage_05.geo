SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are SI metres.
Box(1) = {-0.025, 0, 0, 0.05, 0.1, 0.01};
Box(3) = {-0.0125, 0, 0.01, 0.025, 0.02857142857142857, 0.013057244466482576};
Box(4) = {-0.0125, 0.02857142857142857, 0.01, 0.025, 0.007142857142857142, 0.013057244466482576};
all_solid[] = BooleanFragments{ Volume{1, 3, 4}; Delete; }{};
Coherence;
Cylinder(10) = {0, 0.048214285714285716, 0.0099961, 0, 0, 0.17500000000000002, 0.0125};
Mesh.CharacteristicLengthMin = 0.002;
Mesh.CharacteristicLengthMax = 0.004;
Physical Volume("plate") = {1};
Physical Volume("deposit") = {3};
Physical Volume("fresh_deposit") = {4};
Physical Volume("rod") = {10};
// The named surfaces below are consumed by the stage input deck.
Physical Surface("rod_bottom") = { Surface In BoundingBox{-0.01251, 0.03570428571428571, 0.009986100000000001, 0.01251, 0.060724285714285724, 0.0100061} };
Physical Surface("rod_top") = { Surface In BoundingBox{-0.01251, 0.03570428571428571, 0.18498610000000001, 0.01251, 0.060724285714285724, 0.18500610000000003} };
Physical Surface("workpiece_top") = { Surface In BoundingBox{-0.02501, -1e-05, 0.00999, 0.02501, 0.10001, 0.01001} };
Physical Surface("workpiece_base") = { Surface In BoundingBox{-0.02501, -1e-05, -1e-05, 0.02501, 0.10001, 1e-05} };
// Active volumes: 1, 3, 4, 10
