SetFactory("OpenCASCADE");
Disk(1) = {0, 0.0125, 0.010, 0.020, 0.020};
Disk(2) = {0, 0.0125, 0.010, 0.0125, 0.0125};
s[] = BooleanFragments{ Surface{1}; Delete; }{ Surface{2}; Delete; };
Extrude {0,0,0.006} { Surface{s[]}; Layers{2}; }
If (0.004 > 0)
  core_top[] = Surface In BoundingBox{-0.012501,-0.000001,0.015999,0.012501,0.025001,0.016001};
  Extrude {0,0,0.004} { Surface{core_top[]}; Layers{1}; }
EndIf
v[] = Volume{:};
inlet[] = Surface In BoundingBox{-0.012501,-0.000001,0.019999,0.012501,0.025001,0.020001};
bottom[] = Surface In BoundingBox{-0.020001,-0.007501,0.009999,0.020001,0.032501,0.010001};
external[] = CombinedBoundary{ Volume{v[]}; };
For i In {0:#external[]-1}
  external[i] = Abs(external[i]);
EndFor
free[] = external[];
free[] -= inlet[];
free[] -= bottom[];
Physical Volume("flow", 1) = {v[]};
Physical Surface("rod_inlet", 11) = {inlet[]};
Physical Surface("plate", 12) = {bottom[]};
Physical Surface("free_surface", 13) = {free[]};
Mesh.CharacteristicLengthMin = 0.004;
Mesh.CharacteristicLengthMax = 0.004;
Mesh.MshFileVersion = 2.2;
