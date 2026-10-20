SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are SI metres.
Box(1) = {-0.025, 0, 0, 0.05, 0.1, 0.01};
Box(3) = {-0.0125, 0, 0.01, 0.025, 0.021428571428571432, 0.00870482964432172};
workpiece[] = BooleanFragments{ Volume{1, 3}; Delete; }{};
Coherence;
Cylinder(10) = {0, 0.03392857142857143, 0.009999000000000001, 0, 0, 0.19, 0.0125};
Mesh.CharacteristicLengthMin = 0.002;
Mesh.CharacteristicLengthMax = 0.004;
Physical Volume("workpiece") = {workpiece[]};
Physical Volume("rod") = {10};
// The named surfaces below are consumed by the stage input deck.
Physical Surface("rod_bottom") = { Surface In BoundingBox{-0.01251, 0.021418571428571433, 0.009989000000000001, 0.01251, 0.04643857142857143, 0.010009} };
Physical Surface("rod_top") = { Surface In BoundingBox{-0.01251, 0.021418571428571433, 0.199989, 0.01251, 0.04643857142857143, 0.20000900000000002} };
Physical Surface("workpiece_top") = { Surface In BoundingBox{-0.02501, -1e-05, 0.00999, 0.02501, 0.10001, 0.01001} };
Physical Surface("workpiece_base") = { Surface In BoundingBox{-0.02501, -1e-05, -1e-05, 0.02501, 0.10001, 1e-05} };
// Active volumes: workpiece[], 10
