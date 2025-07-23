import math
import typing

import numpy as np


def from_miller_bravais_direction(uvtw_indices: np.ndarray):
    """Convert a (U,V,T,W) Miller-Bravais direction to a (u,v,w) Miller direction.

    Parameters
    ----------
    uvtw_indices: np.ndarray
        The Miller-Bravais direction, (U, V, T, W). May be 1d or 2d, as columns.

    Returns
    -------
    uvw_indices: np.ndarray
        The Miller direction in 3D, (u, v, w).
    """
    if len(uvtw_indices.shape) == 1:
        U, V, T, W = uvtw_indices
        u = U - T
        v = V - T
        w = W
        return np.array([u, v, w])
    else:
        result = np.zeros((3, uvtw_indices.shape[1]))
        for i in range(uvtw_indices.shape[1]):
            result[:, i] = from_miller_bravais_direction(uvtw_indices[:, i])
        return result


def to_miller_bravais_direction(uvw_indices: np.ndarray):
    """Convert a (u,v,w) Miller direction to a (U,V,T,W) Miller-Bravais direction.

    Parameters
    ----------
    uvw_indices: np.ndarray
        The Miller 3-index direction, (u, v, w). May be 1d or 2d, as columns.

    Returns
    -------
    uvtw_indices: np.ndarray
        The Miller-Bravais 4-index direction, (U,V,T,W).
    """
    if len(uvw_indices.shape) == 1:
        u, v, w = uvw_indices
        U = (2 * u - v) / 3
        V = (2 * v - u) / 3
        T = -(U + V)
        W = w
        return np.array([U, V, T, W])
    else:
        result = np.zeros((4, uvw_indices.shape[1]))
        for i in range(uvw_indices.shape[1]):
            result[:, i] = to_miller_bravais_direction(uvw_indices[:, i])
        return result


def almost_zero(value, abs_tol=1e-5) -> bool:
    """Check if value is approximately zero, using an absolute tolerance"""
    return abs(value) < abs_tol


def almost_equal(value1, value2, abs_tol=1e-5) -> bool:
    """Check if two values are approximately equal, using an absolute tolerance"""
    return almost_zero(value1 - value2, abs_tol=abs_tol)


def almost_int(value, abs_tol=1e-5) -> bool:
    """Check if a floating point value is approximately integer, using an \
    absolute tolerance"""
    return almost_zero(abs(value - round(value)), abs_tol=abs_tol)


def scale_to_int(v: np.ndarray, cutoff: int = 10) -> typing.Union[np.ndarray, str]:
    x = np.max([np.abs(np.max(v)), np.abs(np.min(v))])
    v = v / x

    any_fractions = True
    while any_fractions:
        any_fractions = False
        for i in range(len(v)):
            if not almost_int(v[i]):
                x = np.abs(v[i])
                v = v / (x - math.floor(x))
                any_fractions = True
        for i in range(len(v)):
            if np.abs(v[i]) > cutoff:
                return f"indices elements > {cutoff}"
    return v


def scale_to_int_if_possible(v: np.ndarray, cutoff: int = 10) -> np.ndarray:
    x = scale_to_int(v, cutoff=cutoff)
    if isinstance(x, str):
        return v
    return x


def scale_columns_to_int_if_possible(M: np.ndarray, cutoff: int = 10) -> np.ndarray:
    """Scale the columns of a matrix to integers, if possible

    Parameters
    ----------
    M: np.ndarray
        The matrix to scale.
    cutoff: int
        The cutoff value for scaling.

    Returns
    -------
    scaled_M: np.ndarray
        The scaled matrix, or the original matrix if the cutoff was exceeded.
    """
    result = np.zeros(M.shape)
    for i in range(M.shape[1]):
        x = scale_to_int(M[:, i], cutoff=cutoff)
        if isinstance(x, str):
            return M
        result[:, i] = x
    return result
