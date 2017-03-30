# def g(x):
#     yield from range(x,0,-1)
#     # yield from range(x)
# g = g(5)
# print(list(g))

#1. 迭代器（即可指子生成器）产生的值会直接返回给调用者
#2. 任何使用send()发送给委派生成器（即外部生成器）的值被直接传递给迭代器，如果snedD的值为None，则调用迭代器的next()方法；如果不为None，则调用迭代器的send()方法。如果对迭代器的调用产生了StopIteration异常，委派生产器恢复继续执行yield from后面的语句，若迭代器产生其他异常，都传递给委派生产器。

# def accumulate():   #子生成器(迭代器)，将传进的非None值累加，若传进的值为None，则将累加的结果返回
#     total = 0
#     #7
#     while True:
#         next = yield
#         print(next)
#         if next is None:
#             return total
#         total += next
#
#
# def gathr_total(totals):   #外部生成器，将累加操作任务委托为子生成器
#     while True:
#         #5
#         total = yield from accumulate()
#         totals.append(total)
# totals = []
# acc = gathr_total(totals)
# next(acc)
# for i in range(4):
#     acc.send(i)
#
# acc.send(None)
# for i in range(5):
#     acc.send(i)
#
# acc.send(None)
#
# print(totals)
class Field(object):

    def __init__(self, name, column_type):
        self.name = name
        self.column_type = column_type

    def __str__(self):
        return '<%s:%s>' % (self.__class__.__name__, self.name)

class StringField(Field):

    def __init__(self, name):
        super(StringField, self).__init__(name, 'varchar(100)')

class IntegerField(Field):

    def __init__(self, name):
        super(IntegerField, self).__init__(name, 'bigint')

class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        if name=='Model':
            return type.__new__(cls, name, bases, attrs)
        print('Found model: %s' % name)
        mappings = dict()
        for k, v in attrs.items():
            if isinstance(v, Field):
                print('Found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
        for k in mappings.keys():
            attrs.pop(k)
        attrs['__mappings__'] = mappings # 保存属性和列的映射关系
        attrs['__table__'] = name # 假设表名和类名一致
        return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def save(self):
        fields = []
        params = []
        args = []
        for k, v in self.__mappings__.items():
            fields.append(v.name)
            params.append('?')
            args.append(getattr(self, k, None))
        sql = 'insert into %s (%s) values (%s)' % (self.__table__, ','.join(fields), ','.join(params))
        print('SQL: %s' % sql)
        print('ARGS: %s' % str(args))


class User(Model):
    # 定义类的属性到列的映射：
    id = IntegerField('id')
    name = StringField('username')
    email = StringField('email')
    password = StringField('password')

# 创建一个实例：
u = User(id=12345, name='Michael', email='test@orm.org', password='my-pwd')
# 保存到数据库：
u.save()