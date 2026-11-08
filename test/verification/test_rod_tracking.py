"""Checks for exact affine interpolation and explicit particle loss reporting."""
import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from trace_afsd_rod_material import TetraInterpolator


class TrackingTests(unittest.TestCase):
    def test_affine_field_on_deformed_tetrahedron(self):
        nodes = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        deformation = np.array([[2.,.3,0.],[.1,1.,.2],[0.,0.,.7]])
        nodes = nodes @ deformation.T + [3.,-2.,1.]
        gradient = np.array([[0.,-4.,0.],[4.,0.,0.],[0.,0.,2.]])
        values = nodes @ gradient.T + [1.,2.,3.]
        interp = TetraInterpolator(nodes,np.array([[0,1,2,3]]),values)
        points = np.array([nodes.mean(axis=0),.1*nodes[0]+.2*nodes[1]+.3*nodes[2]+.4*nodes[3]])
        result,located = interp.interpolate(points)
        self.assertTrue(located.all())
        np.testing.assert_allclose(result,points @ gradient.T + [1.,2.,3.],atol=1e-13)

    def test_outside_or_nonfinite_particles_are_not_clipped(self):
        nodes = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        interp = TetraInterpolator(nodes,np.array([[0,1,2,3]]),nodes)
        values,located = interp.interpolate(np.array([[2.,2.,2.],[np.nan,0.,0.],[.1,.1,.1]]))
        np.testing.assert_array_equal(located,[False,False,True])
        self.assertTrue(np.isnan(values[:2]).all())


if __name__ == '__main__':
    unittest.main()
