from django.conf import settings
import os
from celery import Celery

# 为celery设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dailyfresh.settings')

# 创建应用
app = Celery('user')


# 酸配置应用
app.conf.update(

    # 本地Redis服务器
    BROKER_URL='redis://192.168.35.134:6379/2',
)

app.autodiscover_tasks(settings.INSTALLED_APPS)

