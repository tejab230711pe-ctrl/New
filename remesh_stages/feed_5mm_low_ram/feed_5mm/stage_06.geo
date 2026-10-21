SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are SI metres.
Box(1) = {-0.025, 0, 0, 0.05, 0.1, 0.01};
Box(3) = {-0.0125, 0, 0.01, 0.025, 0.03571428571428572, 0.013057244466482577};
Box(4) = {-0.0125, 0.03571428571428572, 0.01, 0.025, 0.007142857142857138, 0.013057244466482577};
all_solid[] = BooleanFragments{ Volume{1, 3, 4}; Delete; }{};
Coherence;
Cylinder(10) = {0, 0.055357142857142855, 0.00999485, 0, 0, 0.17, 0.0125};
Mesh.CharacteristicLengthMin = 0.002;
Mesh.CharacteristicLengthMax = 0.004;
Physical Volume("plate") = {1};
Physical Volume("deposit") = {3};
Physical Volume("fresh_deposit") = {4};
Physical Volume("rod") = {10};
// The named surfaces below are consumed by the stage input deck.
Physical Surface("rod_bottom") = { Surface In BoundingBox{-0.01251, 0.042847142857142854, 0.00998485, 0.01251, 0.06786714285714285, 0.01000485} };
Physical Surface("rod_top") = { Surface In BoundingBox{-0.01251, 0.042847142857142854, 0.17998485, 0.01251, 0.06786714285714285, 0.18000485000000002} };
Physical Surface("workpiece_top") = { Surface In BoundingBox{-0.02501, -1e-05, 0.00999, 0.02501, 0.10001, 0.01001} };
Physical Surface("workpiece_base") = { Surface In BoundingBox{-0.02501, -1e-05, -1e-05, 0.02501, 0.10001, 1e-05} };
// Active volumes: 1, 3, 4, 10
