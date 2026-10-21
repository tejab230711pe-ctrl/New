#define _USE_MATH_DEFINES
#include <cmath>
extern "C" void f_400864a3ef406fdd(double * ret, const double *params, const double *immed, const double eps) {
double s[2];
s[0] = immed[0];
s[1] = params[0];
using std::abs; s[1] = abs(s[1]);
s[0] *= s[1];
*ret = s[0]; }
