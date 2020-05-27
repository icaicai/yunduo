# coding=utf8

import time
import uuid
import hashlib
import six
from dpath import util


def merge(src1, src2, *srcs):
    dst = type(src1)()
    srcs = (src1, src2) + srcs
    for o in srcs:
        util.merge(dst, o)
    return dst


class _NoDefault(object):
    def __repr__(self):
        return '<NoDefault>'


no_default = _NoDefault()
del _NoDefault


def freeze(o):
    if isinstance(o, dict):
        return frozenset({k: freeze(v) for k, v in o.items()}.items())

    if isinstance(o, list):
        return tuple([freeze(v) for v in o])

    return o


def make_hash(o):
    """
    makes a hash out of anything that contains only list,dict and hashable types including string and numeric types
    """
    return hash(freeze(o))


def arg_to_iter(arg):
    if arg is None:
        return []
    elif not isinstance(arg, (dict, six.text_type, bytes)) and hasattr(arg, '__iter__'):
        return arg
    else:
        return [arg]


def md5sum(o):
    m = hashlib.md5()
    s = repr(freeze(o))
    m.update(s.encode('utf8', errors='replace'))
    return m.hexdigest()


def base_convert(num, b=36):
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    return ((num == 0) and "0") or (base_convert(num // b, b).lstrip("0") + alphabet[num % b])


def gen_id(prefix):
    u = uuid.uuid4()
    t = base_convert(int(time.time()))
    r = base_convert(u.time_low)
    # '{:x3s}{:06s}{:06s}'.format(prefix, t, r)
    return '%s%s%s' % (prefix.rjust(3, 'x')[:3], t.rjust(6, '0')[:6], r.rjust(6, '0')[:6])  # 2038
