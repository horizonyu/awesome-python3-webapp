from orm import Model,StringField,IntegerField,BooleanField,FloatField,TextField
import time,uuid

def next_id():
    ''' produce a unique id which is used to add a primary key to every single line
    声成一个基于时间的独一无二的id，作为数据库表中每一行的主键
    time.time(): 放回当前的时间戳
    uuid4(): 是一组伪随机数，有一定的重复概率
    '''
    return '%015d%s000' %(int(time.time() * 1000),uuid.uuid4().hex)

#这是一个用户名的表
class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default= next_id(), ddl= 'varchar(50)')
    email = StringField(ddl= 'varchar(50)')
    passwd = StringField(ddl= 'carchar(50)')
    admin = BooleanField()                      #管理员，True则表示管理员，否则不是
    name = StringField(ddl= 'varchar(50)')
    image = StringField(ddl= 'varchar(500)')    #头像
    created_at = FloatField(default= time.time) #创建时间默认为是当前时间

#这是一个博客的表
class Blog(Model):
    __table__ = 'blogs'
    id = StringField(primary_key=True, default= next_id())

    user_id = StringField(ddl='varchar(50)')      #作者id
    user_name = StringField(ddl= 'carchar(50)')   #作者姓名
    user_image = StringField(ddl= 'varchar(500)') #作者上传的图片
    name = StringField(ddl= 'varchar(50)')        #文章标题
    summary = StringField(ddl= 'carchar(500)')    #文章概要
    content = TextField()                         #文章内容
    created_at = FloatField(default= time.time)

#这是一个评论的表
class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key= True, default= next_id())
    blog_id = StringField(ddl= 'varchar(50)')                   #博客id
    user_id = StringField(ddl= 'varchar(50)')                   #评论者id
    user_name = StringField(ddl= 'carchar(50)')                 #评论者姓名
    user_image = StringField(ddl= 'carchar(500)')               #评论者头像
    content = TextField()
    created_at = FloatField(default= time.time)

