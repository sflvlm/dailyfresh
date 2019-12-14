from django.shortcuts import render,redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from dailyfresh import settings
from django.http import HttpResponse
from user.tasks import send_register_active_email

from user.models import User,Address
from goods.models import GoodsSKU
from django.contrib.auth import authenticate,login,logout
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from utils.mixin import LoginRequiredMixin
from django_redis import get_redis_connection
import re

from order.models import OrderGoods,OrderInfo
from django.core.paginator import Paginator

# Create your views here.
def register(request):
    if request.method == 'GET':
        return render(request,'register.html')
    if request.method == 'POST':
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cpassword = request.POST.get('cpwd')
        email = request.POST.get('email')

        if not all([username, password, cpassword, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user == None:
            user = User.objects.create_user(username, email, password)
            user.is_active = 0
            user.save()

            return redirect(reverse('goods:index'))
        else:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

class Register(View):

    def get(self,request):
        return render(request, 'register.html')

    def post(self,request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cpassword = request.POST.get('cpwd')
        email = request.POST.get('email')

        if not all([username, password, cpassword, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user == None:
            user = User.objects.create_user(username, email, password)
            user.is_active = 0
            user.save()
            serializer = Serializer(settings.SECRET_KEY,3600)
            info = {'confirm':user.id}
            token = serializer.dumps(info)
            token = token.decode()

            send_register_active_email.delay(email, username, token)

            return redirect(reverse('goods:index'))
        else:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

class Active(View):
    def get(self,request,token):
        serializer = Serializer(settings.SECRET_KEY,3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')

class Login(View):
    def get(self,request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        '''登录校验'''
        # 接收数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        # 校验数据
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg':'数据不完整'})

        # 业务处理:登录校验
        user = authenticate(username=username, password=password)
        if user is not None:
            # 用户名密码正确
            if user.is_active:
                # 用户已激活
                # 记录用户的登录状态
                login(request, user)

                # 获取登录后所要跳转到的地址
                # 默认跳转到首页
                next_url = request.GET.get('next', reverse('goods:index'))

                # 跳转到next_url
                response = redirect(next_url) # HttpResponseRedirect

                # 判断是否需要记住用户名
                remember = request.POST.get('rem')

                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    response.delete_cookie('username')

                # 返回response
                return response
            else:
                # 用户未激活
                return render(request, 'login.html', {'errmsg':'账户未激活'})
        else:
            # 用户名或密码错误
            return render(request, 'login.html', {'errmsg':'用户名或密码错误'})

# /user/logout
class LogoutView(View):
    def get(self,request):
        '''退出登录'''
        # 清除用户的session信息
        logout(request)

        # 跳转到首页
        return redirect(reverse('goods:index'))

# /user
class UserInfoView(LoginRequiredMixin,View):
    def get(self,request):
        user = request.user
        address = Address.objects.get_default_address(user)

        con = get_redis_connection("default")
        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的5个商品的id
        sku_ids = con.lrange(history_key, 0, 4)  # [2,3,1]
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {'page': 'user',
                   'address': address,
                   'goods_li': goods_li}
        return render(request,'user_center_info.html',context)

# /user/order
class UserOrderView(LoginRequiredMixin,View):
    def get(self, request, page):
        '''显示'''
        # 获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        # 遍历获取订单商品的信息
        for order in orders:
            # 根据order_id查询订单商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 遍历order_skus计算商品的小计
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price
                # 动态给order_sku增加属性amount,保存订单商品的小计
                order_sku.amount = amount

            # 动态给order增加属性，保存订单状态标题
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 动态给order增加属性，保存订单商品的信息
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Page实例对象
        order_page = paginator.page(page)

        # todo: 进行页码的控制，页面上最多显示5个页码
        # 1.总页数小于5页，页面上显示所有页码
        # 2.如果当前页是前3页，显示1-5页
        # 3.如果当前页是后3页，显示后5页
        # 4.其他情况，显示当前页的前2页，当前页，当前页的后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 组织上下文
        context = {'order_page': order_page,
                   'pages': pages,
                   'page': 'order'}

        # 使用模板
        return render(request, 'user_center_order.html', context)


# /user/address
class AddressView(LoginRequiredMixin,View):
    def get(self,request):
        user = request.user
        address = Address.objects.get_default_address(user)
        return render(request,'user_center_site.html',{'page':'address','address':address})
    def post(self,request):
        '''地址的添加'''
        # 接收数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})

        # 校验手机号
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机格式不正确'})

        # 业务处理：地址添加
        # 如果用户已存在默认收货地址，添加的地址不作为默认收货地址，否则作为默认收货地址
        # 获取登录用户对应User对象
        user = request.user

        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 不存在默认收货地址
        #     address = None

        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        # 添加地址
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)

        # 返回应答,刷新地址页面
        return redirect(reverse('user:address'))  # get请求方式


