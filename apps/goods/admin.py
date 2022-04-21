from django.contrib import admin
from django.core.cache import cache
from goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,GoodsSKU,GoodsImage,IndexTypeGoodsBanner
# Register your models here.

class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from celery_task.celery import generate_index
        generate_index.delay()
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        from celery_task.celery import generate_index
        generate_index.delay()
        cache.delete('index_page_data')

class GoodsTypeAdmin(BaseModelAdmin):
    pass


class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass


class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass


class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)

admin.site.register(GoodsSKU)
admin.site.register(GoodsImage)


