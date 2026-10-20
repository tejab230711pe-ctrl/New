SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are SI metres.
Box(1) = {-0.025, 0, 0, 0.05, 0.1, 0.01};
Cylinder(2) = {0, 0.03607142857142857, 0.00975, 0, 0, 0.189, 0.0125};
Box(3) = {-0.0125, 0, 0.01, 0.025, 0.023571428571428566, 0.008704829644321718};
workpiece[] = BooleanFragments{ Volume{1, 3}; Delete; }{};
Coherence;
Mesh.CharacteristicLengthMin = 0.001;
Mesh.CharacteristicLengthMax = 0.0025;
Physical Volume("workpiece") = {workpiece[]};
Physical Volume("rod") = {2};
// The named surfaces below are consumed by the stage input deck.
Physical Surface("rod_bottom") = { Surface In BoundingBox{-0.01250001, 0.023571418571428564, 0.00974999, 0.01250001, 0.04857143857142857, 0.00975001} };
Physical Surface("rod_top") = { Surface In BoundingBox{-0.01250001, 0.023571418571428564, 0.19874999000000002, 0.01250001, 0.04857143857142857, 0.19875001} };
Physical Surface("workpiece_top") = { Surface In BoundingBox{-0.025000010000000003, -1e-08, 0.00999999, 0.025000010000000003, 0.10000001, 0.01000001} };
Physical Surface("workpiece_base") = { Surface In BoundingBox{-0.025000010000000003, -1e-08, -1e-08, 0.025000010000000003, 0.10000001, 1e-08} };
// Active volumes: workpiece[], 2
