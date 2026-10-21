SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are SI metres.
Box(1) = {-0.025, 0, 0, 0.05, 0.1, 0.01};
Box(3) = {-0.0125, 0, 0.01, 0.025, 0.04285714285714286, 0.013057244466482579};
Box(4) = {-0.0125, 0.04285714285714286, 0.01, 0.025, 0.007142857142857145, 0.013057244466482579};
all_solid[] = BooleanFragments{ Volume{1, 3, 4}; Delete; }{};
Coherence;
Cylinder(10) = {0, 0.0625, 0.009999000000000001, 0, 0, 0.165, 0.0125};
Mesh.CharacteristicLengthMin = 0.002;
Mesh.CharacteristicLengthMax = 0.004;
Physical Volume("plate") = {1};
Physical Volume("deposit") = {3};
Physical Volume("fresh_deposit") = {4};
Physical Volume("rod") = {10};
// The named surfaces below are consumed by the stage input deck.
Physical Surface("rod_bottom") = { Surface In BoundingBox{-0.01251, 0.04999, 0.009989000000000001, 0.01251, 0.07501, 0.010009} };
Physical Surface("rod_top") = { Surface In BoundingBox{-0.01251, 0.04999, 0.174989, 0.01251, 0.07501, 0.17500900000000003} };
Physical Surface("workpiece_top") = { Surface In BoundingBox{-0.02501, -1e-05, 0.00999, 0.02501, 0.10001, 0.01001} };
Physical Surface("workpiece_base") = { Surface In BoundingBox{-0.02501, -1e-05, -1e-05, 0.02501, 0.10001, 1e-05} };
// Active volumes: 1, 3, 4, 10
