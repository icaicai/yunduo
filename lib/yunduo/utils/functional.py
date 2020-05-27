# coding=utf8

import six



charests = ('utf8', 'gbk', 'gb2312', 'big5', 'ascii',
            'shift_jis', 'euc_jp', 'euc_kr', 'iso2022_kr',
            'latin1', 'latin2', 'latin9', 'latin10', 'koi8_r',
            'cyrillic', 'utf16', 'utf32'
            )


def str_encode(stri, encoding='utf8'):
    if isinstance(stri, six.text_type):
        if encoding:
            return stri.encode(encoding)
        else:
            return stri
    else:
        for i in charests:
            try:
                s = stri.decode(i)
                if encoding:
                    return s.encode(encoding)
                else:
                    return s
            except Exception:
                pass
        else:
            return stri


def clear_exc(exc_str):
    lines = exc_str.split('\n')
    lines = filter(lambda line: 'File "<string>"' in line or not line.startswith(' '), lines)
    return '\n'.join(lines)


RATE_MODIFIER_MAP = {
    's': lambda n: n,
    'm': lambda n: n / 60.0,
    'h': lambda n: n / 60.0 / 60.0,
}


def parse_rate(r):
    """Convert rate string (`"100/m"`, `"2/h"` or `"0.5/s"`) to seconds."""
    if r:
        if isinstance(r, six.string_types):
            ops, _, modifier = r.partition('/')
            if len(modifier) > 1:
                burst = int(modifier[:-1])
                unit = modifier[-1]
            else:
                burst = 1
                unit = modifier
            return (RATE_MODIFIER_MAP[unit or 's'](float(ops)) or 0, burst)
        return (r or 0, 1)
    return (0, 1)


def parse_mon_rate(r):
    if r:
        if isinstance(r, six.string_types):
            ops, _, modifier = r.split('/')
            if len(modifier) > 1:
                burst = int(modifier[:-1])
                unit = modifier[-1]
            else:
                burst = 1
                unit = modifier
            return (RATE_MODIFIER_MAP[unit or 's'](float(ops)) or 0, burst)
        return (r or 0, 1)
    return (0, 1)


