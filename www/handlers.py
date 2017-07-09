import asyncio
from www.coroweb import get, post


# 编写用于测试的URL处理函数
from www.model import User


@get('/')
async def index(request):

    users = await User.findAll()
    return {
        '__template__':'test.html',
        'users':users
    }


@get('/greeting/{name}')
async def handler_url_greeting(*, name, request):
    body = '<h1>Awesome: /greeting %s</h1>' % name
    return body


