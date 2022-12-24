import logging
from django.template.loader import render_to_string
from django.http import  JsonResponse
from django.utils.translation import gettext as _
from django.views import View


from stock.models import StockItem, StockItemTracking, StockLocation
from InvenTree.serializers import InvenTreeDecimalField, InvenTreeModelSerializer,UserSerializer
from stock.serializers import LocationBriefSerializer
from rest_framework import serializers, permissions
from django_filters import rest_framework as rest_filters

from InvenTree.helpers import DownloadFile, str2bool
from InvenTree.admin import InvenTreeResource
from import_export.fields import Field
import import_export.widgets as widgets
from django.contrib.auth.models import User

import datetime
import pytz
from dateutil.relativedelta import relativedelta

logger = logging.getLogger('inventree')
### ------------------------------------------- Serializers Class ------------------------------------------------ ###
class SMP_StockItemSerializer(InvenTreeModelSerializer):
    """Brief serializers for a StockItem."""

    part_name = serializers.CharField(source='part.full_name', read_only=True)
    quantity = InvenTreeDecimalField()
    location_detail = LocationBriefSerializer(source='location', many=False, read_only=True)
    unit = serializers.SerializerMethodField()
    
    def get_unit(self,obj):
        return obj.part.units
    
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
            'unit',
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

### ------------------------------------------- Resource Class ------------------------------------------------ ###
class DeltaWidget(widgets.CharWidget):
    def render(self, value, obj=None):
        rem=value.get('removed', None)
        if rem is not None:
            return -rem
        added=value.get('added', None)
        if added is not None:
            return added
        
        quantity=value.get('quantity', None)
        if quantity is not None:
            return quantity
        
        return str(value)
    
    
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
    serial = Field(
        column_name=_('Serial'),
        attribute='item', 
        widget=widgets.ForeignKeyWidget(StockItem, 'serial'), readonly=True
        )
    quantity = Field(
        column_name=_('quantity in stock'),
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
    deltas = Field(
        column_name=_('Delta'),
        attribute='deltas', 
        widget=DeltaWidget(), readonly=True
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
            'metadata',
        ]
        export_order=['itemName', 'batch', 'date', 'label', 'deltas',  'location' ,'quantity', 'notes','user', ]

### ------------------------------------------- View Class ------------------------------------------------ ###

class SMPTrackViewSet(View):
    permission_classes = [permissions.IsAuthenticated]

    http_method_names=['get'] 
    request = None
     
    def filter_queryset(self, queryset):
        params = self.request.GET
        
        name = params.get('username', None)
        if name is not None:
            queryset = queryset.filter(user__username__icontains=name)
        
        
        tracktype = params.get('tracktype', None)
        if tracktype is not None:
            queryset = queryset.filter(tracking_type=tracktype)
        
        batch = params.get('batch', None)
        if batch is not None:
            queryset = queryset.filter(item__batch__icontains=batch)
        
        serial = params.get('serial', None)
        if serial is not None:
            queryset = queryset.filter(item__serial__icontains=serial)
        
        
        dategte = params.get('date_greater', None)
        if dategte is not None:
            date_gte = datetime.datetime.fromtimestamp(int(dategte) / 1e3)
            queryset = queryset.filter(date__gte=date_gte)
        
        datelte = params.get('date_lesser', None)
        if datelte is not None:
            date_lte = datetime.datetime.fromtimestamp(int(datelte) / 1e3)
            queryset = queryset.filter(date__lte=date_lte)
        
        lastdate = params.get('lastdate', None)
        if str2bool(lastdate) :
            last_date = queryset.latest('date').date
            if not last_date:
                last_date= datetime.datetime.now()
            max_date=datetime.datetime(last_date.year, last_date.month, last_date.day)
            queryset = queryset.filter(date__gte=max_date)
        
        return queryset
    
    def get_queryset(self):
        
        from plugins.StockTrackPanel_plugin.StockTrackPanel import StockTrackPanel
        setSMP = StockTrackPanel.get_setting(StockTrackPanel(), key='MONTH_FOLLOW')
        if setSMP:
            setSMP=int(setSMP)
        else:
            setSMP = 2
        last_date = StockItemTracking.objects.latest('date').date
        
        if not last_date:
                last_date= datetime.datetime.now()   
        dateLim = last_date+relativedelta(months=-setSMP)
        
        return StockItemTracking.objects.prefetch_related('item').filter(date__gte=dateLim)
    
    def download_queryset(self, queryset, export_format):
        """Download the filtered queryset as a data file"""
        dataset = SMPTrackResource().export(queryset=queryset)

        filedata = dataset.export(export_format)

        filename = f"StockTrack.{export_format}"

        return DownloadFile(filedata, filename)
    
    def get_track(request,*args, **kwargs):
        return SMPTrackViewSet().get(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
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
        if export is not None:
            return self.download_queryset(trackObj, export)
        
        return  JsonResponse(SMP_StockTrackSerializer(trackObj, many=True).data, safe=False)
