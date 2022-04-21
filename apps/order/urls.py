from django.conf.urls import url
from order.views import PlaceOrderView, OrderCommitView, OrderPayView, OrderCheckView, CommentView

app_name = 'order'
urlpatterns = [
    url(r'^place$', PlaceOrderView.as_view(), name='place'),  # cart提交订单
    url(r'^commit$', OrderCommitView.as_view(), name='commit'),  # 提交订单
    url(r'^pay$', OrderPayView.as_view(), name='pay'),  # to pay
    url(r'^check$', OrderCheckView.as_view(), name='check'),  # to check payment
    url(r'comment/(?P<order_id>\d+)$', CommentView.as_view(), name='comment')

]
