from django.conf.urls import url
from cart.views import CartAddView, ShowCart, UpdateView, RemoveView

app_name = 'cart'
urlpatterns = [
    url(r'^mycart$', ShowCart.as_view(), name='mycart'),

    url(r'^add$', CartAddView.as_view(), name='add'),  # 购物车记录添加

    url(r'^update$', UpdateView.as_view(), name='update'),  # 购物车记录update
    url(r'^remove$', RemoveView.as_view(), name='remove'),  # 购物车记录remove


]
