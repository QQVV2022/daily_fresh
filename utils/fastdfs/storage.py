from django.conf import settings
from django.core.files.storage import Storage
from fdfs_client.client import *
# from fdfs_client.client import Fdfs_client

class MyStorage(Storage):
    def __init__(self, base_url=None,client_conf=None):
        if not client_conf:
            self.client_conf = settings.FDFS_CLIENT_CONF
        if not base_url:

            self.base_url = settings.FDFS_URL

    def _open(self,name, mode='rb'):
        pass


    def _save(self,name, content):
        '''保存文件时使用'''
        # name:你选择上传文件的名字
        # content:包含你上传文件内容的File对象

        # 创建一个Fdfs_client对象
        client = Fdfs_client('./utils/fastdfs/client.conf')
        ret = client.upload_by_buffer(content.read())

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

        file_name = ret['Remote file_id']
        return file_name

    def exists(self, name):
        return False

    def url(self, name):
        return self.base_url+name


