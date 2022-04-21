from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse

from django.views.generic import View
from django_redis import get_redis_connection
import time
from django.db import transaction
from alipay import AliPay
import os

from goods.models import GoodsSKU
from user.models import Address
from order.models import OrderInfo, OrderGoods

from utils.mixin import LoginRequiredMixin



# Create your views here.


class PlaceOrderView(LoginRequiredMixin, View):

    def post(self, request):
        #  接收被选中的商品ID，前端每个商品复选框都设置一个属性存sku_id值，用于接收商品id
        print("start------")
        user = request.user
        # if not user.is_authenticated:
        #     return redirect(reversed('user:login'))  # 从哪个页面来回哪个页面去。因此只需要返回数据即可

        good_ids = request.POST.getlist('goods_ids')

        if not good_ids:
            return redirect(reverse('cart:mycart'))

        for good_id in good_ids:
            try:
                good_sku = GoodsSKU.objects.get(id=good_id)
            except Exception as e:
                print("商品查询是否存在报错：%s" % e)
                return redirect(reverse('cart:mycart'))
        print("start---4---")
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # sku_goods = conn.hgetall(cart_key)

        total_count = 0
        total_all_price = 0

        goods = list()

        for good_id in good_ids:
            cart_count = conn.hget(cart_key, good_id)

            good = GoodsSKU.objects.get(id=good_id)

            good.cart_count = int(cart_count)
            total_price = int(cart_count) * good.price
            good.total_price = total_price

            total_count += good.cart_count
            total_all_price += total_price
            goods.append(good)
            # print("购物车页面%s, %s, %s" % (good_id, cart_count, total_price))

            # 运费:实际开发的时候，属于一个子系统
            transit_price = 10  # 写死

            # 实付款
            total_pay = total_all_price + transit_price

            # 获取用户的收件地址
            addrs = Address.objects.filter(user1=user)

            # 组织上下文
            goods_ids = ','.join(good_ids)  # [1,25]->1,25

            context = {'goods': goods,
                       'total_count': total_count,
                       'total_all_price': total_all_price,
                       'transit_price': transit_price,
                       'total_pay': total_pay,
                       'addrs': addrs,
                       'goods_ids': goods_ids}

            # 使用模板
        return render(request, 'place_order.html', context)


# 悲观锁
class OrderCommitView1(View):

    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'ret': 0, 'error_massage': '请登录'})

        pay_method = request.POST.get('pay_method')
        goods_ids = request.POST.get('goods_ids')
        addr_id = request.POST.get('addr_id')

        if not all([pay_method, goods_ids, addr_id]):
            return JsonResponse({'ret': 1, 'error_massage': '数据不完整'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'ret': 2, 'error_massage': '支付方式不正确'})

        try:
            addr = Address.objects.get(id=addr_id)

        except Address.DoesNotExist:
            return JsonResponse({'ret': 3, 'error_massage': '收货地址不正确'})

        goods_ids_list = goods_ids.split(',')

        total_count = 0
        total_price = 0
        transit_price = 10

        # order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
        order_id = time.strftime("%Y%m%d%H%M%S", time.localtime()) + str(user.id)
        print(order_id)

        saving_id = transaction.savepoint()

        order = OrderInfo.objects.create(order_id=order_id,
                                         user1=user,
                                         addr=addr,
                                         pay_method=pay_method,
                                         total_count=total_count,
                                         total_price=total_price,
                                         transit_price=transit_price)

        try:
            for item_id in goods_ids_list:
                try:
                    # good = GoodsSKU.objects.get(id = item_id)
                    good = GoodsSKU.objects.select_for_update().get(id=item_id)  # 上锁
                except GoodsSKU.DoesNotExist:
                    transaction.savepoint_rollback(saving_id)  # 回滚事务
                    return JsonResponse({'ret': 4, 'error_massage': '商品不存在'})

                conn = get_redis_connection('default')
                cart_key = 'cart_%d' % user.id

                count = conn.hget(cart_key, item_id)
                if not count:
                    transaction.savepoint_rollback(saving_id)  # 回滚事务
                    return JsonResponse({'ret': 6, 'error_massage': '商品数量有误'})

                if int(count) > good.stock:
                    transaction.savepoint_rollback(saving_id)  # 回滚事务
                    return JsonResponse({'ret': 7, 'error_massage': '商品库存不足'})

                total_price += int(count) * good.price
                total_count += int(count)

                # print('user:%d stock:%d' % (user.id, good.stock))
                # time.sleep(10)

                good.stock -= int(count)
                good.sales += int(count)
                good.save()


                # print("user id: %d, stock: %d"%(user.id, good.stock))

                OrderGoods.objects.create(
                    order = order,
                    sku = good,
                    count = total_count,
                    price = total_price
                )
            order.total_count = total_count
            order.total_price = total_price
            order.save()

        except Exception as e:
            transaction.savepoint_rollback(saving_id)  # 回滚事务
            return JsonResponse({'ret': 8, 'error_massage': '订单失败'})

        transaction.savepoint_commit(saving_id)  # 提交事务

        print("------finish-------")
        for good in goods_ids:
            conn.hdel(cart_key, good)

        # 清除用户购物车中对应的记录
        # conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'ret': 5, 'message': '创建成功'})

