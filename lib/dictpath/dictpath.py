
from collections import MutableSequence, MutableMapping
from . import exceptions, utils


class DictPath(dict):
    separator = '/'

    def __safe_path__(self, path):
        """
        Given a path and separator, return a list of path components. If path
        is already a list, return it.

        Note that a string path with the separator at index[0] will have the
        separator stripped off. If you pass a list path, the separator is
        ignored, and is assumed to be part of each key glob. It will not be
        stripped.
        """
        if issubclass(path.__class__, (MutableSequence)):
            return path
        path = path.lstrip(self.separator).split(self.separator)
        validated = []
        for elem in path:
            key = elem[0]
            strkey = str(key)
            if self.separator in strkey:
                raise exceptions.InvalidKeyName("{0} at {1} contains the separator {2}"
                                                "".format(strkey, self.separator.join(validated), self.separator))
            validated.append(strkey)
        return path

    def search(self, glob, afilter=None, dirs=True):
        """
        Given a path glob, return a dictionary containing all keys
        that matched the given glob.

        If 'yielded' is true, then a dictionary will not be returned.
        Instead tuples will be yielded in the form of (path, value) for
        every element in the document that matched the glob.
        """

        if afilter is not None:
            dirs = False

        globlist = self.__safe_path__(glob)
        for path in self._inner_search(globlist, dirs=dirs):
            try:
                val = self._get(path, afilter=afilter)
                yield (self.separator.join(map(str, utils.paths_only(path))), val)
            except exceptions.FilteredValue:
                pass


    def _inner_search(self, glob, dirs=True, leaves=False):
        """Search the object paths that match the glob."""
        for path in utils.paths(self, dirs, leaves):
            if utils.match(path, glob):
                yield path


    def _get(self, path, afilter=None):
        """Get the value of the given path.

        Arguments:

        obj -- Object to look in.
        path -- A list of keys representing the path.

        Keyword Arguments:

        view -- Return a view of the object.

        """
        index = 0
        target = self
        for pair in path:
            key = pair[0]
            target = target[key]

            if not issubclass(target.__class__, (MutableSequence, MutableMapping)):
                if (afilter and (not afilter(target))):
                    raise exceptions.FilteredValue

            index += 1

        return target

    def get(self, path, default=None):
        ret = None
        for item in self.search(path, yielded=True):
            if ret is not None:
                raise ValueError("dpath.util.get() globs must match only one leaf : %s" % path)
            ret = item[1]
        if ret is None:
            raise KeyError(path)
        return ret

    def set(self, path, value, create_missing=True):
        pass

    def delete(self, path):
        pass

    def merge(self, val):
        pass

    def search(self, path):
        pass

    def values(self, path=None):
        pass

