SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are SI metres.
Box(1) = {-0.025, 0, 0, 0.05, 0.1, 0.01};
Cylinder(2) = {0, 0.023214285714285715, 0.00975, 0, 0, 0.195, 0.0125};
Box(3) = {-0.0125, 0, 0.01, 0.025, 0.010714285714285714, 0.00870482964432172};
workpiece[] = BooleanFragments{ Volume{1, 3}; Delete; }{};
Coherence;
Mesh.CharacteristicLengthMin = 0.001;
Mesh.CharacteristicLengthMax = 0.0025;
Physical Volume("workpiece") = {workpiece[]};
Physical Volume("rod") = {2};
// The named surfaces below are consumed by the stage input deck.
Physical Surface("rod_bottom") = { Surface In BoundingBox{-0.01250001, 0.010714275714285714, 0.00974999, 0.01250001, 0.035714295714285714, 0.00975001} };
Physical Surface("rod_top") = { Surface In BoundingBox{-0.01250001, 0.010714275714285714, 0.20474999000000002, 0.01250001, 0.035714295714285714, 0.20475001} };
Physical Surface("workpiece_top") = { Surface In BoundingBox{-0.025000010000000003, -1e-08, 0.00999999, 0.025000010000000003, 0.10000001, 0.01000001} };
Physical Surface("workpiece_base") = { Surface In BoundingBox{-0.025000010000000003, -1e-08, -1e-08, 0.025000010000000003, 0.10000001, 1e-08} };
// Active volumes: workpiece[], 2
