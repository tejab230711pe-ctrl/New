SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are SI metres.
Box(1) = {-0.025, 0, 0, 0.05, 0.1, 0.01};
Box(4) = {-0.0125, 0.0, 0.01, 0.025, 0.007142857142857142, 0.013057244466482579};
all_solid[] = BooleanFragments{ Volume{1, 4}; Delete; }{};
Coherence;
Cylinder(10) = {0, 0.019642857142857142, 0.0099977, 0, 0, 0.195, 0.0125};
Mesh.CharacteristicLengthMin = 0.002;
Mesh.CharacteristicLengthMax = 0.004;
Physical Volume("plate") = {1};

Physical Volume("fresh_deposit") = {4};
Physical Volume("rod") = {10};
// The named surfaces below are consumed by the stage input deck.
Physical Surface("rod_bottom") = { Surface In BoundingBox{-0.01251, 0.007132857142857142, 0.0099877, 0.01251, 0.03215285714285714, 0.0100077} };
Physical Surface("rod_top") = { Surface In BoundingBox{-0.01251, 0.007132857142857142, 0.2049877, 0.01251, 0.03215285714285714, 0.20500770000000001} };
Physical Surface("workpiece_top") = { Surface In BoundingBox{-0.02501, -1e-05, 0.00999, 0.02501, 0.10001, 0.01001} };
Physical Surface("workpiece_base") = { Surface In BoundingBox{-0.02501, -1e-05, -1e-05, 0.02501, 0.10001, 1e-05} };
// Active volumes: 1, 4, 10
