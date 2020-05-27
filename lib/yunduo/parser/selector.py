

import six
from parsel import selector


class SelectorList(selector.SelectorList):

    def text(self, children=True):
        if not self:
            return None
        return ''.join([x.text(children) for x in self])

    __str__ = text

    def attr(self, attr):
        return [x.attr(attr) for x in self]


class Selector(selector.Selector):
    selectorlist_cls = SelectorList

    def text(self, children=True):
        # print '====>2 ', self._expr
        # css: a::attr(href)
        last = self._expr.rpartition('/')[-1]
        if last.startswith('@') or self._expr.endswith('/text()'):
            cs = self.extract()
        else:
            if children:
                xp = './/text()'
            else:
                xp = './text()'

            cs = self.xpath(xp).extract()
        # print cs
        if isinstance(cs, list):
            return ''.join([str(c) for c in cs]).strip()
        elif isinstance(cs, six.text_type):
            return cs.strip()
        elif isinstance(cs, six.binary_type):
            return str(cs).strip()

        return None

    __str__ = text

    def attr(self, attr):
        # print '====>1 ', self._expr
        try:
            return self.root.attrib[attr]
        except Exception:
            return None
