from django.shortcuts import render, redirect
# from django.core.urlresolvers import reverse
from django.urls import reverse

from django.views.generic import View

from user.models import User, Address   # ,AddressManager
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods

# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer1  # 需要先安装 pip install itsdangerous
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer1
from dailyfresh1 import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from celery_task.celery import send_register_active_email
from utils.mixin import LoginRequiredMixin
from django_redis import get_redis_connection
from django.core.paginator import Paginator


import re


# Create your views here.
class RegisterView(View):
    def get(self, request):
        '''获取注册页面'''
        return render(request, 'register.html')

    def post(self, request):
        '''处理注册信息'''
        username = request.POST.get('user_name')
        password = request.POST.get('user_name')
        email = request.POST.get('email')
        allow = request.POST.get('allow')  # 是否同意使用协议

        if not all([username, password, email]):  # 如果这三个参数不是都有值
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):  # 判断是否邮箱的正则表达
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 是否已经注册过
        try:
            user_exist = User.objects.get(username=username)
        except Exception as ret:  # except User.DoesNotExist
            user_exist = None
        if user_exist:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        new_user = User.objects.create_user(username, email, password)
        new_user.is_active = 0  # 默认激活，要改成不激活
        new_user.save()

        serializer = Serializer1(settings.SECRET_KEY, 3600)
        info = {'confirm':new_user.id}
        token = serializer.dumps(info)  # byte
        # print("<---%s--->"%token)
        # print("<---%s--->"%serializer.loads(token))
        token = token.decode()  # 换种形式放进链接。默认以utf8方式解码
        # try:
        #     send_mail('Subject here', 'Here is the message.', settings.EMAIL_FROM,
        #           ['liuqing6@outlook.com'], fail_silently=False)
        # except Exception as ret:
        #     print(ret)
        # print('---------------------------------')
        receivers_list = [email]
        # print(settings.EMAIL_FROM, receivers_list)
        # html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br/>' \
        #                '<a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' \
        #                % (username, token, token)
        # send_mail("Welcome to DailyFresh", "mail body", settings.EMAIL_FROM, receivers_list,
        #           html_message=html_message)  # block. solution: async
        print("-------")
        # from celery_task.celery import send_register_active_email
        send_register_active_email(receivers_list,username,token)

        # return HttpResponse('oookkk')
        # 返回应答, 跳转到首页
        return redirect(reverse('goods:index'))


class ActiveView(View):
    '''账户激活试图'''
    def get(self, request, token):
        serializer = Serializer1(settings.SECRET_KEY, 3600)
        print("我是token：" + token)
        info = serializer.loads(token)
        try:
            # token = token.encode()

            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
        except Exception as ret:
            print("-------", ret)
            return HttpResponse('激活链接已过期，请重新激活')  # 实际上需要重新再发送一次新的激活链接到用户邮箱里
        return redirect(reverse('user:login'))


