SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are mm.
Box(1) = {-25.0, 0, 0, 50.0, 100.0, 10.0};
Cylinder(2) = {0, 68.21428571428572, 10.0, 0, 0, 174.0, 12.5};
Box(3) = {-12.5, 0, 10.0, 25.0, 55.71428571428572, 8.704829644321718};
Mesh.CharacteristicLengthMin = 1.0;
Mesh.CharacteristicLengthMax = 2.5;
Physical Volume("plate") = {1};
Physical Volume("rod") = {2};
Physical Volume("bead") = {3};
// Contact and thermal-contact surfaces are identified after import by
// geometric bounding boxes; do not merge volumes at this stage.
// Active volumes: 1, 2, 3
