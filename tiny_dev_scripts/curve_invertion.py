import numpy as np
import matplotlib.pyplot as plt
from svgpathtools import QuadraticBezier, CubicBezier
import svgpathtools as svgpath
from scipy.optimize import minimize

from pypattern.generic_utils import c_to_list

def _rel_to_abs_2d(in_edge, point):
        """Convert coordinates expressed relative to an edge into absolute """
        start, end = np.array(in_edge[0]), np.array(in_edge[1])
        edge = end - start
        edge_perp = np.array([-edge[1], edge[0]])

        conv_start = start + point[0] * edge
        conv_point = conv_start + point[1] * edge_perp
        
        return conv_point


def plot_bezier_curve(curve, control_points=None, bounding_points=None, extreme_points=None, tag='Bezier'):
    t_values = np.linspace(0, 1, num=1000)
    curve_points = np.array([c_to_list(curve.point(t)) for t in t_values])

    plt.plot(curve_points[:, 0], curve_points[:, 1], label=tag + " Curve")
    # plt.scatter([p.real for p in extreme_points], [p.imag for p in extreme_points], color='red', label="Extreme Points")
    
    if control_points is not None:
        plt.scatter(control_points[:, 0], control_points[:, 1], label=tag + " Control Points")

    if extreme_points is not None:
        plt.scatter(extreme_points[:, 0], extreme_points[:, 1], color='red', label=tag + " Extreme Points")
    
    if bounding_points is not None:
        plt.scatter(bounding_points[:, 0], bounding_points[:, 1], color='yellow', label=tag + " Control Points")


def match_length(control_points, end_points, target_len):

    control = np.array([
        end_points[0], 
        [control_points[0], control_points[1]], 
        [control_points[2], control_points[3]], 
        end_points[1]
    ])

    params = control[:, 0] + 1j*control[:, 1]
    curve_inverse = CubicBezier(*params)

    return (curve_inverse.length() - target_len)**2


def match_length_tangent(control_points, end_points, target_len, target_tangent):

    control = np.array([
        end_points[0], 
        [control_points[0], control_points[1]], 
        [control_points[2], control_points[3]], 
        end_points[1]
    ])

    params = control[:, 0] + 1j*control[:, 1]
    curve_inverse = CubicBezier(*params)

    length_diff = (curve_inverse.length() - target_len)**2

    tan_diff = (abs(curve_inverse.unit_tangent(0) - target_tangent))**2

    return length_diff + tan_diff


def bend_tangent(shift, cp, target_len, target_tangent):

    control = np.array([
        cp[0], 
        [cp[1][0] + shift[0], cp[1][0] + shift[1]], 
        cp[2],
        # [cp[2][0] + shift[2], cp[2][0] + shift[3]], 
        cp[-1]
    ])

    params = control[:, 0] + 1j*control[:, 1]
    curve_inverse = CubicBezier(*params)

    length_diff = (curve_inverse.length() - target_len)**2  # preservation

    tan_diff = (abs(curve_inverse.unit_tangent(0) - target_tangent))**2

    print('Step')
    print(length_diff, tan_diff)  # DEBUG
    print(curve_inverse.unit_tangent(0))

    reg = sum([x**2 for x in shift]) 

    return length_diff + tan_diff # DRAFT + 0.1*reg


shortcut_dist = 20  # Notably, this factor does not affect any calculations

# Forward
control_fwd = np.array([[0, 0], [0.3, 0.2], [0.8, 0.3], [1, 0]])
control_fwd *= shortcut_dist

params = control_fwd[:, 0] + 1j*control_fwd[:, 1]
curve_forward = CubicBezier(*params)

# alignemnt target 
# NOTE: Which alignement of Cubic curve corresponding to flat shoulder angle?
# 1) Preserving the tangent at connecting point
# 2) Following the "depth" vector part -- the same as tangent at connecting point

tangent = curve_forward.unit_tangent(t=0)
target_end = [tangent.real, tangent.imag]
target_vec = [[0, 0], target_end]


