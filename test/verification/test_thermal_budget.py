"""Independent checks of thermal energy integration used in the contact audit."""
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from check_contact_thermal_balance import reference_enthalpy_density, stored_energy, capacity_increment


class ThermalBudgetTest(unittest.TestCase):
    def test_capacity_is_enthalpy_derivative(self):
        for temperature in [270.,293.15,340.]:
            d=temperature-293.15
            expected=(2661.42-.312*d)*(948.14+.601*d)
            derivative=(reference_enthalpy_density(temperature+.001)-reference_enthalpy_density(temperature-.001))/.002
            self.assertAlmostEqual(derivative/expected,1.,places=9)

    def test_affine_temperature_cubic_integral(self):
        xyz=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        # Delta T = 6*x. Integral x^n on unit tetrahedron = n!/(n+3)!.
        a=2661.42*948.14
        b=.5*(2661.42*.601+948.14*(-.312))
        c=(-.312)*.601/3
        exact=a*6/24+b*36/60+c*216/120
        self.assertAlmostEqual(stored_energy(xyz,np.array([[0,1,2,3]]),293.15+6*xyz[:,0])/exact,1.,places=12)

    def test_discrete_capacity_uses_current_volume_and_end_properties(self):
        xyz=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        a=2661.42*948.14
        b=2661.42*.601+948.14*(-.312)
        c=(-.312)*.601
        exact=8*(a*6/24+b*36/60+c*216/120)
        result=capacity_increment(2*xyz,np.array([[0,1,2,3]]),293.15+6*xyz[:,0],np.full(4,293.15))
        self.assertAlmostEqual(result/exact,1.,places=12)


if __name__=='__main__': unittest.main()
