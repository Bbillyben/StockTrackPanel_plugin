from plugin import InvenTreePlugin
from plugin.mixins import PanelMixin, SettingsMixin
from plugin.base.integration.mixins import UrlsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from stock.views import StockLocationDetail, StockIndex
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.urls import path, re_path, reverse
from django.conf.urls import include
from django.db.models import Max, F 
from django.utils.translation import gettext as _


from stock.models import StockItem, StockItemTracking, StockLocation
from InvenTree.serializers import InvenTreeDecimalField, InvenTreeModelSerializer,UserSerializer
from stock.serializers import LocationBriefSerializer
from rest_framework import serializers, viewsets, permissions, routers
from rest_framework.decorators import action
from django_filters import rest_framework as rest_filters

from InvenTree.api import APIDownloadMixin
from InvenTree.helpers import DownloadFile, str2bool
from InvenTree.admin import InvenTreeResource
from InvenTree.status_codes import StockHistoryCode
from import_export.fields import Field
import import_export.widgets as widgets
from django.contrib.auth.models import User

import datetime

from plugins.StockTrackPanel_plugin import views as SMPviews
    
    
### ------------------------------------------- Plugin Class ------------------------------------------------ ###

class StockTrackPanel(PanelMixin, SettingsMixin, UrlsMixin,  InvenTreePlugin):

    NAME = "StockTrackPanel"
    SLUG = "stocktrack"
    TITLE = "StockTrack panel"
    AUTHOR = "Bbillyben"
    DESCRIPTION = "A plugin to visualize last stock tracking item by location"
    VERSION = "0.1"

    SETTINGS = {
        'MONTH_FOLLOW': {
            'name': 'Number of Month to follow',
            'description': 'time scope in month to visualize from last entry',
            'default': 1,
            'validator': MinValueValidator(1),
        },
    }

    def get_panel_context(self, view, request, context):
        """Returns enriched context."""
        ctx = super().get_panel_context(view, request, context)

        return ctx

    def get_custom_panels(self, view, request):
        if isinstance(view, StockIndex) or isinstance(view, StockLocationDetail):
            
            if isinstance(view, StockLocationDetail):
                loc=view.get_object()
                urlTrac=reverse('plugin:stocktrack:track-location', kwargs={'loc': loc.pk})
                # print("  --- > objc url :"+str(urlTrac))
            else:
                urlTrac=reverse('plugin:stocktrack:track-list')
                
            context={'dataUrl':urlTrac}
            
            tmpRend = render_to_string(template_name='stocktrackpanel/SMP_panel.html',context=context)

            panels = [
                {
                    # Simple panel without any actual content
                    'title': 'Stock Tracking',
                    'content': tmpRend,
                    'icon' : 'fa-thumbtack', 
                    'javascript': 'SMP_initPanel',
                    'javascript_template': 'stocktrackpanel/SMP_panel.js'
                }
            ]
        return panels

    # def getSMPSerializeTrack(self, request, location=None):
    #     strLoc = "The location called is :"+str(location)
    #     trackObj = StockItemTracking.objects.prefetch_related('item').all()
        
    #     if location is not None:
    #         loc= StockLocation.objects.get(pk=location)
    #         # print("stock loc : "+str(location)+ " / " +str(loc))
    #         if loc:
    #             locs = loc.getUniqueChildren(True).values("pk")
    #             # print(" -> all locs :" + str(locs))
    #             trackObj = trackObj.filter(item__location__in = locs)
        
    #     return  JsonResponse(SMP_StockTrackSerializer(trackObj, many=True).data, safe=False)


    def setup_urls(self):
        """Urls that are exposed by this plugin."""
        router = routers.DefaultRouter()

        router.register(r'track', SMPviews.SMPTrackViewSet, basename='track')
        return router.urls
        


