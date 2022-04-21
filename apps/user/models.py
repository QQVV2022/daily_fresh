# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import AbstractUser  # django自带后台管理系统里用的用户信息
from db.base_model import BaseModel  #以项目文件夹目录为准

# Create your models here.
class User(AbstractUser, BaseModel):
    class Meta:
        db_table = 'df_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name



class AddressManager(models.Manager):
    '''获取用户默认收货地址'''

    # self.model:获取self对象所在的模型类
    def get_default_address(self,user):
        try:
            addr_info = self.get(user1=user, is_default=True)
            print('the default value is %s' % addr_info.is_default)
        except Exception as ret:
            print(ret, "No data aaaaaaaa")
            addr_info = None

        return addr_info



class Address(BaseModel):
    '''地址模型类'''
    user1 = models.ForeignKey('User',related_name='user_address_user', null=True, on_delete=models.SET_NULL,verbose_name='所属账户')
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=256, verbose_name='收件地址')
    zip_code = models.CharField(max_length=6, verbose_name='邮政编码')
    phone = models.CharField(max_length=11, verbose_name='联系电话')
    is_default = models.BooleanField(default=False, verbose_name='是否默认地址')

    objects = AddressManager()

    class Meta:
        db_table = 'df_address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name


