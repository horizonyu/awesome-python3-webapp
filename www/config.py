'''
Configurations
'''
from www import config_default


class Dict(dict):
    '''
    zip(x, y) 会生成一个可返回元组 (m, n) 的迭代器，其中m来自x，n来自y。 一旦其中某个序列迭代结束，迭代就宣告结束。 因此迭代长度跟参数中最短的那个序列长度一致。

    '''
    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

def merge(defaults, override):
        r = {}
        for k, v in defaults.items():
            if k in override:
                if isinstance(v, dict):
                    r[k] = merge(v, override[k])
                else:
                    r[k] = override[k]
            else:
                r[k] = v
        return r

def toDict(d):
    D = Dict()
    for k,v in d.items():
        D[k] = toDict(v) if isinstance(v, dict) else v

    return D

configs = config_default.configs
try:
    from www import config_override
    configs = merge(configs, config_override.configs)
except ImportError as e:
    pass

configs = toDict(configs)
