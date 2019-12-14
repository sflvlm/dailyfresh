from django.conf.urls import url
from apps.user import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    url(r'^register$',views.Register.as_view(),name='register'),
    url(r'^active/(?P<token>.*)$',views.Active.as_view(),name='active'),
    url(r'^login$',views.Login.as_view(),name='login'),
    url(r'^logout$', views.LogoutView.as_view(), name='logout'), # 注销登录

    # url(r'^$',login_required(views.UserInfoView.as_view()),name='user'),
    # url(r'^order$',login_required(views.UserOrderView.as_view()),name='order'),
    # url(r'^address$',login_required(views.AddressView.as_view()),name='address')
    url(r'^$',views.UserInfoView.as_view(),name='user'),
    url(r'^order/(?P<page>\d+)$',views.UserOrderView.as_view(),name='order'),
    url(r'^address$',views.AddressView.as_view(),name='address')
]