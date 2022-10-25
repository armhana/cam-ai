# Copyright (C) 2022 Ludger Hellerhoff, ludger@cam-ai.de
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
# See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

from django.conf import settings
from django.views.generic.base import TemplateView
from django.shortcuts import render
from streams.models import stream
from access.c_access import access
from tf_workers.models import school
from tools.l_tools import djconf

class health(TemplateView):
  template_name = 'tools/health.html'


  def get_context_data(self, **kwargs):
    camlist = access.filter_items(stream.objects.filter(active=True).filter(cam_mode_flag__gt=0), 'C', self.request.user, 'R')
    detectorlist = access.filter_items(stream.objects.filter(active=True).filter(det_mode_flag__gt=0), 'D', self.request.user, 'R')
    eventerlist = access.filter_items(stream.objects.filter(active=True).filter(eve_mode_flag__gt=0), 'E', self.request.user, 'R')
    schoollist = access.filter_items(school.objects.filter(active=True), 'S', self.request.user, 'R')
    context = super().get_context_data(**kwargs)
    context.update({
      'version' : djconf.getconfig('version', 'X.Y.Z'),
      'emulatestatic' : djconf.getconfigbool('emulatestatic', False),
      'debug' : settings.DEBUG,
      'camlist' : camlist,
      'detectorlist' : detectorlist,
      'eventerlist' : eventerlist,
      'schoollist' : schoollist,
      'recordingspath' : djconf.getconfig('recordingspath', 'data/recordings/'),
      'schoolframespath' : djconf.getconfig('schoolframespath', 'data/schoolframes/')
    })
    return context
