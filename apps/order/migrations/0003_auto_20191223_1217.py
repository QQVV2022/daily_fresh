# Generated by Django 2.2.7 on 2019-12-23 04:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0002_auto_20191113_2205'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderinfo',
            name='order_status',
            field=models.SmallIntegerField(choices=[(1, '待支付'), (2, '待发货'), (3, '待收货'), (4, '已完成')], default=1, verbose_name='订单状态'),
        ),
        migrations.AlterField(
            model_name='ordergoods',
            name='comment',
            field=models.CharField(default='', max_length=256, verbose_name='评论'),
        ),
        migrations.AlterField(
            model_name='orderinfo',
            name='pay_method',
            field=models.SmallIntegerField(choices=[(1, '货到付款'), (2, '微信支付'), (3, '支付宝'), (4, '银联支付')], default=3, verbose_name='支付方式'),
        ),
        migrations.AlterField(
            model_name='orderinfo',
            name='trade_no',
            field=models.CharField(default='', max_length=128, verbose_name='支付编号'),
        ),
    ]
