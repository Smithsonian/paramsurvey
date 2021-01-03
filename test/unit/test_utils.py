import pytest
from unittest.mock import patch
import os
import platform
import collections

import pandas as pd
import psutil

import paramsurvey
from paramsurvey import utils


def test_psets_prep():
    with pytest.raises(ValueError):
        utils.psets_prep([{'_pset_id': None}])
    with pytest.raises(ValueError):
        utils.psets_prep([{'a b': None}])  # invalid identifier
    with pytest.raises(ValueError):
        utils.psets_prep([{'raise': None}])  # keyword
    with pytest.raises(ValueError):
        utils.psets_prep([{'_asdf': None}])


def test_flatten_results():
    normal = [
        {'pset': {'a': 1}, 'result': {'b': 1}},
        {'pset': {'a': 2}, 'result': {'b': 2}},
    ]
    flat = paramsurvey.flatten_results(normal)
    assert len(flat) == 2
    assert flat == [
        {'a': 1, 'b': 1},
        {'a': 2, 'b': 2},
    ]

    normal[1]['result']['a'] = 1
    with pytest.raises(ValueError):
        flat = paramsurvey.flatten_results(normal)


def test_make_subdir_name():
    ret = utils.make_subdir_name(100)
    assert len(ret) == 4

    ret = utils.make_subdir_name(100, prefix='prefix')
    assert len(ret) == 8

    with pytest.raises(Exception):
        ret = utils.make_subdir_name(0)


def test_get_pset_group():
    psets = [{'a': 1}, {'a': 2}, {'a': 3}, {'a': 4}, {'a': 5}]
    psets = pd.DataFrame(psets)
    pset_index = 0

    pset_group, pset_index = utils.get_pset_group(psets, pset_index, 3)
    assert len(pset_group) == 3
    assert pset_group.iloc[0].a == 1
    assert pset_group.iloc[-1].a == 3

    pset_group, pset_index = utils.get_pset_group(psets, pset_index, 3)
    assert len(pset_group) == 2
    assert pset_group.iloc[0].a == 4
    assert pset_group.iloc[-1].a == 5

    pset_group, pset_index = utils.get_pset_group(psets, pset_index, 3)
    assert len(pset_group) == 0


def copy2(orig):
    ret = orig.copy()  # shallow copy
    for k in ret:
        ret[k] = ret[k].copy()  # now deep copy
    return ret


def test_init_resolve_kwargs():
    gkwargs = copy2(paramsurvey.global_kwargs)
    with patch.dict(os.environ, {'PARAMSURVEY_VERBOSE': '3'}, clear=True):
        utils.initialize_kwargs(gkwargs, {'verbose': 1})
        system_kwargs, backend_kwargs, other_kwargs = utils.resolve_kwargs(gkwargs, {'verbose': 2, 'unrecognized': 'asdf'}, '', {})
        assert system_kwargs['verbose'] == 3, 'env variables trump all'
        assert backend_kwargs == {}
        assert other_kwargs['unrecognized'] == 'asdf', 'unrecognized args pass through'

    gkwargs = copy2(paramsurvey.global_kwargs)
    with patch.dict(os.environ, {}, clear=True):
        utils.initialize_kwargs(gkwargs, {'verbose': 1})
        system_kwargs, backend_kwargs, other_kwargs = utils.resolve_kwargs(gkwargs, {'verbose': 2}, '', {})
        assert system_kwargs['verbose'] == 2, 'closest wins'
        assert backend_kwargs == {}
        assert other_kwargs == {}

    gkwargs = copy2(paramsurvey.global_kwargs)
    with patch.dict(os.environ, {}, clear=True):
        utils.initialize_kwargs(gkwargs, {'verbose': 1})
        system_kwargs, backend_kwargs, other_kwargs = utils.resolve_kwargs(gkwargs, {}, '', {})
        assert system_kwargs['verbose'] == 1, 'init kwarg comes last'
        assert backend_kwargs == {}
        assert other_kwargs == {}

    gkwargs = copy2(paramsurvey.global_kwargs)
    with patch.dict(os.environ, {}, clear=True):
        utils.initialize_kwargs(gkwargs, {})
        system_kwargs, backend_kwargs, other_kwargs = utils.resolve_kwargs(gkwargs, {}, '', {})
        assert system_kwargs['verbose'] == 1, 'default'
        assert backend_kwargs == {}
        assert other_kwargs == {}

    gkwargs = copy2(paramsurvey.global_kwargs)
    with patch.dict(os.environ, {'PARAMSURVEY_BACKEND': 'FOO'}, clear=True):
        utils.initialize_kwargs(gkwargs, {})
        system_kwargs, backend_kwargs, other_kwargs = utils.resolve_kwargs(gkwargs, {}, '', {})
        assert system_kwargs['backend'] == 'FOO', 'type works'
        assert backend_kwargs == {}
        assert other_kwargs == {}

    gkwargs = copy2(paramsurvey.global_kwargs)
    with patch.dict(os.environ, {}, clear=True):
        utils.initialize_kwargs(gkwargs, {})
        kwargs = {'ray': {'foo': 1}, 'multiprocessing': {'bar': 2}, 'other': {'baz': 3}}
        system_kwargs, backend_kwargs, other_kwargs = utils.resolve_kwargs(gkwargs, kwargs, 'ray', {'ray': '', 'multiprocessing': ''})
        assert backend_kwargs == {'foo': 1}
        assert other_kwargs == {'other': {'baz': 3}}

    gkwargs = copy2(paramsurvey.global_kwargs)
    with patch.dict(os.environ, {'PARAMSURVEY_VERBOSE': 'None'}, clear=True):
        # int('None') raises ValueError
        with pytest.raises(ValueError):
            utils.initialize_kwargs(gkwargs, {})


