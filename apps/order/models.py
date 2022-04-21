from django.db import models
from db.base_model import BaseModel

# Create your models here.
class OrderInfo(BaseModel):
    PAY_METHODS = {
        '1': "货到付款",
        '2': "微信支付",
        '3': "支付宝",
        '4': '银联支付'
    }
    ORDER_STATUS = {
        '1':'待支付',
        '2':'待发货',
        '3':'待收货',
        '4':'待评价',
        '5':'已完成'
    }

    PAY_METHOD_CHOICES = (
        (1,'货到付款'),
        (2,'微信支付'),
        (3, '支付宝'),
        (4,'银联支付')
    )
    ORDER_STATUS_CHOICES = (
        (1, '待支付'),
        (2,'待发货'),
        (3, '待收货'),
        (4, '待评价'),
        (5, '已完成')
    )

    order_id = models.CharField(max_length=128, primary_key=True,verbose_name='订单ID')
    user1 = models.ForeignKey('user.User',related_name='user_orderinfo_user', null = True,on_delete=models.SET_NULL,verbose_name='用户')
    addr = models.ForeignKey('user.Address', related_name='user_orderinfo_addr',null = True,on_delete=models.SET_NULL,verbose_name='地址')
    pay_method = models.SmallIntegerField(choices=PAY_METHOD_CHOICES,default=3,verbose_name='支付方式')
    total_count = models.IntegerField(default=1, verbose_name='商品数量')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品总价')
    transit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='订单运费')
    # pay_method = models.SmallIntegerField(choices=ORDER_STATUS_CHOICES, default=3, verbose_name='订单状态')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS_CHOICES, default=1, verbose_name='订单状态')
    trade_no = models.CharField(max_length=128, default='', verbose_name='支付编号')

    class Meta:
        db_table = 'df_order_info'
        verbose_name = '订单'
        verbose_name_plural = verbose_name

class OrderGoods(BaseModel):
    order = models.ForeignKey('OrderInfo',related_name='orderinfo_ordergoods_order',null = True,on_delete=models.SET_NULL,verbose_name='订单')
    sku = models.ForeignKey('goods.GoodsSKU', related_name='goodssku_ordergoods_sku',null = True,on_delete=models.SET_NULL, verbose_name='商品SKU')
    count = models.IntegerField(default=1,verbose_name='商品数目')
    price = models.DecimalField(max_digits=10, decimal_places=2,verbose_name='商品价格')
    comment = models.CharField(max_length=256,default='', verbose_name='评论')

    class Meta:
        db_table = 'df_order_goods'
        verbose_name = '商品订单'
        verbose_name_plural = verbose_name