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
from django.views import View


from stock.models import StockItem, StockItemTracking, StockLocation
from InvenTree.serializers import InvenTreeDecimalField, InvenTreeModelSerializer,UserSerializer
from stock.serializers import LocationBriefSerializer
from rest_framework import serializers, generics, viewsets, permissions, routers
from rest_framework.decorators import action, api_view
from django_filters import rest_framework as rest_filters

from InvenTree.api import APIDownloadMixin
from InvenTree.helpers import DownloadFile, str2bool
from InvenTree.admin import InvenTreeResource
from InvenTree.status_codes import StockHistoryCode
from import_export.fields import Field
import import_export.widgets as widgets
from django.contrib.auth.models import User

import datetime
from dateutil.relativedelta import relativedelta

### ------------------------------------------- Serializers Class ------------------------------------------------ ###
class SMP_StockItemSerializer(InvenTreeModelSerializer):
    """Brief serializers for a StockItem."""

    part_name = serializers.CharField(source='part.full_name', read_only=True)

    quantity = InvenTreeDecimalField()
    
    location_detail = LocationBriefSerializer(source='location', many=False, read_only=True)

    class Meta:
        """Metaclass options."""

        model = StockItem
        fields = [
            'part',
            'part_name',
            'pk',
            'location',
            'location_detail',
            'quantity',
            'batch',
            'serial',
            'supplier_part',
        ]
    
class SMP_StockTrackSerializer(InvenTreeModelSerializer):
    """Serializer for StockItemTracking model with details."""

    label = serializers.CharField(read_only=True)

    item_detail = SMP_StockItemSerializer(source='item', many=False, read_only=True)

    user_detail = UserSerializer(source='user', many=False, read_only=True)

    deltas = serializers.JSONField(read_only=True)

    class Meta:
        """Metaclass options."""

        model = StockItemTracking
        fields = [
            'pk',
            'item',
            'item_detail',
            'date',
            'deltas',
            'label',
            'notes',
            'tracking_type',
            'user',
            'user_detail',
        ]

        read_only_fields = [
            'date',
            'user',
            'label',
            'tracking_type',
        ]   

### ------------------------------------------- Filter Class ------------------------------------------------ ###

class SMPTrackFilter(rest_filters.FilterSet):
    
    class Meta:
        model = StockItemTracking
        fields = ['tracking_type','item', 'date', 'notes',]
        

### ------------------------------------------- Resource Class ------------------------------------------------ ###

class SMPTrackResource(InvenTreeResource):
    """Class for managing import / export of PurchaseOrder data."""

    itemName = Field(
        column_name=_('Item'),
        attribute='item', 
        widget=widgets.ForeignKeyWidget(StockItem, 'part__name'), readonly=True
        )
    batch = Field(
        column_name=_('Batch'),
        attribute='item', 
        widget=widgets.ForeignKeyWidget(StockItem, 'batch'), readonly=True
        )
    quantity = Field(
        column_name=_('quantity'),
        attribute='item', 
        widget=widgets.ForeignKeyWidget(StockItem, 'quantity'), readonly=True
        )
    location = Field(
        column_name=_('location'),
        attribute='item', 
        widget=widgets.ForeignKeyWidget(StockItem, 'location__pathstring'), readonly=True
        )
    label = Field(
        column_name=_('Operation'),
        attribute='label', 
        widget=widgets.CharWidget(), readonly=True
        )
    user = Field(
        column_name=_('User'),
        attribute='user', 
        widget=widgets.ForeignKeyWidget(User, 'username'), readonly=True
        )
    def export(self, queryset=None):
        fetched_queryset = list(queryset)
        return super().export(fetched_queryset)

    class Meta:
        """Metaclass"""
        model = StockItemTracking
        skip_unchanged = False
        clean_model_instances = False
        exclude = [
            'id',
            'tracking_type', 
            'item', 
            'deltas',
            'metadata',
        ]
        export_order=['itemName', 'batch', 'date', 'label', 'quantity', 'location' , 'notes','user', ]

