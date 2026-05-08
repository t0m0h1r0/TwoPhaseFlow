import numpy as np

from twophase.simulation.face_boundary import (
    zero_wall_normal_face_components,
    zero_wall_velocity_face_components,
)


def test_zero_wall_normal_face_components_only_zeros_normal_faces():
    faces = [
        np.ones((4, 5)),
        2.0 * np.ones((4, 5)),
    ]

    bounded = zero_wall_normal_face_components(faces, xp=np, bc_type="wall")

    np.testing.assert_allclose(bounded[0][0, :], 0.0)
    np.testing.assert_allclose(bounded[0][-1, :], 0.0)
    np.testing.assert_allclose(bounded[0][1:-1, :], 1.0)
    np.testing.assert_allclose(bounded[1][:, 0], 0.0)
    np.testing.assert_allclose(bounded[1][:, -1], 0.0)
    np.testing.assert_allclose(bounded[1][:, 1:-1], 2.0)


def test_zero_wall_normal_face_components_respects_periodic_axes():
    faces = [
        np.ones((4, 5)),
        2.0 * np.ones((4, 5)),
    ]

    bounded = zero_wall_normal_face_components(
        faces,
        xp=np,
        bc_type="periodic_wall",
    )

    np.testing.assert_allclose(bounded[0], 1.0)
    np.testing.assert_allclose(bounded[1][:, 0], 0.0)
    np.testing.assert_allclose(bounded[1][:, -1], 0.0)
    np.testing.assert_allclose(bounded[1][:, 1:-1], 2.0)


def test_zero_wall_velocity_face_components_zeros_all_wall_boundaries():
    faces = [
        np.ones((4, 5)),
        2.0 * np.ones((4, 5)),
    ]

    bounded = zero_wall_velocity_face_components(faces, xp=np, bc_type="wall")

    for face in bounded:
        np.testing.assert_allclose(face[0, :], 0.0)
        np.testing.assert_allclose(face[-1, :], 0.0)
        np.testing.assert_allclose(face[:, 0], 0.0)
        np.testing.assert_allclose(face[:, -1], 0.0)
    np.testing.assert_allclose(bounded[0][1:-1, 1:-1], 1.0)
    np.testing.assert_allclose(bounded[1][1:-1, 1:-1], 2.0)