# 乐观锁
class OrderCommitView(View):

    @transaction.atomic
    def post(self, request):
        print("**********************************************************")
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'ret': 0, 'error_massage': '请登录'})

        pay_method = request.POST.get('pay_method')
        goods_ids = request.POST.get('goods_ids')
        addr_id = request.POST.get('addr_id')

        if not all([pay_method, goods_ids, addr_id]):
            return JsonResponse({'ret': 1, 'error_massage': '数据不完整'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'ret': 2, 'error_massage': '支付方式不正确'})

        try:
            addr = Address.objects.get(id=addr_id)

        except Address.DoesNotExist:
            return JsonResponse({'ret': 3, 'error_massage': '收货地址不正确'})

        goods_ids_list = goods_ids.split(',')

        total_count = 0
        total_price = 0
        transit_price = 10

        # order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
        order_id = time.strftime("%Y%m%d%H%M%S", time.localtime()) + str(user.id)
        print(order_id)

        saving_id = transaction.savepoint()

        # 更新订单信息表中的商品的总数量和总价格
        order = OrderInfo.objects.create(order_id=order_id,
                                         user1=user,
                                         addr=addr,
                                         pay_method=pay_method,
                                         total_count=total_count,
                                         total_price=total_price,
                                         transit_price=transit_price)

        try:
            for item_id in goods_ids_list:
                for i in range(3):
                    try:
                        good = GoodsSKU.objects.get(id=item_id)
                        # good = GoodsSKU.objects.select_for_update().get(id=item_id)  # 上锁
                    except GoodsSKU.DoesNotExist:
                        transaction.savepoint_rollback(saving_id)  # 回滚事务
                        return JsonResponse({'ret': 4, 'error_massage': '商品不存在'})

                    conn = get_redis_connection('default')
                    cart_key = 'cart_%d' % user.id

                    count = conn.hget(cart_key, item_id)
                    if not count:
                        transaction.savepoint_rollback(saving_id)  # 回滚事务
                        return JsonResponse({'ret': 6, 'error_massage': '购物车商品数量有误'})

                    if int(count) > good.stock:
                        transaction.savepoint_rollback(saving_id)  # 回滚事务
                        return JsonResponse({'ret': 7, 'error_massage': '商品库存不足'})
                    if i == 0:
                        total_price += int(count) * good.price
                        total_count += int(count)

                        # print('user:%d stock:%d' % (user.id, good.stock))
                        original_stock = good.stock
                        new_stock = good.stock - int(count)
                        new_sales = good.sales + int(count)

                    print("user id: %d, ori_stock: %d, count: %d/%s, i=%d" % (user.id, original_stock, int(count),item_id,i))
                    # time.sleep(10)

                    # 返回受影响的行数--乐观锁
                    res = GoodsSKU.objects.filter(id=good.id, stock=original_stock).update(stock=new_stock, sales=new_sales)
                    print(res, i,'========')
                    if res == 0:
                        if i == 2:
                            transaction.savepoint_rollback(saving_id)  # 回滚事务
                            return JsonResponse({'ret': 8, 'error_massage': '订单失败222222'})
                    else:

                        OrderGoods.objects.create(
                            order = order,
                            sku = good,
                            count = count,
                            price = good.price
                        )
                        break


            order.total_count = total_count
            order.total_price = total_price + transit_price
            order.save()

        except Exception as e:
            transaction.savepoint_rollback(saving_id)  # 回滚事务
            print(e)
            return JsonResponse({'ret': 8, 'error_massage': '订单失败'})

        transaction.savepoint_commit(saving_id)  # 提交事务

        print("------finish-------", user.id)
        for item_id in goods_ids_list:
            conn.hdel(cart_key, item_id)

        # 清除用户购物车中对应的记录
        # conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'ret': 5, 'message': '创建成功'})



