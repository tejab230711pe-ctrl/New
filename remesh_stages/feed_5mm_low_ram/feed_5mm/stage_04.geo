SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are SI metres.
Box(1) = {-0.025, 0, 0, 0.05, 0.1, 0.01};
Box(3) = {-0.0125, 0, 0.01, 0.025, 0.02142857142857143, 0.013057244466482579};
Box(4) = {-0.0125, 0.02142857142857143, 0.01, 0.025, 0.007142857142857142, 0.013057244466482579};
all_solid[] = BooleanFragments{ Volume{1, 3, 4}; Delete; }{};
Coherence;
Cylinder(10) = {0, 0.04107142857142857, 0.00999485, 0, 0, 0.18, 0.0125};
Mesh.CharacteristicLengthMin = 0.002;
Mesh.CharacteristicLengthMax = 0.004;
Physical Volume("plate") = {1};
Physical Volume("deposit") = {3};
Physical Volume("fresh_deposit") = {4};
Physical Volume("rod") = {10};
// The named surfaces below are consumed by the stage input deck.
Physical Surface("rod_bottom") = { Surface In BoundingBox{-0.01251, 0.02856142857142857, 0.00998485, 0.01251, 0.05358142857142858, 0.01000485} };
Physical Surface("rod_top") = { Surface In BoundingBox{-0.01251, 0.02856142857142857, 0.18998484999999998, 0.01251, 0.05358142857142858, 0.19000485} };
Physical Surface("workpiece_top") = { Surface In BoundingBox{-0.02501, -1e-05, 0.00999, 0.02501, 0.10001, 0.01001} };
Physical Surface("workpiece_base") = { Surface In BoundingBox{-0.02501, -1e-05, -1e-05, 0.02501, 0.10001, 1e-05} };
// Active volumes: 1, 3, 4, 10