# Inverse
# DRAFT control_inv = np.array([
#      [0, 0], 
#      [0.3, 0.2], 
#      [0.8, -0.3], 
#      [1, 0]])
control_inv = np.array([
     target_vec[0], 
     _rel_to_abs_2d(target_vec, [0.3, 0.2]), 
     _rel_to_abs_2d(target_vec, [0.8, -0.3]),    # With last Y inverted
     target_vec[1]
])
control_inv *= shortcut_dist

params = control_inv[:, 0] + 1j*control_inv[:, 1]
curve_inverse = CubicBezier(*params)

print('Shortcut_dist = ', shortcut_dist)
print(f_len:=curve_forward.length())
print(in_len:=curve_inverse.length())
print('Length diff before opt: ', abs(f_len - in_len))

# Optimize for length difference
# TODO What are we preserving? 
# Currently: shorcut distance + overall length
# In sleeve examples: overall lengths and ????
start = control_inv[1].tolist() + control_inv[2].tolist()
# DRAFT start[-1] *= -1    # Invert the Y   
out = minimize(
    match_length_tangent,   # with tangent matching
    start, 
    args=(
        [control_inv[0], control_inv[-1]], 
        curve_forward.length(),
        curve_forward.unit_tangent(t=0)
    )
)

# DEBUG
# print(out)

cp = out.x

control_opt = np.array([
        control_inv[0], 
        [cp[0], cp[1]], 
        [cp[2], cp[3]], 
        control_inv[-1]
    ])

params = control_opt[:, 0] + 1j*control_opt[:, 1]
curve_inverse_opt = CubicBezier(*params)

print(f_len:=curve_forward.length())
print(in_len:=curve_inverse_opt.length())
print('Length diff after opt: ', abs(f_len - in_len))
# NOTE: If I use relative coordinates for cp representation, 
# will the optimal coordinates stay the same regardless of overall length??
# => YES!! Indeed it works
# print(f'Fin relative coords for {shortcut_dist}: ', control_opt / shortcut_dist)

# NOTE: Tangents -- aligned, because the first cp is almost the same
# DEBUG
print(curve_forward.unit_tangent(0))
print(curve_inverse.unit_tangent(0))
print(curve_inverse_opt.unit_tangent(0))



# --- Bending to the desired angle from inverse --- 
angle = 0
# Start from simple inverse
curve_inverse_rot = curve_inverse.rotated(-angle, origin=curve_inverse.point(0))
rot_cps = [
    curve_inverse_rot.start,
    curve_inverse_rot.control1,
    curve_inverse_rot.control2,
    curve_inverse_rot.end
]

rot_cps = [[cp.real, cp.imag] for cp in rot_cps]

# match tangent while preserving length
out = minimize(
    bend_tangent,  # with tangent matching
    [0, 0, 0, 0], 
    args=(
        rot_cps, 
        curve_forward.length(),
        curve_forward.unit_tangent(t=0)
    )
)

print(out)

shift = out.x

control_bend = np.array([
        rot_cps[0], 
        [rot_cps[1][0] + shift[0], rot_cps[1][0] + shift[1]], 
        rot_cps[2],   # DRAFT [rot_cps[2][0] + shift[2], rot_cps[2][0] + shift[3]],  # DRAFT 
        rot_cps[-1]
    ])

params = control_bend[:, 0] + 1j*control_bend[:, 1]
curve_inverse_bend = CubicBezier(*params)

print(curve_inverse_bend.unit_tangent(0))
print('Shortcut_dist = ', shortcut_dist)
print(f_len:=curve_forward.length())
print(in_len:=curve_inverse_bend.length())
print('Length diff after bending: ', abs(f_len - in_len))


# Visualize
plot_bezier_curve(curve_forward, control_fwd, tag='Cut')
plot_bezier_curve(curve_inverse, control_inv, tag='Initialization')
plot_bezier_curve(curve_inverse_opt, control_points=control_opt, tag='Optimized')
plot_bezier_curve(curve_inverse_rot, tag='Rotated')
plot_bezier_curve(curve_inverse_bend, control_bend, tag='Bended')

plt.title('Curve Inversion')
plt.legend()
plt.gca().set_aspect('equal', adjustable='box')
plt.show()