class OrderCommitView3(View):
    '''订单创建'''
    @transaction.atomic
    def post(self, request):

        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res':0, 'error_massage':'用户未登录'})

        # 接收参数

        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('goods_ids')
        addr_id = request.POST.get('addr_id')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res':1, 'error_massage':'参数不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res':2, 'error_massage':'非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            # 地址不存在
            return JsonResponse({'res':3, 'error_massage':'地址非法'})

        # todo: 创建订单核心业务

        # 组织参数
        # 订单id: 20171122181630+用户id
        order_id = time.strftime("%Y%m%d%H%M%S", time.localtime()) + str(user.id)

        # 运费
        transit_price = 10

        # 总数目和总金额
        total_count = 0
        total_price = 0

        # 设置事务保存点
        save_id = transaction.savepoint()
        try:
            # todo: 向df_order_info表中添加一条记录


            # todo: 用户的订单中有几个商品，需要向df_order_goods表中加入几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id

            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                for i in range(3):
                    # 获取商品的信息
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except:
                        # 商品不存在
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res':4, 'error_massage':'商品不存在'})

                    # 从redis中获取用户所要购买的商品的数量
                    count = conn.hget(cart_key, sku_id)

                    # todo: 判断商品的库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res':6, 'error_massage':'商品库存不足'})

                    # todo: 更新商品的库存和销量
                    orgin_stock = sku.stock
                    new_stock = orgin_stock - int(count)
                    new_sales = sku.sales + int(count)

                    # 返回受影响的行数
                    res = GoodsSKU.objects.filter(id=sku_id, stock=orgin_stock).update(stock=new_stock, sales=new_sales)

                    print("user id: %d, ori_stock: %d， res：%d" % (user.id, orgin_stock, res))
                    time.sleep(10)

                    if res == 0:
                        if i == 2:
                            # 尝试的第3次
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 7, 'error_massage': '下单失败2'})
                        continue

                    order = OrderInfo.objects.create(order_id=order_id,
                                                     user1=user,
                                                     addr=addr,
                                                     pay_method=pay_method,
                                                     total_count=total_count,
                                                     total_price=total_price,
                                                     transit_price=transit_price)

                    # todo: 向df_order_goods表中添加一条记录
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)

                    # todo: 累加计算订单商品的总数量和总价格
                    amount = sku.price*int(count)
                    total_count += int(count)
                    total_price += amount

                    # 跳出循环
                    break

            #  更新订单信息表中的商品的总数量和总价格

            # order.total_count = total_count
            # order.total_price = total_price
            # order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res':7, 'error_massage':'下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)

        # 清除用户购物车中对应的记录
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res':5, 'message':'创建成功'})


# ajax post
# 前端传递的参数:订单id(order_id)
# /order/pay
class OrderPayView(View):
    def post(self, request):
        '''order to pay'''
        # log in or not
        # print('1111111')
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': 'User does not log in!'})
        # To get Order id
        order_id = request.POST.get('order_id')
        print('2222'+order_id)
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': 'Invalid Order ID!'})

        try:
            order = OrderInfo.objects.get(order_id = order_id,
                                          user1 = user,
                                          pay_method = 3,
                                          order_status = 1)
            print(order)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': 'Order Error!'})



        # app_private_key_path = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        # alipay_public_key_path = os.path.join(settings.BASE_DIR, 'apps/order/apppay_public_key.pem'),

        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/apppay_public_key.pem')).read()

        print(app_private_key_string)
        print(alipay_public_key_string)

        alipay = AliPay(
            appid="2016101900724322",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = True  # 默认False
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price  # + order.transit_price

        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=str(order_id),
            total_amount=str(total_pay),
            subject="DailyFresh"+str(order_id),
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})

