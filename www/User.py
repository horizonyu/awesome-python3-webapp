from www import orm
from www.model import User
import sys,asyncio

async def test(loop):
    await orm.create_pool(loop, user='root', password='root', db='awesome')

    user = await User.findAll()
    for u in user:
        print(u.name, ',' , u.email)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([test(loop)]))
    loop.close()
    if loop.is_closed():
        sys.exit(0)