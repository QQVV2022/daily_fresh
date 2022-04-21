from django.conf.urls import url
# from user.views import RegisterView
from apps.user.views import RegisterView, ActiveView, LoginView, LogoutView, UserCenterInfo, UserCenterOrder, UserCenterSite
from django.contrib.auth.decorators import login_required

app_name = 'user'

urlpatterns = [
    # url(r'^register$', views.register, name='register'), # 注册
    # url(r'^register_handle$', views.register_handle, name='register_handle'), # 注册处理
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),
    url(r'^register$', RegisterView.as_view(), name='register'),  # 注册
    # url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'), # 用户激活
    # url(r'^login$', LoginView.as_view(), name='login'), # 登录
    url(r'^login$', LoginView.as_view(), name='login'),
    url(r'^logout$', LogoutView.as_view(), name='logout'),
    url(r'^user_center_info$', UserCenterInfo.as_view(), name='user_center_info'),
    url(r'^user_center_order/(?P<page_num>\d+)$', UserCenterOrder.as_view(), name='user_center_order'),
    url(r'^user_center_site$', UserCenterSite.as_view(), name='user_center_site'),

    # url(r'^user_center_info$', login_required(UserCenterInfo.as_view()), name='user_center_info'),
    # url(r'^user_center_order$', login_required(UserCenterOrder.as_view()), name='user_center_order'),
    # url(r'^user_center_site$', login_required(UserCenterSite.as_view()), name='user_center_site'),
    # url(r'^base$', to_base),
    # url(r'^base_no_cart$', base_no_cart),
    # url(r'^base_user_center$', base_user_center),
    # url(r'^base_detail_list$', base_detail_list),
]
