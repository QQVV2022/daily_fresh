from django.conf.urls import url
from goods import views
app_name = 'goods'
urlpatterns = [
    url(r'^$', views.IndexShow.as_view(), name='index'), # 首页
    url(r'^goods/(?P<goods_id>\d+)$', views.DetailView.as_view(), name='detail'),
    url(r'^pagitest/(?P<type_id>\d+)/(?P<page_num>\d+)$', views.ListTest.as_view(), name='listtest'),
    url(r'^list/(?P<type_id>\d+)/(?P<page_num>\d+)$', views.ListView.as_view(), name='list'),  # 列表页

    url(r'^test$', views.upload_pic, name='test'),
]
