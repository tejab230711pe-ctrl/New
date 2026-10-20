SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are SI metres.
Box(1) = {-0.025, 0, 0, 0.05, 0.1, 0.01};
Cylinder(2) = {0, 0.0125, 0.009980000000000001, 0, 0, 0.2, 0.0125};
Mesh.CharacteristicLengthMin = 0.002;
Mesh.CharacteristicLengthMax = 0.004;
Physical Volume("workpiece") = {1};
Physical Volume("rod") = {2};
// The named surfaces below are consumed by the stage input deck.
Physical Surface("rod_bottom") = { Surface In BoundingBox{-0.01251, -1e-05, 0.009970000000000001, 0.01251, 0.02501, 0.00999} };
Physical Surface("rod_top") = { Surface In BoundingBox{-0.01251, -1e-05, 0.20997, 0.01251, 0.02501, 0.20999} };
Physical Surface("workpiece_top") = { Surface In BoundingBox{-0.02501, -1e-05, 0.00999, 0.02501, 0.10001, 0.01001} };
Physical Surface("workpiece_base") = { Surface In BoundingBox{-0.02501, -1e-05, -1e-05, 0.02501, 0.10001, 1e-05} };
// Active volumes: 1, 2
