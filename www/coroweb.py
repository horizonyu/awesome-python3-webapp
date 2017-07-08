__author__ = 'H'
import functools, inspect
import logging, os
import asyncio
import json, time

from aiohttp import web
from urllib import parse
from www.apis import APIError



# 1. 需要将函数映射为URL处理函数
# def get(path):
#     '''
#     Define decorator  @get('/path')
#     :param path:
#     :return:
#     '''
#
#     def decorator(func):
#         @functools.wraps(func)
#         def wrapper(*args, **kv):
#             return func(*args, **kv)
#
#         wrapper.__method__ = 'GET'
#         wrapper.__route__ = path
#         return wrapper
#
#     return decorator
#
#
# def post(path):
#     '''
#     Define decorator @post('/path')
#     :param path:
#     :return:
#     '''
#
#     def decorator(func):
#         @functools.wraps(func)
#         def wrapper(*args, **kv):
#             return func(*args, **kv)
#
#         wrapper.__method__ = 'POST'
#         wrapper.__route__ = path
#         return wrapper
#
#     return decorator

def Handler_decorator(path, *, method):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = method
        wrapper.__route__ = path
        return wrapper
    return decorator
get = functools.partial(Handler_decorator, method='GET')
post = functools.partial(Handler_decorator, method='POST')

# 2. 使用RequestHandler封装URL处理函数
def get_requried_kw_args(fn):
    '''
    收集没有默认值的命名关键字参数
    :param fn:
    :return:
    '''
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if str(param.kind) == 'KEYWORD_ONLY' and param.default == inspect.Parameter.empty:
            args.append(name)

    return tuple(args)


def get_named_kw_args(fn):
    '''
    获取命名关键字参数
    :param fn:
    :return:
    '''
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if str(param.kind) == 'KEYWORD_ONLY':
            args.append(name)

    return tuple(args)


def has_named_kw_args(fn):
    '''
    判断有没有命名关键字参数
    :param fn:
    :return:
    '''
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if str(param.kind) == 'KEYWORD_ONLY':
            return True


def has_var_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if str(param.kind) == 'VAR_KEYWORD':
            return True


def has_request_args(fn):
    '''
    判断是否含有名字为'request'的参数，且该参数为最后一个参数
    :param fn:
    :return:
    '''
    params = inspect.signature(fn).parameters
    sig = inspect.signature(fn)
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (str(param.kind) != 'VAR_POSITIONAL' and str(param.kind) != 'KEYWORD_ONLY' and str(
                param.kind) == 'VAR_KEYWORD'):
            raise ValueError(
                'request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))

        return found


# 目的： 从URL函数中分析其需要接收的参数，向request获取url处理函数所需的参数,从未调用定义的处理函数
class RequestsHandler(object):
    def __init__(self, app, fn):
        '''
        接收app参数
        '''
        self.app = app
        self._fn = fn
        self._required_kw_args = get_requried_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._has_var_kw_args = has_var_kw_args(fn)
        self._has_request_args = has_request_args(fn)

    async def __call__(self, request):
        '''
        构造协程
        :param request:
        :return:
        '''
        kw = None

        if self._has_var_kw_args or self._has_named_kw_args:
            if request.method == 'POST':
                # 判断客户端发来的方法是否为空
                if not request.content_type:
                    # 查询有没有提交数据的格式
                    return web.HTTPBadRequest(text='Missing Content Type.')
                ct = request.content_type.lower()  # 小写
                if ct.startswith('application/json'):
                    params = await request.json()  # Read request body, decoded as json
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest(text='JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()  # Read post params from post body.If method is not POST, PUT, PATCH, TRACE or DELETE or content_type is not empty or application/x-www-form-urlencoded or multipart/form-data returns empty multidict.
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest(text='Unsupported Content Type: %s' % (request.content_type))

            if request.method == 'GET':
                qs = request.query_string  # The query string in the URL
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True):
                        kw[k] = v[0]

        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_args and self._has_named_kw_args:
                # 当函数参数没有关键字参数时，移去request除命名关键字参数所有的参数信息
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy

            for k, v in request.math_info.items():
                # 检查命名关键字参数
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)

                kw[k] = v
            if self._has_request_args:
                kw['request'] = request
            if self._required_kw_args:
                # 假如命名关键字参数(没有附加默认值)，request没有提供相应的数值，报错
                for name in self._required_kw_args:
                    if name not in kw:
                        return web.HTTPBadRequest(text='Missing argument: %s' % (name))
            logging.info('call with args: %s' % str(kw))

        try:
            r = await self._fn(**kw)
            return r
        except APIError as e:
            return dict(error=e.erro, message=e.message)


# 3. 注册URL处理函数
def add_route(app, fn):
    '''
    注册一个URL处理函数
    :param app:
    :param fn:
    :return:
    '''
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if method is None or path is None:
        return ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        # 判断是否为协程且生成器,不是使用isinstance
        fn = asyncio.coroutine(fn)
    logging.info(
        'add route %s %s => %s(%s)' % (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestsHandler(app, fn))


def add_routes(app, moudle_name):
    '''
    直接导入需要处理的函数所在的文件，批量注册多个URL处理函数
    :param app:
    :param moudle_name: 函数所在的文件
    :return:
    '''
    # Python rfind() 返回字符串最后一次出现的位置(从右向左查询)，如果没有匹配项则返回-1。
    n = moudle_name.rfind('.')
    if n == -1:
        mod = __import__(moudle_name, globals(), locals())
    else:
        name = moudle_name[n + 1:]
        # 第一个参数为文件路径参数，不能掺夹函数名，类名，获取所有的属性集合
        mod = getattr(__import__(moudle_name[:n], globals(), locals(), [name], 0), name)

    #依次获取处理url函数的方法类型以及对应的路由
    for attr in dir(mod):
        #查找所需的属性，遇到内置属性则跳过
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)


# 4. 添加静态文件，初始胡jinja2
# 添加静态文件夹路径
def add_static(app):
    # 当前文件夹中'static'的路径
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))


