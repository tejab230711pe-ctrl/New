import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from transfer_afsd_state import conservative_remap,intersection_volume

class RemapTests(unittest.TestCase):
    def setUp(self):
        self.tet=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    def test_partial_intersection_known_volume(self):
        shifted=self.tet+np.array([.5,0,0])
        self.assertAlmostEqual(intersection_volume(self.tet,shifted),.5**3/6,places=13)
    def test_refinement_conserves_multiple_extensive_fields(self):
        from itertools import combinations
        center=self.tet.mean(axis=0)
        target=np.array([np.vstack([self.tet[list(face)],center]) for face in combinations(range(4),3)])
        q=np.array([[3.,20.,1.]])
        result,sv,tv=conservative_remap(self.tet[None],target,q,['rod'],['rod']*4)
        np.testing.assert_allclose(tv@result,sv@q,rtol=1e-12)
    def test_missing_volume_rejected(self):
        with self.assertRaisesRegex(ValueError,'lost'):
            conservative_remap(self.tet[None],(self.tet*.5)[None],np.array([[1.]]),['rod'],['rod'])
    def test_outside_target_and_wrong_material_rejected(self):
        for target,label in [(self.tet+2,'rod'),(self.tet,'plate')]:
            with self.assertRaises(ValueError):
                conservative_remap(self.tet[None],target[None],np.array([[1.]]),['rod'],[label])
    def test_duplicate_target_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicated'):
            conservative_remap(self.tet[None],np.array([self.tet,self.tet]),np.array([[1.]]),['rod'],['rod','rod'])

if __name__=='__main__':unittest.main()
