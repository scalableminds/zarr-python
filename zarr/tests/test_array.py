# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division


from nose.tools import eq_ as eq
import numpy as np
from numpy.testing import assert_array_equal
import zarr


def test_array_1d():

    a = np.arange(1050)
    z = zarr.Array(a.shape, chunks=100, dtype=a.dtype)

    # check properties
    eq(a.shape, z.shape)
    eq(a.dtype, z.dtype)
    eq((100,), z.chunks)
    eq((11,), z.cdata.shape)
    eq(zarr.defaults.cname, z.cname)
    eq(zarr.defaults.clevel, z.clevel)
    eq(zarr.defaults.shuffle, z.shuffle)

    # set data
    z[:] = a

    # check properties
    eq(a.nbytes, z.nbytes)
    eq(sum(c.cbytes for c in z.cdata.flat), z.cbytes)

    # check round-trip
    assert_array_equal(a, z[:])
    assert_array_equal(a, z[...])

    # check slicing
    assert_array_equal(a[:10], z[:10])
    assert_array_equal(a[10:20], z[10:20])
    assert_array_equal(a[-10:], z[-10:])
    # ...across chunk boundaries...
    assert_array_equal(a[:110], z[:110])
    assert_array_equal(a[190:310], z[190:310])
    assert_array_equal(a[-110:], z[-110:])

    # check partial assignment
    b = np.arange(1e5, 2e5)
    z = zarr.Array(a.shape, chunks=100)
    z[:] = a
    assert_array_equal(a, z[:])
    z[190:310] = b[190:310]
    assert_array_equal(a[:190], z[:190])
    assert_array_equal(b[190:310], z[190:310])
    assert_array_equal(a[310:], z[310:])


def test_array_1d_fill_value():

    for fill_value in -1, 0, 1, 10:

        a = np.arange(1050)
        f = np.empty_like(a)
        f.fill(fill_value)
        z = zarr.Array(a.shape, chunks=100, fill_value=fill_value)
        z[190:310] = a[190:310]

        assert_array_equal(f[:190], z[:190])
        assert_array_equal(a[190:310], z[190:310])
        assert_array_equal(f[310:], z[310:])


def test_array_1d_set_scalar():

    # setup
    a = np.empty(100)
    z = zarr.Array(a.shape, chunks=10, dtype=a.dtype)
    z[:] = a
    assert_array_equal(a, z[:])

    for value in -1, 0, 1, 10:
        a[15:35] = value
        z[15:35] = value
        assert_array_equal(a, z[:])
        a[:] = value
        z[:] = value
        assert_array_equal(a, z[:])
