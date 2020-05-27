
import fnmatch
import six
from collections import MutableSequence, MutableMapping
from . import exceptions


def paths_only(path):
    """
    Return a list containing only the pathnames of the given path list, not the types.
    """
    l = []
    for p in path:
        l.append(p[0])
    return l


def paths(obj, dirs=True, leaves=True, path=[]):
    """Yield all paths of the object.

    Arguments:

    obj -- An object to get paths from.

    Keyword Arguments:

    dirs -- Yield intermediate paths.
    leaves -- Yield the paths with leaf objects.
    path -- A list of keys representing the path.
    skip -- Skip special keys beginning with '+'.

    """
    if isinstance(obj, MutableMapping):
        # Python 3 support
        if six.PY3:
            iteritems = obj.items()
            string_class = str
        else:  # Default to PY2
            iteritems = obj.iteritems()
            string_class = basestring

        for (k, v) in iteritems:
            if issubclass(k.__class__, (string_class)):
                if not k:
                    raise exceptions.InvalidKeyName("Empty string keys not allowed without ")

            newpath = path + [(k, v.__class__)]

            if dirs:
                yield newpath
            for child in paths(v, dirs, leaves, newpath):
                yield child
    elif isinstance(obj, MutableSequence):
        for (i, v) in enumerate(obj):
            newpath = path + [[i, v.__class__]]
            if dirs:
                yield newpath
            for child in paths(obj[i], dirs, leaves, newpath):
                yield child
    elif leaves:
        yield path + [[obj, obj.__class__]]
    elif not dirs:
        yield path


def match(path, glob):
    """Match the path with the glob.

    Arguments:

    path -- A list of keys representing the path.
    glob -- A list of globs to match against the path.

    """
    path_len = len(path)
    glob_len = len(glob)

    ss = -1
    ss_glob = glob
    if '**' in glob:
        ss = glob.index('**')
        if '**' in glob[ss + 1:]:
            raise exceptions.InvalidGlob("Invalid glob. Only one '**' is permitted per glob.")

        if path_len >= glob_len:
            # Just right or more stars.
            more_stars = ['*'] * (path_len - glob_len + 1)
            ss_glob = glob[:ss] + more_stars + glob[ss + 1:]
        elif path_len == glob_len - 1:
            # Need one less star.
            ss_glob = glob[:ss] + glob[ss + 1:]

    if path_len == len(ss_glob):
        # Python 3 support
        if six.PY3:
            return all(map(fnmatch.fnmatch, list(map(str, paths_only(path))), list(map(str, ss_glob))))
        else:  # Default to Python 2
            return all(map(fnmatch.fnmatch, map(str, paths_only(path)), map(str, ss_glob)))

    return False


