SetFactory("OpenCASCADE");
// AA5083 AFSD remesh stage; coordinates are mm.
Box(1) = {-25.0, 0, 0, 50.0, 100.0, 10.0};
Cylinder(2) = {0, 23.214285714285715, 10.0, 0, 0, 195.0, 12.5};
Box(3) = {-12.5, 0, 10.0, 25.0, 10.714285714285715, 8.70482964432172};
Mesh.CharacteristicLengthMin = 1.0;
Mesh.CharacteristicLengthMax = 2.5;
Physical Volume("plate") = {1};
Physical Volume("rod") = {2};
Physical Volume("bead") = {3};
// Contact and thermal-contact surfaces are identified after import by
// geometric bounding boxes; do not merge volumes at this stage.
// Active volumes: 1, 2, 3
