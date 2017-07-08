# day02. 编写web-app 骨架，框架基于asyncio

import logging;

logging.basicConfig(level=logging.INFO)
import asyncio, os, time, json
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from www.coroweb import add_static, add_routes


# 之后初始化jinja2模板
def init_jinjia2(app, **kw):
    logging.info('initing jinjia2...')
    options = dict(
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_string', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)

    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        logging.info('set jinjia templtes path: %s' % path)
        env = Environment(loader=FileSystemLoader(path), **options)
        filters = kw.get('filters', None)
        if filters is not None:
            for name, f in filters.items():
                env.filters[name] = f
    app['__templating__'] = env


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.year)


# 5. 编写中间件middlware,将返回值改为web.response，符合aiohttp的要求。
# middleware是一种拦截器，一个URL在被某个函数处理前，可以经过一系列的middleware的处理。一个middleware可以改变URL的输入、输出，甚至可以决定不继续处理而直接返回。middleware的用处就在于把通用的功能从每个URL处理函数中拿出来，集中放到一个地方。
# 在我看来，middleware的感觉有点像装饰器，这与上面编写的RequestHandler有点类似。
async def logger_factory(app, handler):
    '''
    记录url日志的logger
    '''

    async def logger_middleware(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        return await handler(request)

    return logger_middleware


async def response_factory(app, handler):
    '''
    将返回值改为web.Response对象
    '''

    async def response_middleware(request):
        logging.info('Request handler...')
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'

            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])

            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(
                    body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                return resp

        if isinstance(r, int) and r < 600 and r >= 100:
            return web.Response(r)

        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))

        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp

    return response_middleware


def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')


def hello(request):
    text = "<h1>hello %s!</h1>" % (request.match_info["name"])
    return web.Response(body=text.encode("utf-8"), content_type='text/html')


# 使用async代替@asyncio.coroutine装饰器，表示此函数需要异步运行
async def init(loop):
    app = web.Application(loop=loop, middlewares=[
        logger_factory, response_factory
    ])

    init_jinjia2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'www.handlers')
    add_static(app)

    # app.router.add_route('GET', '/', index)
    # app.router.add_route('GET', '/hello/{name}', hello)

    ##await 代替yield from ,表示要放入asyncio.get_event_loop中进行的异步操作
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server start at 127.0.0.1:9000...')
    return srv


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.run_forever()
