from www import orm
from www.model import User
import sys,asyncio

async def test(loop):
    await orm.create_pool(loop, user='root', password='root', db='awesome')

    u = User(name='test', email='test@example.com', passwd='1234567890', image='about:blank')

    await u.save()



if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([test(loop)]))
    loop.close()
    if loop.is_closed():
        sys.exit(0)