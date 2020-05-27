# coding=utf8

import time
import six
from hashlib import sha1
from redis.exceptions import NoScriptError
from yunduo.resource import get_connection


redis_conf = get_connection('conf')
RATE_LIMIT_SCRIPT = '''\
local key, now, token = KEYS[1], tonumber(ARGV[1]), tonumber(ARGV[2])
local timestamp, fill_rate, capacity, tokens, rhold = 0, 0, 0, 0, 0
local vals = redis.call("hgetall", key)

for i = 1, #vals, 2 do
    if     vals[i] == "timestamp" then timestamp = tonumber(vals[i+1])
    elseif vals[i] == "fill_rate" then fill_rate = tonumber(vals[i+1])
    elseif vals[i] == "capacity"  then capacity  = tonumber(vals[i+1])
    elseif vals[i] == "tokens"    then tokens    = tonumber(vals[i+1])
    elseif vals[i] == "rhold"     then rhold     = tonumber(vals[i+1])
    end
end
if fill_rate == 0 then
    return 0
end

local delta = fill_rate * (now - timestamp)
rhold = rhold - delta
if rhold < 0 then
    rhold = 0
end
tokens = math.min(capacity, tokens + delta)

token = token + rhold
if token <= tokens then
    tokens = tokens - token
    redis.call("hmset", key, "timestamp", tostring(now), "tokens", tostring(tokens), "rhold", "0")
    return 0
end
local _tokens = math.max(token, tokens)
local rhold = (_tokens - tokens)
local hold = rhold / fill_rate
tokens = tokens - rhold
if tokens < 0 then
    tokens = 0
end
redis.call("hmset", key, "timestamp", tostring(now), "tokens", tostring(tokens), "rhold", tostring(rhold))
return tostring(hold)'''.encode('utf8')
RATE_LIMIT_SCRIPT_HASH = sha1(RATE_LIMIT_SCRIPT).hexdigest()


def get_expected_time(key, token=1):
    now = time.time()
    try:
        result = redis_conf.evalsha(RATE_LIMIT_SCRIPT_HASH, 1, key, now, token)
    except NoScriptError:
        result = redis_conf.eval(RATE_LIMIT_SCRIPT, 1, key, now, token)

    return float(result)


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