def test_psets_empty():
    psets = []
    assert utils.psets_empty(psets)
    psets = [1]
    assert not utils.psets_empty(psets)

    df = pd.DataFrame()
    assert utils.psets_empty(df)
    df = pd.DataFrame({'a': [1, 2]})
    assert not utils.psets_empty(df)


def test_vmem():
    vmem0 = utils.vmem()
    big = bytearray(10000000)  # 10 megs
    vmem1 = utils.vmem()
    # vmem might not go up at all, if there is free memory
    assert vmem1 <= vmem0 + 0.011, 'vmem does not go up more than expected'


def test_resource_stats():
    rs = utils.resource_stats()
    for k in ('hostname', 'pid', 'total', 'available', 'load1', 'worker'):
        assert k in rs


def test_resource_complaint(capsys):
    rs = utils.resource_stats()

    h = 'bob'
    hp = 'bob:32'

    rsc = rs.copy()
    rsc['available'] = rsc['total'] * 0.06
    paramsurvey.utils._memory_complaint(h, hp, rsc)
    out, err = capsys.readouterr()
    assert err
    paramsurvey.utils._memory_complaint(h, hp, rsc)
    out, err = capsys.readouterr()
    assert not err, 'one complaint per level'

    rsc = rs.copy()
    rsc['available'] = rsc['total'] * 0.01
    paramsurvey.utils._memory_complaint(h, hp, rsc)
    out, err = capsys.readouterr()
    assert err, 'second complaint if available falls'

    rsc = rs.copy()
    rsc['load1'] = 0.
    paramsurvey.utils._loadavg_complaint(h, hp, rsc)
    out, err = capsys.readouterr()
    assert not err

    rsc = rs.copy()
    rsc['load1'] = 100.
    paramsurvey.utils._loadavg_complaint(h, hp, rsc)
    out, err = capsys.readouterr()
    assert err

    rsc = rs.copy()
    rsc['load1'] = 0.
    paramsurvey.utils._loadavg_complaint(h, hp, rsc)
    out, err = capsys.readouterr()
    assert err, 'load returned to normal'

    rsc = rs.copy()
    rsc['load1'] = 0.
    paramsurvey.utils._loadavg_complaint(h, hp, rsc)
    out, err = capsys.readouterr()
    assert not err

    rs1 = rs.copy()
    rs1['uss'] = rs1['total'] / 4
    rs1['dirty'] = 0
    rs1['swap'] = 0

    for weird_key in ('uss', 'dirty', 'swap'):
        rs1c = rs1.copy()
        del rs1c[weird_key]
        paramsurvey.utils._other_complaint(h, hp, rs1c)
        out, err = capsys.readouterr()
        assert not err

    rs1c = rs1.copy()
    paramsurvey.utils._other_complaint(h, hp, rs1c)
    out, err = capsys.readouterr()
    assert not err

    rs1c = rs1.copy()
    rs1c['dirty'] = rs1c['uss']
    paramsurvey.utils._other_complaint(h, hp, rs1c)
    out, err = capsys.readouterr()
    assert err

    rs1c = rs1.copy()
    rs1c['swap'] = rs1c['uss']
    paramsurvey.utils._other_complaint(h, hp, rs1c)
    out, err = capsys.readouterr()
    assert err


def test_memory_limits():
    lim, limits = utils.memory_limits(raw=True)
    assert 'available' in limits

    megabyte = 1024 * 1024

    assert lim > megabyte, 'at least a megabyte'
    assert lim < megabyte ** 3, 'less than an exabyte'

    assert lim <= limits['available']

    if platform.system == 'Linux':
        for e in ('rlimit_as', 'rlimit_rss', 'cgroups'):
            assert e in limits, 'expected '+e+' in limits'
    if platform.system == 'Darwin':
        for e in ('rrlimit_rss'):
            assert e in limits, 'expected '+e+' in limits'
        assert 'cgroup' not in limits, 'wut macos now has cgroups?'
