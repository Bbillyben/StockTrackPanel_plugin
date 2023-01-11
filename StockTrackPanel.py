from plugin import InvenTreePlugin
from plugin.mixins import PanelMixin, SettingsMixin
from plugin.base.integration.mixins import UrlsMixin
from django.core.validators import  MinValueValidator
from stock.views import StockLocationDetail, StockIndex
from django.template.loader import render_to_string
from django.urls import path, reverse,re_path, include
from django.utils.translation import gettext as _


from plugins.StockTrackPanel_plugin import views as SMPviews
import logging
logger = logging.getLogger('inventree')
### ------------------------------------------- Plugin Class ------------------------------------------------ ###


class StockTrackPanel(PanelMixin, SettingsMixin, UrlsMixin, InvenTreePlugin):

    NAME = "StockTrackPanel"
    SLUG = "stocktrack"
    TITLE = "StockTrack panel"
    AUTHOR = "Bbillyben"
    DESCRIPTION = "A plugin to visualize last stock tracking item by location"
    VERSION = "0.1"

    SETTINGS = {
        'MONTH_FOLLOW': {
            'name': 'Number of Month to follow',
            'description': 'number ofmonth from last entry to display in Stock Track Panel',
            'default': 1,
            'validator': MinValueValidator(1),
        },
    }
    
    def setup_urls(self):
        # """Urls that are exposed by this plugin."""
        logger.debug('[StockTrackPanel] - setup_urls ')
        SMP_URL=[
            path('track/', SMPviews.SMPTrackViewSet.get_track, name='track-list'),
            path('track/location/<loc>/', SMPviews.SMPTrackViewSet.get_track, name='track-location'),      
        ]
        return SMP_URL
    
    
    @property
    def urlpatterns(self):
        """Urlpatterns for this plugin.""" 
        logger.debug('[StockTrackPanel] - urlpatterns ')
        if self.has_urls:
            return re_path(f'^{self.slug}/', include((self.urls, self.slug)), name=self.slug)
        return None
    
    def get_panel_context(self, view, request, context):
        """Returns enriched context."""
        ctx = super().get_panel_context(view, request, context)

        return ctx

    def get_custom_panels(self, view, request):
        if isinstance(view, StockIndex) or isinstance(view, StockLocationDetail):
            
            if isinstance(view, StockLocationDetail):
                loc=view.get_object()
                urlTrac=reverse('plugin:stocktrack:track-location', kwargs={'loc': loc.pk})
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
        return []