### ------------------------------------------- View Class ------------------------------------------------ ###
class SMPTrackViewSet(View):
    serializer_class = SMP_StockTrackSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (rest_filters.DjangoFilterBackend,)
    filterset_class = SMPTrackFilter
    
    http_method_names=['get'] 
    request = None
     
    def filter_queryset(self, queryset):
        params = self.request.GET
        # queryset = super().filter_queryset(queryset)
        
        name = params.get('username', None)
        print("[SMPTrackViewSet.filter_queryset] username:"+str(name))
        if name is not None:
            queryset = queryset.filter(user__username__icontains=name)
        
        
        tracktype = params.get('tracktype', None)
        print("[SMPTrackViewSet.filter_queryset] tracktype:"+str(tracktype))
        if tracktype is not None:
            queryset = queryset.filter(tracking_type=tracktype)
        
        lastdate = params.get('lastdate', None)
        print("[SMPTrackViewSet.filter_queryset] lastdate:"+str(lastdate))
        if str2bool(lastdate) :
            last_date = queryset.latest('date').date
            if not last_date:
                last_date= datetime.datetime.now()
            max_date=datetime.datetime(last_date.year, last_date.month, last_date.day)
            print('--> max date : '+str(max_date))
            queryset = queryset.filter(date__gte=max_date)
        
        print('[SMPTrackViewSet] filter_queryset END')
        return queryset
    
    def get_queryset(self):
        
        from plugins.StockTrackPanel_plugin.StockTrackPanel import StockTrackPanel
        print('[SMPTrackViewSet] get_queryset')
        setSMP = StockTrackPanel.get_setting(StockTrackPanel(), key='MONTH_FOLLOW')
        if setSMP:
            setSMP=int(setSMP)
        else:
            setSMP = 2
        last_date = StockItemTracking.objects.latest('date').date
        print(' -> last Date :'+str(last_date))
        
        if not last_date:
                last_date= datetime.datetime.now()   
        dateLim = last_date+relativedelta(months=-setSMP)
        print(' -> dateLim :'+str(dateLim))
        
        return StockItemTracking.objects.prefetch_related('item').filter(date__gte=dateLim)
        
        # return StockItemTracking.objects.prefetch_related('item')
    
    def download_queryset(self, queryset, export_format):
        """Download the filtered queryset as a data file"""
        print('[SMPTrackViewSet] download_queryset call')
        dataset = SMPTrackResource().export(queryset=queryset)

        filedata = dataset.export(export_format)

        filename = f"StockTrack.{export_format}"

        return DownloadFile(filedata, filename)
    
    def get_track(request,*args, **kwargs):
        return SMPTrackViewSet().get(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        print('request : '+str(request))
        print('args : '+str(args))
        print('kwargs : '+str(kwargs))
        self.request = request
        loc = kwargs.get('loc', None)
        if loc :
            return self.location(loc)
        return self.list()
        # return HttpResponse('Hello, World!')
        
    def list(self):
        params = self.request.GET
        trackObj = self.filter_queryset(self.get_queryset())
        export = params.get('export', None)
        print('[SMPTrackViewSet] export :'+str(export))
        if export is not None:
            return self.download_queryset(trackObj, export)
        
        return  JsonResponse(SMP_StockTrackSerializer(trackObj, many=True).data, safe=False)
    
    
    def location(self, loc=None):
        # print('[SMPTrackFilter] / location :'+str(loc))
        params = self.request.GET
        
        trackObj = self.filter_queryset(self.get_queryset())
        
        if loc is not None:
            locItem= StockLocation.objects.get(pk=loc)
            # print("stock loc : "+str(loc)+ " / " +str(locItem))
            if loc:
                locs = locItem.getUniqueChildren(True).values("pk")
                # print(" -> all locs :" + str(locs))
                trackObj = trackObj.filter(item__location__in = locs)
                
        export = params.get('export', None)
        print('[SMPTrackViewSet] export :'+str(export))
        if export is not None:
            return self.download_queryset(trackObj, export)
        
        return  JsonResponse(SMP_StockTrackSerializer(trackObj, many=True).data, safe=False)
