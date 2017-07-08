# orm- object relational mapping 对象关系映射 用于实现面向对象编程语言里不同类型系统的数据之间的转换
# 创建连接池，每一个Http请求都可以从连接池中获取数据库的连接。好处是，不必频繁的打开、关闭数据库，而是尽可能的复用。连接池由全局变量__pool存储。
import aiomysql, asyncio
import logging;

logging.basicConfig(level=logging.INFO)



async def create_pool(loop, **kv):
    '''
    :param loop:
    :param kv: 字典dict(),有一个get方法，如果dict中有对应的value值，则返回，否则返回默认值，例如下面的host，如果dict中没有，则返回localhost
    :return:
    '''
    logging.info("creating database connection pool...")
    global __pool
    __pool = await aiomysql.create_pool(
        host=kv.get('host', 'localhost'),
        port=kv.get('port', 3306),
        user=kv['user'],
        password=kv['password'],
        db=kv['db'],
        charset=kv.get('charset', 'utf8'),  # 注意此处的编码为'utf8',而不是'utf-8'
        autocommit=kv.get('autocommit', True),
        maxsize=kv.get('maxsize', 10),
        minsize=kv.get('minsize', 1),
        loop=loop
    )


# 返回影响的行数
# 定义execute函数，执行Insert delete update操作

async def execute(sql, args, autocommit=True):
    logging.info(sql)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount  # 返回受影响的行数
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected


async def select(sql, args, size=None):
    logging.info(sql, args)
    global __pool
    async with __pool.get() as conn:
        # 生成游标
        # cursor = await conn.cursor(aiomysql.DictCursor)
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 执行sql语句
            # sql语句的占位符是？ mysql语句中的占位符是 %s
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()

            # await cur.close()
            logging.info('rows return:%s' % len(rs))
            return rs

# 此函数在元类中被使用，作用是创建一定数量的占位符
def create_args_string(num):
    L = []
    # 创建指定数量的占位符
    for n in range(num):
        L.append('?')

    return ','.join(L)


# 开始编写一个简单的ORM
# 设置一个ORM需要从上层调用者的角度来看
# 首先需要考虑的是，如何建立一个User对象，然后把数据表user与之关联起来。

# ========================================Field定义区域============================================

# 首先定义Field类，负责保存数据中的字段名和字段类型
# 父定义域，可以被其他类所继承
class Field(object):
    # 定义域的初始化，包括属性(列)名，属性(列)的类型，主键，默认值
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        # 如果存在默认值，此值会在getDefault()方法中会被调用
        self.default = default

    # 定制输出信息为 类名，列的类型，列名
    def __str__(self):
        return '<%s,%s:%s>' % (self.__class__.__name__, self.column_type, self.name)


# 定义StringField
# ddl（"data definition languages" 数据定义语言），默认值是'varchar(100)', 意思是可变字长，长度为100，和char相对应，char是固定长度，字符串长度不够会自动补齐，varchar则是实际的长度，但最长不能超过规定的长度。
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        Field.__init__(self, name, ddl, primary_key, default)


# 定义BooleanField
class BooleanField(Field):
    def __init__(self, name=None, default=False):
        Field.__init__(self, name, 'boolean', False, default)


# 定义IntegerField
class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super.__init__(self, name, 'bigint', primary_key, default)


# 定义FloatField
class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        Field.__init__(self, name, 'real', primary_key, default)


# 定义TextField
class TextField(Field):
    def __init__(self, name=None, default=None):
        Field.__init__(self, name, 'text', False, default)


# ==================================Model基类区域==================================================

# 首先编写元类

