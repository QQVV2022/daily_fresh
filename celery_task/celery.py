# 使用celery
from django.core.mail import send_mail
from django.conf import settings
from celery import Celery
import time
from django.shortcuts import render
from django.template import loader, RequestContext
import os


# 在任务处理者一端加这几句
# # import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh1.settings")
# django.setup()

# 创建一个Celery类的实例对象
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/3')


# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    # 组织邮件信息
    subject = '天天生鲜欢迎信息'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (username, token, token)

    send_mail(subject, message, sender, receiver, html_message=html_message)
    time.sleep(5)

@app.task
def generate_index():
    from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, GoodsSKU, IndexTypeGoodsBanner
    '''生成静态首页，然后由nginx提供页面'''
    goods_type = GoodsType.objects.all()
    goods_banner = IndexGoodsBanner.objects.all().order_by('index')
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')

    for gtype in goods_type:
        pic_banners = IndexTypeGoodsBanner.objects.filter(type=gtype, display_type=1).order_by('index')
        title_banners = IndexTypeGoodsBanner.objects.filter(type=gtype, display_type=1).order_by('index')
        # # 获取type种类首页分类商品的图片展示信息
        # image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # # 获取type种类首页分类商品的文字展示信息
        # title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        gtype.pic_banners = pic_banners
        gtype.title_banners = title_banners
        cart_count = 0

    # user = request.user
    # if user.is_authenticated:
    #     cart_key = 'cart_%s' % user.id
    #     conn = get_redis_connection('default')
    #     cart_count = conn.hlen(cart_key)

    context = {'goods_type': goods_type,
               'goods_banner': goods_banner,
               'promotion_banner': promotion_banner,
               'cart_count': cart_count}

    temp = loader.get_template('index_static.html')
    static_index_html = temp.render(context)

    with open(os.path.join(settings.BASE_DIR, 'static/index.html'), 'w') as f:
        f.write(static_index_html)



