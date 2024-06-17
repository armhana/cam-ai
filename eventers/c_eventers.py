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

c_eventer.py V2.1.0 03.03.2024
"""

import cv2 as cv
import json
import numpy as np
from os import remove, path, nice, environ
from shutil import copyfile
from traceback import format_exc
from logging import getLogger
from setproctitle import setproctitle
from collections import deque
from time import time, sleep
from threading import Thread, Lock as t_lock
from queue import SimpleQueue
from multiprocessing import Process, Lock as p_lock
from subprocess import run
from django.forms.models import model_to_dict
from django.db import connection
from django.db.utils import OperationalError
from tools.l_tools import djconf
from tools.c_logger import log_ini
from tools.c_tools import hasoverlap, rect_btoa
from viewers.c_viewers import c_viewer
from l_buffer.l_buffer import l_buffer, c_buffer
from tf_workers.c_tfworkers import tf_workers
from tf_workers.models import school
from streams.c_devices import c_device
from streams.models import stream
from schools.c_schools import get_taglist
from .models import evt_condition
from .models import event
from .c_event import c_event, resolve_rules
from .c_alarm import alarm, alarm_init

#from threading import enumerate

class c_eventer(c_device):

  def __init__(self, *args, **kwargs):
    self.type = 'E'
    super().__init__(*args, **kwargs)
    self.mode_flag = self.dbline.eve_mode_flag
    if self.dbline.eve_view:
      self.viewer = c_viewer(self, self.logger)
    else:
      self.viewer = None
    self.tf_worker = tf_workers[school.objects.get(id=self.dbline.eve_school.id).tf_worker.id]
    self.tf_worker.eventer = self
    self.dataqueue = c_buffer(block=True)
    self.detectorqueue = l_buffer(queue=True)
    self.buffer_ts = time()
    self.display_ts = 0
    self.nr_of_cond_ed = 0
    self.read_conditions()
    self.tag_list_active = self.dbline.eve_school.id
    self.tag_list = get_taglist(self.tag_list_active)
    datapath = djconf.getconfig('datapath', 'data/')
    self.recordingspath = djconf.getconfig('recordingspath', datapath + 'recordings/')

  def runner(self):
    super().runner()
    self.logname = 'eventer #'+str(self.dbline.id)
    self.logger = getLogger(self.logname)
    log_ini(self.logger, self.logname)
    alarm_init(self.logger, self.dbline.id)
    setproctitle('CAM-AI-Eventer #'+str(self.dbline.id))
    environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    if self.dbline.eve_gpu_nr_cv== -1:
      environ["CUDA_VISIBLE_DEVICES"] = ''
    else:  
      environ["CUDA_VISIBLE_DEVICES"] = str(self.dbline.eve_gpu_nr_cv)
    self.logger.info('**** Eventer #' + str(self.dbline.id)+' running GPU #' 
      + str(self.dbline.eve_gpu_nr_cv))
    self.eventdict = {}
    self.eventdict_lock = t_lock()
    self.display_lock = t_lock()
    self.vid_deque = deque()
    self.vid_str_dict = {}
    self.set_cam_counts()

    self.tf_w_index = self.tf_worker.register()
    self.tf_worker.run_out(self.tf_w_index)

    self.finished = False
    self.do_run = True
    self.scaling = None
    
    self.frame_queue = SimpleQueue()
    self.active_pred_count = 0
    self.active_pred_lock = t_lock()
    self.motion_frame = [0,0,0.0]
    self.run_one_ts = time()
    self.pred_deque = deque()

    Thread(target=self.inserter, name='InserterThread').start()
    
    self.webm_lock = p_lock()
    self.redis.set('webm_queue:' + str(self.id) + ':start', 0)
    self.redis.set('webm_queue:' + str(self.id) + ':end', 0)
    self.webm_proc = Process(target=self.make_webm).start()
    try:
      while self.do_run:
        if self.redis.view_from_dev('E', self.dbline.id): 
          frameline = self.dataqueue.get()
        else:
          frameline = [None, 0, time()]  
        if (self.do_run and (frameline is not None) 
            and self.sl.greenlight(self.period, frameline[2])):
          self.run_one(frameline) 
        else:
          sleep(djconf.getconfigfloat('short_brake', 0.1))
      self.dataqueue.stop()
      with self.eventdict_lock:
        for item in self.eventdict.values():
          while True:
            try:
              item.dbline.delete()
              break
            except OperationalError:
              connection.close()
      self.finished = True
      self.logger.info('Finished Process '+self.logname+'...')
      self.logger.handlers.clear()
      self.tf_worker.stop_out(self.tf_w_index)
      self.tf_worker.unregister(self.tf_w_index)
    except:
      self.logger.error(format_exc())
      self.logger.handlers.clear()
#    for thread in enumerate(): 
#      print(thread)

  def in_queue_handler(self, received):
    try:
      if super().in_queue_handler(received):
        return(True)
      else:
        if (received[0] == 'new_video'):
          self.vid_deque.append(received[1:])
          while True:
            if self.vid_deque and (time() - self.vid_deque[0][2]) > 300:
              listitem = self.vid_deque.popleft()
              try:
                remove(self.recordingspath + listitem[1])
              except FileNotFoundError:
                self.logger.warning('c_eventers.py:new_video - Delete did not find: '
                  + self.recordingspath + listitem[1])
            else:
              break
        elif (received[0] == 'purge_videos'):
          for item in self.vid_deque.copy():
            try:
              remove(self.recordingspath + item[1])
            except FileNotFoundError:
              self.logger.warning('c_eventers.py:purge_videos - Delete did not find: '
                + self.recordingspath + item[1])
          self.vid_deque.clear()
        elif (received[0] == 'set_fpslimit'):
          self.dbline.eve_fpslimit = received[1]
          if received[1] == 0:
            self.period = 0.0
          else:
            self.period = 1.0 / received[1]
        elif (received[0] == 'set_margin'):
          self.dbline.eve_margin = received[1]
        elif (received[0] == 'set_event_time_gap'):
          self.dbline.eve_event_time_gap = received[1]
        elif (received[0] == 'set_school'):
          self.dbline.eve_school = school.objects.get(id=received[1])
        elif (received[0] == 'set_alarm_email'):
          self.dbline.eve_alarm_email = received[1]
        elif (received[0] == 'cond_open'):
          self.nr_of_cond_ed += 1
          self.last_cond_ed = received[1]
        elif (received[0] == 'cond_close'):
          self.nr_of_cond_ed = max(0, self.nr_of_cond_ed - 1)
        elif (received[0] == 'new_condition'):
          self.cond_dict[received[1]].append(received[2])
          self.set_cam_counts()
        elif (received[0] == 'del_condition'):
          self.cond_dict[received[1]] = [item 
            for item in self.cond_dict[received[1]] 
            if item['id'] != received[2]]
          self.set_cam_counts()
        elif (received[0] == 'save_condition'):
          for item in self.cond_dict[received[1]]:
            if item['id'] == received[2]:
	            item['c_type'] = received[3]
	            item['x'] = received[4]
	            item['y'] = received[5]
	            break
          self.set_cam_counts()
        elif (received[0] == 'save_conditions'):
          self.cond_dict[received[1]] = json.loads(received[2])
          self.set_cam_counts()
        elif (received[0] == 'setdscrwidth'):
          self.scrwidth = received[1]
          self.scaling = None
        elif (received[0] == 'reset'):
          while True:
            try:
              self.dbline.refresh_from_db()
              break
            except OperationalError:
              connection.close()
        else:
          return(False)
        return(True)
    except:
      self.logger.error(format_exc())
      self.logger.handlers.clear()

  def run_one(self, frame):
    if self.redis.check_if_counts_zero('E', self.dbline.id):
      sleep(djconf.getconfigfloat('long_brake', 1.0))
    else:
      if frame[0]:
        if self.scaling is None:
          if frame[1].shape[1] > self.scrwidth:
            self.scaling = self.scrwidth / frame[1].shape[1]
          else:
            self.scaling = 1.0  
          self.linewidth = round(4.0 / self.scaling)
          self.textheight = round(0.51 / self.scaling)
          self.textthickness = round(2.0 / self.scaling)
      else:
        sleep(djconf.getconfigfloat('short_brake', 0.01))
      if (time() - self.run_one_ts) > 1.0:
        self.run_one_ts = time()
        for i, item in list(self.eventdict.items()): 
          if self.tag_list_active != self.dbline.eve_school.id:
            self.tag_list_active = self.dbline.eve_school.id
            self.tag_list = get_taglist(self.tag_list_active)
          self.check_events(i, item) 
      while self.motion_frame[2] <= frame[2] + self.dbline.eve_sync_factor:
        #print(self.motion_frame[2], frame[2], self.motion_frame[2] - frame[2], self.active_pred_count)
        if self.active_pred_count:
          if not self.pred_deque:
            predictions = self.tf_worker.get_from_outqueue(self.tf_w_index)
            for i in range(predictions.shape[0]):
              self.pred_deque.append(predictions[i]) 
          self.motion_frame = self.frame_queue.get()
          #print('*****', self.motion_frame[2:])
          self.motion_frame.append(self.pred_deque.popleft())
          with self.active_pred_lock:
            self.active_pred_count -= 1
          margin = self.dbline.eve_margin
          found = None
          for i, item in list(self.eventdict.items()):
            if hasoverlap((self.motion_frame[3]-margin, self.motion_frame[4]+margin, 
                self.motion_frame[5]-margin, self.motion_frame[6]+margin), item):
              found = item
              break
          if found is None or found.check_out_ts:
            new_event = c_event(self.tf_worker, self.tf_w_index, self.motion_frame, 
              margin, self.dbline, self.logger)
            with self.eventdict_lock:
              self.eventdict[new_event.dbline.id] = new_event
          else: 
            found.add_frame(self.motion_frame) 
          self.merge_events()
        else:
          break
      if frame[0]:
        self.display_events(frame)
      if self.dbline.eve_view:
        fps = self.som.gettime()
        if fps:
          self.dbline.eve_fpsactual = fps
          while True:
            try:
              stream.objects.filter(id = self.dbline.id).update(eve_fpsactual = fps)
              break
            except OperationalError:
              connection.close()
          self.redis.fps_to_dev('E', self.dbline.id, fps)

  def read_conditions(self):
    self.cond_dict = {1:[], 2:[], 3:[], 4:[], 5:[]}
    condition_lines = evt_condition.objects.filter(eventer_id=self.dbline.id)
    for item in condition_lines:
      self.cond_dict[item.reaction].append(model_to_dict(item))

  def merge_events(self):
    while True:
      del_set = set()
      with self.eventdict_lock:
        i_list = list(self.eventdict.items())
      j_list = i_list
      for i, event_i in i_list:
        if not event_i.check_out_ts:
          for j, event_j in j_list:
            if j > i:
              if not event_j.check_out_ts:
                if hasoverlap(event_i, event_j):
                  event_i[0] = min(event_i[0], event_j[0])
                  event_i[1] = max(event_i[1], event_j[1])
                  event_i[2] = min(event_i[2], event_j[2])
                  event_i[3] = max(event_i[3], event_j[3])
                  event_i.start = min(event_i.start, event_j.start)
                  event_i.end = max(event_i.end, event_j.end)
                  event_i.merge_frames(event_j)
                  del_set.add(j) 
      if del_set:     
        with self.eventdict_lock:
          for j in del_set:
            if j in self.eventdict:
              del self.eventdict[j]
      else:
        break

  def display_events(self, frame):
    try:
      newimage = frame[1].copy()
      with self.display_lock:
        eventlist = list(self.eventdict.items())
        for i, item in eventlist:
          if not item.check_out_ts:
            predictions = item.pred_read(max=1.0)
            if self.dbline.eve_all_predictions or (self.nr_of_cond_ed > 0):
              if self.nr_of_cond_ed <= 0:
                self.last_cond_ed = 1
              if resolve_rules(self.cond_dict[self.last_cond_ed], predictions):
                colorcode= (0, 0, 255)
              else:
                colorcode= (0, 255, 0)
              displaylist = [(j, predictions[j]) for j in range(1, len(self.tag_list)) 
                if predictions[j] >= 0.5]
              displaylist.sort(key=lambda x: -x[1])
              displaylist = displaylist[:3]
              if displaylist:
                cv.rectangle(newimage, rect_btoa(item), colorcode, self.linewidth)
                if item[2] < (self.dbline.cam_yres - item[3]):
                  y0 = item[3] + 30 * self.textheight
                else:
                  y0 = item[2] - (10 + (len(displaylist) - 1) * 30) * self.textheight
                for j in range(len(displaylist)):
                  cv.putText(newimage, 
                    self.tag_list[displaylist[j][0]].name[:3]
                    +' - '+str(round(displaylist[j][1],2)), 
                    (item[0]+2, y0 + j * 30 * self.textheight), 
                    cv.FONT_HERSHEY_SIMPLEX, self.textheight, colorcode, 
                    self.textthickness, cv.LINE_AA)
            else:
              imax = -1
              pmax = -1
              for j in range(1,len(predictions)):
                if predictions[j] >= 0.0:
                  if predictions[j] > pmax:
                    pmax = predictions[j]
                    imax = j
              if resolve_rules(self.cond_dict[1], predictions):
                cv.rectangle(newimage, rect_btoa(item), (255, 0, 0), 
                  self.linewidth)
                cv.putText(newimage, self.tag_list[imax].name[:3], 
                  (item[0]+10, item[2]+30), 
                  cv.FONT_HERSHEY_SIMPLEX, self.textheight, (255, 0, 0), 
                    self.textthickness, cv.LINE_AA)
      self.viewer.inqueue.put((3, newimage, frame[2]))
    except:
      self.logger.error(format_exc())
      self.logger.handlers.clear()

  def make_webm(self):
    setproctitle('CAM-AI-Eventer(WEBM) #'+str(self.dbline.id))
    while True:
      with self.webm_lock:
        the_start = self.redis.get('webm_queue:' + str(self.id) + ':start')
        if the_start == b'stop':
          return()
        else:
          the_start = int(the_start)  
        the_end = int(self.redis.get('webm_queue:' + str(self.id) + ':end'))
        if (the_end > 0) and (the_end == the_start):
          self.redis.set('webm_queue:' + str(self.id) + ':start', 0)
          self.redis.set('webm_queue:' + str(self.id) + ':end', 0)
      if the_end > the_start:
        the_start += 1
        savepath = (self.redis.get('webm_queue:' + str(self.id) + ':item:' 
          + str(the_start)).decode("utf-8"))
        self.redis.delete('webm_queue:' + str(self.id) + ':item:' + str(the_start))
        self.redis.set('webm_queue:' + str(self.id) + ':start', str(the_start))
        nice(19)
        myts = time()
        run([
          'ffmpeg', 
          '-v', 'fatal', 
          '-i', savepath, 
          '-crf', '51', #0 = lossless, 51 = very bad
          '-vf', 'scale=500:-1',
          savepath[:-4]+'.webm'
        ])
        self.logger.info('WEBM-Conversion: E' + str(self.id) + ' ' 
          + str(round(time() - myts)) + ' sec')
      else:
        sleep(djconf.getconfigfloat('long_brake', 5.0))
    

  def check_events(self, i, item):
    try:
      if (item.end < time() - self.dbline.eve_event_time_gap 
          or item.end > item.start + 120.0):
        item.check_out_ts = item.end
      if self.cond_dict[5]:
        predictions = item.pred_read(max=1.0)
      else:
        predictions = None   
      if resolve_rules(self.cond_dict[5], predictions):
        alarm(self.dbline.id, predictions) 
      if item.check_out_ts:
        if predictions is None and self.cond_dict[2]:
          predictions = item.pred_read(max=1.0)
        item.goes_to_school = resolve_rules(self.cond_dict[2], predictions)
        if predictions is None and self.cond_dict[3]:
          predictions = item.pred_read(max=1.0)
        item.isrecording = resolve_rules(self.cond_dict[3], predictions)
        if predictions is None and self.cond_dict[4]:
          predictions = item.pred_read(max=1.0)
        if resolve_rules(self.cond_dict[4], predictions):
          item.to_email = self.dbline.eve_alarm_email
        else:
          item.to_email = ''
        is_ready = True
        if item.goes_to_school or item.isrecording or item.to_email:
          if item.isrecording:
            if (self.vid_deque and 
                (item.check_out_ts <= (self.vid_deque[-1][2]))):
              my_vid_list = []
              my_vid_str = ''
              my_vid_start = None
              for v_item in self.vid_deque:
                if (item.start <= v_item[2]):
                  if not my_vid_start:
                    #10 seconds video length plus average trigger delay from checkmp4
                    my_vid_start = (v_item[2] - 10.5)
                  my_vid_end = v_item[2]
                  my_vid_list.append(v_item[1])
                  my_vid_str += str(v_item[0])
              vid_offset = item.focus_time - my_vid_start
              vid_offset = max(vid_offset, 0.0)
              if my_vid_str in self.vid_str_dict:
                item.savename=self.vid_str_dict[my_vid_str]
                isdouble = True
              else:
                item.savename = ('E_'
                  +str(item.dbline.id).zfill(12)+'.mp4')
                savepath = (self.recordingspath + item.savename)
                if len(my_vid_list) == 1: 
                  copyfile(self.recordingspath + my_vid_list[0], savepath)
                else:
                  tempfilename = (self.recordingspath + 'T_'
                    + str(item.dbline.id).zfill(12)+'.temp')
                  with open(tempfilename, 'a') as f1:
                    for line in my_vid_list:
                      f1.write('file ' + path.abspath(self.recordingspath + line) + '\n')
                  run(['ffmpeg', 
                    '-f', 'concat', 
                    '-safe', '0', 
                    '-v', 'fatal', 
                    '-i', tempfilename, 
                    '-codec', 'copy', 
                    savepath])
                  remove(tempfilename)
                self.vid_str_dict[my_vid_str] = item.savename
                isdouble = False
              item.dbline.videoclip = item.savename[:-4]
              item.dbline.double = isdouble
              item.dbline.save()
              if not isdouble:
                run([
                  'ffmpeg', 
                  '-ss', str(vid_offset), 
                  '-v', 'fatal', 
                  '-i', savepath, 
                  '-vframes', '1', 
                  '-q:v', '2', 
                  savepath[:-4]+'.jpg'
                ])
                with self.webm_lock:
                  the_end = int(self.redis.get('webm_queue:' + str(self.id) + ':end'))
                  the_end += 1
                  self.redis.set('webm_queue:' + str(self.id) + ':item:' + str(the_end), 
                    savepath)
                  self.redis.set('webm_queue:' + str(self.id) + ':end', 
                    str(the_end))
            else:  
              is_ready = False
          if is_ready:
            if not item.save(self.cond_dict):
              while True:
                try:
                  item.dbline.delete()
                  break  
                except OperationalError:
                  connection.close()  
        else:
          while True:
            try:
              item.dbline.delete()
              break  
            except OperationalError:
              connection.close()  
        if is_ready:
          with self.eventdict_lock:
            with self.display_lock:
              del self.eventdict[i]
    except:
      self.logger.error(format_exc())
      self.logger.handlers.clear()

  def inserter(self):
    try:
      detector_buffer = deque()
      detector_to = None
      while (not self.tf_worker.check_ready(self.tf_w_index)):
        sleep(djconf.getconfigfloat('long_brake', 1.0))
      while self.do_run:
        if self.detectorqueue.empty():
          frame = None
        else:
          image, numbers = self.detectorqueue.get()
          np_image = np.frombuffer(image, dtype=np.uint8)
          np_image = np_image.reshape(numbers[5]-numbers[4], numbers[3]-numbers[2], 3)
          frame = [numbers[0], np_image] + list(numbers[1:])
          self.frame_queue.put(frame)
        if frame:
          if not self.dbline.cam_xres:
            self.dbline.refresh_from_db(fields=['cam_xres', 'cam_yres', ])
          if detector_to is None:
            detector_to = frame[2]
          detector_buffer.append(frame)
          if len(detector_buffer) < 16 and (new_time := frame[2]) - detector_to < 0.1:
            detector_to = new_time
            continue
          detector_to = new_time
          if detector_buffer:
            imglist = []  
            for item in detector_buffer:
              np_image = cv.cvtColor(item[1], cv.COLOR_BGR2RGB)
              imglist.append(np_image)
            if self.tf_w_index is not None:
              while True:
                try:
                  school_id = self.dbline.eve_school.id
                  break
                except OperationalError:
                  connection.close()
              self.tf_worker.ask_pred(
                school_id, 
                imglist, 
                self.tf_w_index,
              )
              with self.active_pred_lock:
                self.active_pred_count += len(detector_buffer)
            detector_buffer.clear()
        else:  
          sleep(djconf.getconfigfloat('short_brake', 0.1))
    except:
      self.logger.error(format_exc())
      self.logger.handlers.clear()

  def set_cam_counts(self):
    if any([len(self.cond_dict[x]) for x in range(2,6)]):
      self.add_data_count() #just switch 0 or 1
    else:
      self.take_data_count()
    if self.cond_dict[3]:
      self.add_record_count()
    else:
      self.take_record_count()

  def build_string(self, i):
    if i['c_type'] == 1:
	    result = 'Any movement detected'
    elif  i['c_type'] in {2, 3}:
	    result = str(i['x'])+' predictions are '
    elif i['c_type']  in {4, 5}:
	    result = 'Tag "'+self.tag_list[i['x']].name+'" is '
    elif i['c_type'] == 6:
	    result = ('Tag "'+self.tag_list[i['x']].name+'" is in top '
        +str(round(i['y'])))
    if i['c_type'] in {2,4}:
	    result += 'above or equal '+str(i['y'])
    elif i['c_type'] in {3,5}:
	    result += 'below or equal '+str(i['y'])
    return(result)   
      
  def reset(self):  
    self.inqueue.put(('reset', ))

  def stop(self):
    self.redis.set('webm_queue:' + str(self.id) + ':start', 'stop')
    self.dataqueue.stop()
    super().stop()
    
