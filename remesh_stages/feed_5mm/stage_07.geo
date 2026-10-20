SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are SI metres.
Box(1) = {-0.025, 0, 0, 0.05, 0.1, 0.01};
Box(3) = {-0.0125, 0, 0.01, 0.025, 0.07500000000000001, 0.00870482964432172};
workpiece[] = BooleanFragments{ Volume{1, 3}; Delete; }{};
Coherence;
Cylinder(10) = {0, 0.08750000000000001, 0.00975, 0, 0, 0.165, 0.0125};
Mesh.CharacteristicLengthMin = 0.001;
Mesh.CharacteristicLengthMax = 0.0025;
Physical Volume("workpiece") = {workpiece[]};
Physical Volume("rod") = {10};
// The named surfaces below are consumed by the stage input deck.
Physical Surface("rod_bottom") = { Surface In BoundingBox{-0.01251, 0.07499000000000001, 0.00974, 0.01251, 0.10001, 0.00976} };
Physical Surface("rod_top") = { Surface In BoundingBox{-0.01251, 0.07499000000000001, 0.17474, 0.01251, 0.10001, 0.17476000000000003} };
Physical Surface("workpiece_top") = { Surface In BoundingBox{-0.02501, -1e-05, 0.00999, 0.02501, 0.10001, 0.01001} };
Physical Surface("workpiece_base") = { Surface In BoundingBox{-0.02501, -1e-05, -1e-05, 0.02501, 0.10001, 1e-05} };
// Active volumes: workpiece[], 10
