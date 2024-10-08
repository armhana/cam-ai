"""
Copyright (C) 2024 by the CAM-AI team, info@cam-ai.de
More information and complete source: https://github.com/ludgerh/cam-ai
This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""

from django.db import models
from django.utils import timezone
from datetime import datetime
from tf_workers.models import school
from streams.models import stream

class event(models.Model):
  deleted = models.BooleanField(default=False)
  p_string = models.CharField(max_length=255, default='[]')
  start = models.DateTimeField(default=timezone.make_aware(datetime(1900, 1, 1)))
  end = models.DateTimeField(default=timezone.make_aware(datetime(1900, 1, 1)))
  xmin = models.IntegerField(default=-1)
  xmax = models.IntegerField(default=-1)
  ymin = models.IntegerField(default=-1)
  ymax = models.IntegerField(default=-1)
  numframes = models.IntegerField(default=0)
  school = models.ForeignKey(school, on_delete=models.CASCADE, default=1)
  camera = models.ForeignKey(stream, on_delete=models.CASCADE, default=1)
  done = models.BooleanField(default=False)
  videoclip = models.CharField(max_length=256, default='')
  video_encrypted = models.BooleanField(default=True)
  double = models.BooleanField(default=False)
  hasarchive = models.BooleanField(default=False)

  def __str__(self):
    return('event model, id = '+str(self.id))
		
class event_frame(models.Model):
  deleted = models.BooleanField(default=False)
  time = models.DateTimeField(default=timezone.make_aware(datetime(1900, 1, 1)))
  status = models.SmallIntegerField(default=0)
  name = models.CharField(max_length=100)
  encrypted = models.BooleanField(default=True)
  x1 = models.IntegerField(default=0)
  x2 = models.IntegerField(default=0)
  y1 = models.IntegerField(default=0)
  y2 = models.IntegerField(default=0)
  event = models.ForeignKey(event, on_delete=models.CASCADE, default=1)
  trainframe = models.BigIntegerField(default=0)
  hasarchive = models.BooleanField(default=False)
  
  class Meta:
    indexes = [
      models.Index(fields=["name"], name="name_idx"),
    ]

  def __str__(self):
    return('event_frames model (TBD ...)')

class evt_condition(models.Model):
  eventer = models.ForeignKey(stream, on_delete=models.CASCADE)
  reaction = models.IntegerField("reaction", choices=(
    (1, 'show frame'),
    (2, 'send school'),
    (3, 'record video'),
    (4, 'send email'),
    (5, 'alarm'),
  ), default=0)
  and_or = models.IntegerField("and_or", choices=((1, 'and'), (2, 'or')), default=2)
  c_type = models.IntegerField("c_type", choices=(
    (1, 'any movement detection'),
    (2, 'x values above or equal y'),
    (3, 'x values below or equal y'),
    (4, 'tag x is above or equal y'),
    (5, 'tag x is below or equal y'),
    (6, 'tag x is in top y'),
  ), default=1)
  x = models.IntegerField("x", default=1)
  y = models.FloatField("y", default=0.5)
  bracket = models.IntegerField("bracket", default=0)

  def __str__(self):
    return('evt_conditions model (TBD ...)')
  
class alarm_device_type(models.Model):
  name = models.CharField(max_length=50, default="New device type")
  mendef = models.CharField(max_length=255, default="[]")
  
  def __str__(self):
    return('Model: alarm_device_type:' + self.name)
  
class alarm_device(models.Model):
  name = models.CharField(max_length=50, default="New device")
  device_type = models.ForeignKey(alarm_device_type, on_delete=models.CASCADE)
  
  def __str__(self):
    return('Model: alarm_device:' + self.name)
    
class alarm(models.Model):
  name = models.CharField(max_length=50, default="New alarm")
  active = models.BooleanField(default=True)
  mystream = models.ForeignKey(stream, on_delete=models.CASCADE)
  mydevice = models.ForeignKey(alarm_device, on_delete=models.CASCADE, null=True)
  mendef = models.CharField(max_length=255, default="[]")
  
  def __str__(self):
    return('Model: alarm:' + self.name)
