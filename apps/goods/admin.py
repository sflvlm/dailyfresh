from django.contrib import admin
from goods.models import *
from django.core.cache import cache
from apps.goods.tasks import generate_static_index_html
# Register your models here.
class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        '''新增或更新表中的数据时调用'''
        super().save_model(request, obj, form, change)

        # 发出任务，让celery worker重新生成首页静态页


        generate_static_index_html.delay()

        # 清除首页的缓存数据
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        '''删除表中的数据时调用'''
        super().delete_model(request, obj)
        # 发出任务，让celery worker重新生成首页静态页

        generate_static_index_html.delay()

        # 清除首页的缓存数据
        cache.delete('index_page_data')


class GoodsTypeAdmin(BaseModelAdmin):
    pass


class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass


class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass


class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass

class GoodsSKUAdmin(BaseModelAdmin):
    pass

admin.site.register(GoodsType,GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner,IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner,IndexTypeGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner,IndexPromotionBannerAdmin)
admin.site.register(GoodsSKU,GoodsSKUAdmin)