# /order/check
class OrderCheckView(View):
    def post(self, request):
        '''order to pay'''
        # log in or not
        print('start checking...................')
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': 'User does not log in!'})
        # To get Order id
        order_id = request.POST.get('order_id')

        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': 'Invalid Order ID!'})

        try:
            order = OrderInfo.objects.get(order_id = order_id,
                                          user1 = user,
                                          pay_method = 3,
                                          order_status = 1)
            # print(order)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': 'Order Error!'})



        # app_private_key_path = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        # alipay_public_key_path = os.path.join(settings.BASE_DIR, 'apps/order/apppay_public_key.pem'),

        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/apppay_public_key.pem')).read()

        alipay = AliPay(
            appid="2016101900724322",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = True  # 默认False
        )

        # 调用支付宝的交易查询接口
        """
        response = {
            "trade_no": # 支付宝交易号
            "code": "10000" # 接口调用是否成功
            "trade_status": "TRADE_SUCCESS" # 支付成功
        }
        """


        while True:
            # response = alipay.api_alipay_trade_query(out_trade_no=order_id)
            print('aaaaaaaaaa', order_id)
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            response = alipay.api_alipay_trade_query(out_trade_no=str(order_id))
            print("response:ok")
            code = response.get('code')
            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get("trade_no")
                # 更新订单状态

                order.trade_no = trade_no
                order.order_status = 4  # 待评价
                order.save()

                # 返回结果
                return JsonResponse({'res': 3, 'message': '支付成功'})
            elif code == '40004' or (code == '10000' and response.get("trade_status") == 'WAIT_BUYER_PAY'):
                # 等待买家付款
                # 业务处理失败， 可能一会就会成功
                import time
                time.sleep(5)
                print('NotPayYet')
                continue
            else:
                # 支付出错
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})



class CommentView(LoginRequiredMixin, View):

    def get(self, request, order_id):
        user = request.user
        if not order_id:
            return redirect(reverse('user:user_center_order', kwargs={"page_num": 1}))

        try:
            order = OrderInfo.objects.get(order_id = order_id,
                                          user1 = user,
                                          order_status = '4')
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:user_center_order', kwargs={"page_num": 1}))

        try:
            items = OrderGoods.objects.filter(order_id=order_id)
            for item in items:
                sku = GoodsSKU.objects.get(id=item.sku_id)
                item.sku = sku
                amount = item.count * item.price
                item.amount = amount
            order.items = items

        except OrderGoods.DoesNotExist:
            return redirect(reverse('user:user_center_order', kwargs={"page_num": 1}))

        return render(request, 'order_comment.html', {'order': order})


    def post(self, request, order_id):
        print("开始了吗")
        user = request.user

        items_count = request.POST.get("items_count")
        items_count = int(items_count)

        # order_id = request.POST.get('order_id')
        if not order_id:
            return redirect(reverse('user:user_center_order', kwargs={"page_num": 1}))

        try:
            order = OrderInfo.objects.get(order_id = order_id,
                                          user1 = user,
                                          order_status = '4')
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:user_center_order', kwargs={"page_num": 1}))

        items_count_num = items_count + 1
        print(items_count_num)
        for i in range(1, items_count_num):
            try:
                comment = request.POST.get("content_%d" % i)
                sku_id = request.POST.get("item_%d" % i)
                print("sku_id is %s, comment id %s" % (sku_id, comment))
                item = OrderGoods.objects.get(order=order, sku_id=sku_id)
                item.comment = comment
                print(item, comment)
                item.save()

            except OrderGoods.DoesNotExist:
                print('失败哈哈哈哈哈哈哈')
                continue
        order.order_status = 5
        order.save()

        return redirect(reverse('user:user_center_order', kwargs={"page_num": 1}))