# 通过元类将具体的子类如User的映射信息读出来
class ModelMetaClass(type):
    def __new__(cls, name, base, attrs):
        # 排除Model本身类
        if name == 'Model':
            return type.__new__(cls, name, base, attrs)

        # 获取表的名称
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table:%s)' % (name, tableName))

        # 获取所有的Field和主键名
        mappings = dict()
        fields = []
        primary_key = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('found mapping:%s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primary_key:
                        raise RuntimeError('Duplicate primary_key for field:%s' % k)
                    primary_key = k
                else:
                    fields.append(k)
        if not primary_key:
            raise RuntimeError('Primary key not found.')
        for k in mappings.keys():
            attrs.pop(k)

        escaped_field = list(map(lambda f: '`%s`' % f, fields))
        # 保存属性和列的映射关系
        attrs['__mappings__'] = mappings
        attrs['__table__'] = tableName
        # 主键属性名
        attrs['__primary_key__'] = primary_key
        # 除主键外的属性名
        attrs['__fields__'] = fields

        # 构造默认的SELECT INSERT UPDATE DELETE语句
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primary_key, ','.join(escaped_field), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s) ' % (
        tableName, ','.join(escaped_field), primary_key, create_args_string(len(escaped_field) + 1))

        # attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_field), primary_key, create_args_string(len(escaped_field) + 1))
        #


        attrs['__update__'] = 'update `%s` set %s where `%s` = ?' % (
        tableName, ','.join(map(lambda f: '`%s` = ? ' % (mappings.get(f).name or f), fields)), primary_key)
        attrs['__delete__'] = 'delete from `%s` where `%s` = ? ' % (tableName, primary_key)
        return type.__new__(cls, name, base, attrs)


# 所以任何继承自Model的类,如（USer）,会自动通过ModelMetaClass扫描映射关系，并存储到自身的类属性如__table__、__mappings__中。
# 然后我们在Model类中添加类方法，就可以让所有子类调用class方法。

############################################################
# 首先是定义一个所有ORM映射的基类Model
############################################################
class Model(dict, metaclass=ModelMetaClass):
    def __init__(self, **kv):
        super(Model, self).__init__(**kv)

    # 获取属性方法
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(b"'Model' object has no attribute %s" % key.encode())

    # 设置属性方法
    def __setattr__(self, key, value):
        self[key] = value

    # 获取属性值的方法
    def getValue(self, key):
        return getattr(self, key, None)

    # 获取属性值，如果没有则返回默认值
    def getValueorDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            # self.__mappings__在元类中，用于保存不同实例属性在Model基类中的映射关系
            # field 是一个定义域
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s : %s' % (key, str(value)))

                # 把默认值设为这个属性的值
                setattr(self, key, value)

        return value

    # =================在Model添加类方法，就可以让所有子类调用类方法========================================

    # 类方法装饰器，即可以不创建类实例就可以调用此方法
    @classmethod
    async def find(cls, pk):
        'find object by primary_key'
        rs = await select('%s where `%s` = ?' % (cls.__select__, cls.__primary_key), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    # findAll 根据where条件查找
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        sql = [cls.__select__]
        # 如果存在where参数，就在sql语句中添加字符串where和参数where
        if where:
            sql.append('where')
            sql.append(where)

        # 这个参数是在执行sql语句时嵌入到sql 语句中，如果为None则定义一个空列表
        if args is None:
            args = []
        # 如果有orderBy参数就在sql语句中添加字符串OrderBy和参数OrderBy,但是OrderBy是在关键字参数中定义的
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append("?")
                args.append(limit)

            if isinstance(limit, tuple) and len(limit) == 2:
                sql.append("?,?")
                # extend函数用于在列表末尾一次性增加另一个序列中的多个值（用新列表扩展原来的列表）
                args.extend(limit)

            else:
                raise ValueError("错误的limit值：%s" % limit)
        rs = await select(' '.join(sql), args)
        # **r是关键字参数，构成了一个cls类列表，其实就是一条记录对应的类实例。
        return [cls(**r) for r in rs]

    # findNumber()-根据where条件查找，但返回的是整数，适用于select count(*)类型的SQL
    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)

        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    # ======================定义Model类实例方法，可以让子类调用此实例方法=======================================
    # sava/update/remove 三个方法，需要管理员权限才能操作，所以不定义为类方法，需要创建实例后才能调用

    async def save(self):
        # 将除主键外的属性添加到args这个列表中
        args = list(map(self.getValueorDefault, self.__fields__))
        # 再把主键添加到列表的最后
        args.append(self.getValueorDefault(self.__primary_key__))

        sql = self.__insert__
        rows = await execute(self.__insert__, args)
        # 如果受影响的行数不为1，则出现错误
        if rows != 1:
            logging.warn('无法插入记录，受影响的行数：%s' % rows)


    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary_key:affected rows: %s' % rows)


    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove by primary_key:affected rows: %s' % rows)
