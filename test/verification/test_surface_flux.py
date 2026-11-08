"""Analytical checks for the independent Exodus surface-flux diagnostic."""
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from analyze_afsd_surface_flux import exterior_faces, surface_fluxes, mesh_derivative, tetra_determinants


class SurfaceFluxTests(unittest.TestCase):
    def test_variable_step_bdf2(self):
        times = np.array([0., .1, .3, .7])
        displacement = times**2
        for i in (2, 3):
            self.assertAlmostEqual(mesh_derivative(displacement, times, i, 'bdf2'), 2*times[i])
        self.assertAlmostEqual(mesh_derivative(displacement, times, 1, 'bdf2'), .1)

    def test_inverted_tetrahedron(self):
        p = np.array([[0.,0.,0.], [1.,0.,0.], [0.,1.,0.], [0.,0.,1.]])
        connectivity = np.array([[0,1,2,3]])
        self.assertGreater(tetra_determinants(p, connectivity)[0], 0)
        p[3,2] = -1
        self.assertLess(tetra_determinants(p, connectivity)[0], 0)

    def test_divergence_theorem_and_mesh_leak(self):
        points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        faces = exterior_faces(np.array([[0, 1, 2, 3]]))
        flux = surface_fluxes(points, faces, points, 2*points, ['surface']*4)['surface']
        # div(x)=3; unit tetrahedron volume=1/6. Mesh velocity is 2x.
        self.assertAlmostEqual(flux['fluid_m3_s'], .5)
        self.assertAlmostEqual(flux['mesh_m3_s'], 1.)
        self.assertAlmostEqual(flux['relative_m3_s'], -.5)

    def test_internal_face_cancels_and_translation_has_no_net_flux(self):
        points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.],
                           [0., 0., 1.], [0., 0., -1.]])
        faces = exterior_faces(np.array([[0, 1, 2, 3], [0, 2, 1, 4]]))
        self.assertEqual(len(faces), 6)
        velocity = np.tile([2., -3., 4.], (5, 1))
        flux = surface_fluxes(points, faces, velocity, velocity, ['surface']*6)['surface']
        self.assertAlmostEqual(flux['fluid_m3_s'], 0.)
        self.assertAlmostEqual(flux['absolute_normal_leak_m3_s'], 0.)


if __name__ == '__main__':
    unittest.main()