class LoginView(View):
    '''用户登录页面'''

    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, "login.html", {'username':username,'checked':checked})

    def post(self,request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        checked = request.POST.get('remember')
        if not all([username, password]):
            return render(request, 'login.html', {'errmasage':'用户信息不完整'})
        else:
            # from django.contrib.auth import authenticate, login, logout  # 登入和登出

            # from django.contrib.auth.decorators import login_required  # 验证用户是否登录

            user = authenticate(username=username, password=password)  # 类型为<class 'django.contrib.auth.models.User'>

            # print(type(models.Customer.objects.get(name="赵凡")))
            # print(user,type(user))
            if user:
                if user.is_active:
                    login(request, user)  # 验证成功之后登录

                    next_url = request.GET.get('next', reverse('goods:index'))  # to get the 'next' of url, if not, set the 'next'
                    responese = redirect(next_url)

                    if checked == 'on':
                        responese.set_cookie('username', username, max_age=24 * 7 * 3600)
                    else:
                        responese.delete_cookie('username')

                    # 除了你给模板文件传递的模板变量之外，django框架会把request.user也传给模板文件, 本项目传给base模版了
                    return responese
                else:
                    return render(request, "login.html", {'errmasage':'用户未激活'})
            else:
                return render(request, "login.html", {'errmasage':'用户名或密码错误'})


class UserCenterInfo(LoginRequiredMixin, View):
    def get(self,request):
        user = request.user
        addr_info = Address.objects.get_default_address(user)
        con = get_redis_connection('default')
        history_id = 'history_%s' % user.id
        goods_li = con.lrange(history_id,0,4)
        goods_viewed = list()

        for id in goods_li:
            print("<---%s--->" % str(id))
            good = GoodsSKU.objects.get(id=id)
            goods_viewed.append(good)
            print(good.name)
        print(goods_viewed)

        # 除了你给模板文件传递的模板变量之外，django框架会把request.user也传给模板文件
        return render(request,'user_center_info.html',{'page':'info','addr_info':addr_info,'goods_viewed':goods_viewed})


class UserCenterOrder(LoginRequiredMixin, View):
    def get(self,request,page_num):
        user = request.user
        try:
            orders = OrderInfo.objects.filter(user1=user).order_by('-create_time')
        except OrderInfo.DoesNotExist:
            # 订单为空
            return render(request,'user_center_order.html', {'message':'订单为空'})

        try:
            for order in orders:
                items = OrderGoods.objects.filter(order_id=order)

                for item in items:
                    sku = GoodsSKU.objects.get(id=item.sku_id)
                    item.sku = sku
                    amount = item.count * item.price
                    item.amount = amount
                order.items = items
                order.status_name = OrderInfo.ORDER_STATUS.get(str(order.order_status))
        except Exception as e:
            # 订单有误
            return render(request,'user_center_order.html', {'message':'订单有误'})

        p = Paginator(orders, 1)
        try:
            page_num = int(page_num)
        except Exception as ret:
            page_num = 1

        if page_num > p.num_pages:
            page_num = 1

        order_page = p.get_page(page_num)

        if p.num_pages <= 5:
            p_range = p.page_range
        elif page_num < 5:
            p_range = range(1, 6)
        elif page_num > p.num_pages - 2:
            p_range = range(p.num_pages - 4, p.num_pages + 1)
        else:
            p_range = range(page_num - 2, page_num + 3)

        page_n = p.page(page_num)  # 当前页码
        context = {
            # 'orders': orders,
            'page': 'order',
            'page_n': page_n,
            'p_range': p_range,
            'order_page': order_page
        }
        return render(request, 'user_center_order.html', context)


class UserCenterSite(LoginRequiredMixin, View):
    def get(self,request):
        # try:
        #     addr_info = Address.objects.get(user1=request.user, is_default=True)
        #     print('the default value is %s' % addr_info.is_default)
        # except Exception as ret:
        #     print(ret, "No data aaaaaaaa")
        #     addr_info = None
        addr_info = Address.objects.get_default_address(request.user)
        return render(request,'user_center_site.html',{'page':'site','addr_info':addr_info})

    def post(self,request):
        receiver = request.POST.get('receiver')
        address = request.POST.get('address')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        print('Got dat')
        if not all([receiver, address, phone]):
            return render(request,'user_center_site.html',{'err':'数据不完整'})
        elif not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'err': '手机号码格式不正确'})
        else:
            user = request.user
            # try:
            #     addr_info = Address.objects.get(user1=user, is_default=True)
            #     print("2222222")
            # except Exception as ret:
            #     print(ret, "No data")
            #     addr_info = None
            addr_info = Address.objects.get_default_address(user)

            if addr_info:
                is_default = False
            else:
                is_default = True
            print("33333")
            Address.objects.create(user1=user,receiver=receiver,addr=address,zip_code=zip_code,phone=phone,is_default=is_default)
            print('444444')
            return redirect(reverse('user:user_center_site'))


class LogoutView(View):
    def get(self,request):
        logout(request)
        return redirect(reverse('goods:index'))