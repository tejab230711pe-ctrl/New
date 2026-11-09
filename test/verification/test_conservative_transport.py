import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from conservative_rod_transport import FluxTransport,tetra_barycentric_gradients

class TransportTests(unittest.TestCase):
    def setUp(self):
        self.x=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        self.cells=np.array([[0,1,2,3]])
    def test_affine_gradient_on_skew_tet(self):
        x=self.x@np.array([[2.,.4,.8],[.3,1.,.2],[.5,.1,3.]])
        gradient,_=tetra_barycentric_gradients(x[None,:,:])
        nodal=x@np.array([3.,-2.,7.])+4
        np.testing.assert_allclose(nodal@gradient[0],[3,-2,7],atol=1e-12)
    def test_inlet_added_mass_is_exact_and_not_lagged(self):
        f=FluxTransport(self.x,self.cells,lambda faces:np.all(self.x[faces,0]==0,axis=1))
        v=np.tile([.1,0,0],(4,1))
        c,r=f.step(self.x,self.x,v,v,np.array([0.]),.1)
        self.assertAlmostEqual(c[0]/6,.005,places=14)
        self.assertAlmostEqual(c[0]/6,r['supplied']-r['escaped'],places=14)
    def test_geometric_conservation_preserves_uniform_field(self):
        f=FluxTransport(self.x,self.cells,lambda faces:np.ones(len(faces),bool))
        c,r=f.step(self.x,1.01*self.x,np.zeros_like(self.x),np.zeros_like(self.x),np.ones(1),.1)
        np.testing.assert_allclose(c,1,atol=1e-12)
        self.assertAlmostEqual(r['supplied'],(1.01**3-1)/6,places=14)
    def test_inversion_rejected(self):
        f=FluxTransport(self.x,self.cells,lambda faces:np.ones(len(faces),bool))
        x=self.x.copy();x[[1,2]]=x[[2,1]]
        with self.assertRaises(ValueError): f.volumes(x)
    def test_large_cfl_rejected_without_clipping(self):
        f=FluxTransport(self.x,self.cells,lambda faces:np.ones(len(faces),bool))
        v=np.tile([10.,0,0],(4,1))
        with self.assertRaisesRegex(ValueError,'CFL'):
            f.step(self.x,self.x,v,v,np.array([.5]),1.)

if __name__=='__main__':unittest.main()
