from django.shortcuts import render, redirect
from django.views.generic import View
from django_redis import get_redis_connection
from django.http import JsonResponse
from goods.models import GoodsSKU
from utils.mixin import LoginRequiredMixin


# Create your views here.
class CartAddView(View):

    def post(self, request):
        """0 是否登陆 1 接受的数据不完整 2 商品数量是否有误 3 是否有该商品存在 4 是否超出库存 """

        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'ret': 0, 'error_massage': '请登录'})  # 从哪个页面来回哪个页面去。因此只需要返回数据即可

        good_id = request.POST.get('good_id')
        count = request.POST.get('count')
        if not all([good_id, count]):
            return JsonResponse({'ret': 1, 'error_massage': '数据不完整'})

        try:
            count = int(count)
        except Exception as e:
            print("商品数量报错：%s" % e)
            return JsonResponse({'ret': 2, 'error_massage': '商品数量有误'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        try:
            good_sku = GoodsSKU.objects.get(id = good_id)
        except Exception as e:
            print("商品查询是否存在报错：%s" % e)
            return JsonResponse({'ret': 3, 'error_massage': '商品不存在'})

        good_stock = good_sku.stock
        cart_count = conn.hget(cart_key, good_id)
        print("redis:%s" % cart_count)
        if cart_count:
            count = count + int(cart_count)

        if count > good_stock:
            return JsonResponse({'ret': 4, 'error_massage': '商品库存不足'})

        conn.hset(cart_key, good_id, count)
        total_count = conn.hlen(cart_key)

        print(total_count)

        return JsonResponse({'ret': 5, 'total_count': total_count, 'massage': '添加成功'})




class ShowCart(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        sku_goods = conn.hgetall(cart_key)

        total_count = 0
        total_all_price = 0

        goods = list()

        for good_id, cart_count in sku_goods.items():
            # print("购物车页面%s, %s" % (good_id,cart_count))
            good = GoodsSKU.objects.get(id=good_id)

            good.cart_count = int(cart_count)
            total_price = int(cart_count) * good.price
            good.total_price = total_price

            total_count += good.cart_count
            total_all_price += total_price
            goods.append(good)
            # print("购物车页面%s, %s, %s" % (good_id, cart_count, total_price))

        context = {"goods":goods,
                   'total_count': total_count,
                   'total_all_price': total_all_price}

        return render(request,'cart.html', context)


class UpdateView(View):
    def post(self, request):
        """0 是否登陆 1 接受的数据不完整 2 商品数量是否有误 3 是否有该商品存在 4 是否超出库存 """
        # print("2222")
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'ret': 0, 'error_massage': '请登录'})  # 从哪个页面来回哪个页面去。因此只需要返回数据即可

        good_id = request.POST.get('good_id')
        count = request.POST.get('count')
        if not all([good_id, count]):
            return JsonResponse({'ret': 1, 'error_massage': '数据不完整'})

        try:
            count = int(count)
        except Exception as e:
            print("商品数量报错：%s" % e)
            return JsonResponse({'ret': 2, 'error_massage': '商品数量有误'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        try:
            good_sku = GoodsSKU.objects.get(id=good_id)
        except Exception as e:
            print("商品查询是否存在报错：%s" % e)
            return JsonResponse({'ret': 3, 'error_massage': '商品不存在'})

        good_stock = good_sku.stock

        if count > good_stock:
            return JsonResponse({'ret': 4, 'error_massage': '商品库存不足'})

        conn.hset(cart_key, good_id, count)

        total_count = 0

        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        total_price = good_sku.price * count  # 单个商品的总价格
        # print(count, total_price)

        return JsonResponse({'ret': 5,
                             'total_price': total_price,
                             'total_count': total_count,
                             'massage': '添加成功'})


class RemoveView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'ret': 0, 'error_massage': '请登录'})  # 从哪个页面来回哪个页面去。因此只需要返回数据即可

        good_id = request.POST.get('good_id')
        if not good_id:
            return JsonResponse({'ret': 1, 'error_massage': '商品id无效'})

        try:
            good_sku = GoodsSKU.objects.get(id=good_id)
        except Exception as e:
            print("商品查询是否存在报错：%s" % e)
            return JsonResponse({'ret': 2, 'error_massage': '商品不存在'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        conn.hdel(cart_key, good_id)

        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'ret': 3,
                             'total_count': total_count,
                             'massage': '删除成功'})


