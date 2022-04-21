from django.shortcuts import render, redirect
from django.urls import reverse
import os

from django.core.paginator import Paginator
from fdfs_client.client import Fdfs_client
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, GoodsSKU, IndexTypeGoodsBanner
from order.models import OrderGoods
from django_redis import get_redis_connection
from django.core.cache import cache
from django.views.generic import View


# Create your views here.
# http://127.0.0.1:8000
class IndexShow(View):
    def get(self, request):
        '''首页'''

        context = cache.get('index_page_data')

        if not context:
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

            context = {'goods_type': goods_type,
                       'goods_banner': goods_banner,
                       'promotion_banner': promotion_banner
                       }
            cache.set('index_page_data', context, 3600)

        cart_count = 0
        user = request.user
        if user.is_authenticated:
            cart_key = 'cart_%s' % user.id
            conn = get_redis_connection('default')
            cart_count = conn.hlen(cart_key)

        context.update(cart_count=cart_count)
        # context = {'goods_type': goods_type,
        #            'goods_banner': goods_banner,
        #            'promotion_banner': promotion_banner,
        #            'cart_count': cart_count}

        return render(request, 'index.html', context)


class DetailView(View):

    def get(self, request, goods_id):
        try:
            good = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))

        same_type_goods = GoodsSKU.objects.filter(goods1=good.goods1).exclude(id=good.id)
        newest_goods = GoodsSKU.objects.filter(type=good.type).exclude(id=good.id).order_by('-create_time')[:2]  # -表示降序
        good_orders = OrderGoods.objects.filter(sku=good).exclude(comment='')

        user = request.user
        cart_count = 0

        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            conn = get_redis_connection('default')
            history_id = 'history_%s' % user.id
            conn.lrem(history_id, 0, goods_id)
            conn.lpush(history_id, goods_id)
            conn.ltrim(history_id, 0, 4)

        context = {'good': good,
                   'same_type_goods': same_type_goods,
                   'newest_goods': newest_goods,
                   'good_orders': good_orders,
                   'cart_count': cart_count}

        return render(request, "detail.html", context)


class ListView(View):

    def get(self, request, type_id, page_num):
        # print("start--------")
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            # 种类不存在
            return redirect(reverse('goods:index'))

        cart_count = 0
        user = request.user

        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        sort = request.GET.get('sort')

        if sort == 'price':
            sku_goods = GoodsSKU.objects.filter(type=type_id).order_by('price')
        elif sort == 'hot':
            sku_goods = GoodsSKU.objects.filter(type=type_id).order_by('-create_time')
        else:
            sort = 'default'
            sku_goods = GoodsSKU.objects.filter(type=type_id).order_by('-id')

        types = GoodsType.objects.all()
        newest_goods = GoodsSKU.objects.filter(type=type_id).order_by('-create_time')[:2]  # -表示降序

        paginator = Paginator(sku_goods, 1)  # 对数据进行分页
        # paginator = Paginator(sku_goods, 1)

        try:
            page_num = int(page_num)
        except Exception as ret:
            page_num = 1

        if page_num > paginator.num_pages:
            page_num = 1

        sku_goods_page = paginator.get_page(page_num)

        if page_num < 5:
            p_range = range(1, 6)
        elif page_num > paginator.num_pages - 2:
            p_range = range(paginator.num_pages - 4, paginator.num_pages + 1 )
        else:
            p_range = range(page_num-2, page_num + 3)

        context = {'cart_count': cart_count,
                   # 'sku_goods': sku_goods,
                   'newest_goods': newest_goods,
                   'type': type,
                   'types': types,
                   'p_range': p_range,
                   'sort': sort,
                   'sku_goods_page': sku_goods_page,
                   }

        return render(request, 'list.html', context)





class ListTest(View):

    def get(self, request, type_id, page_num):

        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            # 种类不存在
            return redirect(reverse('goods:index'))
        sort = request.GET.get('sort')

        if sort == 'price':
            sku_goods = GoodsSKU.objects.filter(type=type_id).order_by('price')
        elif sort == 'hot':
            sku_goods = GoodsSKU.objects.filter(type=type_id).order_by('-create_time')
        else:
            sort = 'default'
            sku_goods = GoodsSKU.objects.filter(type=type_id).order_by('-id')

        newest_goods = GoodsSKU.objects.filter(type=type_id).order_by('-create_time')[:2]  # -表示降序
        types = GoodsType.objects.all()

        cart_count = 0
        user = request.user

        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)


        p = Paginator(sku_goods, 1)
        try:
            page_num = int(page_num)
        except Exception as ret:
            page_num = 1

        if page_num > p.num_pages:
            page_num = 1

        page1 = p.page(page_num)
        return render(request, 'pagitest.html', {'page1':page1,
                                                 'type':type,
                                                 'sort': sort,
                                                 'cart_count':cart_count,
                                                 'newest_goods':newest_goods,
                                                 'types': types})


def upload_pic(request):
    folder_path = './static/images/goods/'
    files = os.listdir(folder_path)
    client = Fdfs_client('./utils/fastdfs/client.conf')
    success_file_name = []

    for f in files:

        if f != 'goods':
            with open(folder_path + f, 'rb') as file:
                pic_content = file.read()
                ret = client.upload_by_buffer(pic_content)

        # dict
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # }

        if ret['Status'] != 'Upload successed.':
            raise Exception("上传文件到fast dfs失败")

        success_file_name.append(ret['Remote file_id'])

    return render(request, 'test.html', {'pictures': files, 'success_file_name': success_file_name})
