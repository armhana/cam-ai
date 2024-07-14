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

import json
import numpy as np
import cv2 as cv
import aiofiles
import aiofiles.os
import aioshutil
from glob import glob
from os import path
from random import randint
from logging import getLogger
from datetime import datetime
from django.utils import timezone
from django.contrib.auth.models import User as dbuser
from django.core.paginator import Paginator
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.hashers import check_password
from tools.l_tools import ts2filename, djconf, uniquename_async
from tools.c_tools import reduce_image_async
from tools.djangodbasync import (filterlines, getoneline, savedbline, 
  deldbline, updatefilter, deletefilter, getonelinedict, filterlinesdict,
  countfilter)
from tools.c_logger import log_ini
from tools.l_crypt import l_crypt
from access.c_access import access
from access.models import access_control
from schools.c_schools import get_taglist, check_extratags_async
from tf_workers.c_tfworkers import tf_workers
from tf_workers.models import school, worker
from eventers.models import event, event_frame
from trainers.models import trainframe, img_size
from users.models import userinfo
from streams.models import stream

logname = 'ws_schoolsconsumers'
logger = getLogger(logname)
log_ini(logger, logname)
classes_list = get_taglist(1)
datapath = djconf.getconfig('datapath', 'data/')
schoolframespath = djconf.getconfig('schoolframespath', datapath + 'schoolframes/')
recordingspath = djconf.getconfig('recordingspath', datapath + 'recordings/')
schoolsdir = djconf.getconfig('schools_dir', datapath + 'schools/')
school_x_max = djconf.getconfigint('school_x_max', 500)
school_y_max = djconf.getconfigint('school_y_max', 500)

#*****************************************************************************
# SchoolDBUtil
#*****************************************************************************

class schooldbutil(AsyncWebsocketConsumer):

  @database_sync_to_async
  def gettags(self, myschool):
    return([line.description for line in get_taglist(myschool)])

  @database_sync_to_async
  def gettrainshortlist(self, page_nr):
    return(list(self.trainpage.get_elided_page_range(page_nr)))

  @database_sync_to_async
  def geteventshortlist(self, page_nr):
    return(list(self.eventpage.get_elided_page_range(page_nr)))

  async def connect(self):
    self.user = self.scope['user']
    if self.user.is_authenticated:
      self.tf_w_index = None
      await self.accept()
    else:
      await self.close()
    self.schoolinfo = None

  async def disconnect(self, close_code):
    if self.tf_w_index is not None:
      self.tf_worker.stop_out(self.tf_w_index)
      self.tf_worker.unregister(self.tf_w_index) 

  async def receive(self, text_data):
    logger.debug('<-- ' + text_data)
    params = json.loads(text_data)['data']

    if ((params['command'] == 'gettags') 
        or self.scope['user'].is_authenticated):
      outlist = {'tracker' : json.loads(text_data)['tracker']}
    else:
      await self.close()

    if params['command'] == 'settrainpage' :
      filterdict = {'school' : params['model']}
      if params['cbnot']:
        if not params['cbchecked']:
          filterdict['checked'] = 0
      else:
        if params['cbchecked']:
          filterdict['checked'] = 1
        else:
          filterdict['checked'] = -1 #Never
      if params['class'] == -2:
        pass
      elif params['class'] == -1:
        for i in range(0,10):
          filterdict['c'+str(i)] = 0
      else:
        filterdict['c'+str(params['class'])] = 1
      
      framelines = trainframe.objects.filter(**filterdict)
      self.trainpage = Paginator(framelines, params['pagesize'])
      outlist['data'] = 'OK'
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    if params['command'] == 'seteventpage' :
      if params['showdone']:
        eventlines = event.objects.filter(
          camera=params['streamnr'], 
          xmax__gt=-1, 
          deleted=False,
        ).order_by('-id')
      else:  
        eventlines = event.objects.filter(
          camera=params['streamnr'], 
          done=False, 
          xmax__gt=-1,
          deleted=False,
        ).order_by('-id')
      self.eventpage = Paginator(eventlines, params['pagesize'])
      outlist['data'] = 'OK'
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    if params['command'] == 'gettrainimages' :
      lines = []
      async for line in self.trainpage.page(params['page_nr']).object_list:
        made_by_nr = await sync_to_async(lambda: line.made_by)()
        if made_by_nr is None:
          made_by = ''
        else:
          made_by = made_by_nr.username
        lines.append({
          'id' : line.id, 
          'name' : line.name, 
          'made_by' : made_by,
          'cs' : [line.c0,line.c1,line.c2,line.c3,line.c4,line.c5,line.c6,
            line.c7,line.c8,line.c9,],
          'made' : line.made.strftime("%d.%m.%Y %H:%M:%S %Z"),
        })
      outlist['data'] = lines
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    if params['command'] == 'getevents' :
      lines = []
      async for line in self.eventpage.page(params['page_nr']).object_list:
        lines.append({
          'id' : line.id, 
          'p_string' : line.p_string, 
          'done' : line.done,
          'start' : line.start.strftime("%d.%m.%Y %H:%M:%S"),
          'end' : line.end.strftime("%d.%m.%Y %H:%M:%S"),
          'numframes' : line.numframes,
          'videoclip' : line.videoclip,
          'xmin' : line.xmin,
          'xmax' : line.xmax,
          'ymin' : line.ymin,
          'ymax' : line.ymax,
        })
      outlist['data'] = lines
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    if params['command'] == 'gettrainshortlist' :
      result = list(await self.gettrainshortlist(params['page_nr']))
      for i in range(len(result)):
        if not isinstance(result[i], int):
          result[i] = 0
      outlist['data'] = result
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    if params['command'] == 'geteventshortlist' :
      result = list(await self.geteventshortlist(params['page_nr']))
      for i in range(len(result)):
        if not isinstance(result[i], int):
          result[i] = 0
      outlist['data'] = result
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    elif params['command'] == 'gettags':
      outlist['data'] = await self.gettags(params['school'])
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    elif params['command'] == 'getpredictions':
      if await access.check_async('S', params['school'], self.scope['user'], 'R'):
        imglist = []
        for item in params['idxs']:
          try:
            if params['is_school']:
              frameline = await event_frame.objects.aget(id=item)
              imagepath = schoolframespath + frameline.name
              if self.schoolinfo is None:
                schoolline = await school.objects.aget(id=params['school'])
                xytemp = self.tf_worker.get_xy(schoolline.id, self.tf_w_index)
                self.schoolinfo = {'xdim' : xytemp[0], 'ydim' : xytemp[1], }
            else:
              frameline = await trainframe.objects.aget(id=item,)
              if self.schoolinfo is None:
                schoolline = await school.objects.aget(id=frameline.school)
                xytemp = self.tf_worker.get_xy(schoolline.id, self.tf_w_index)
                self.schoolinfo = {'xdim' : xytemp[0], 'ydim' : xytemp[1], 'schooldict' : schoolline, }
              imagepath = self.schoolinfo['schooldict'].dir + 'frames/' + frameline.name
            async with aiofiles.open(imagepath, mode = "rb") as f:
              myimage = await f.read()
            if frameline.encrypted:
              myimage = self.crypt.decrypt(myimage)  
            myimage = cv.imdecode(np.frombuffer(myimage, dtype=np.uint8), cv.IMREAD_UNCHANGED)
            myimage = cv.cvtColor(myimage, cv.COLOR_BGR2RGB)
            imglist.append(myimage)
          except FileNotFoundError:
            logger.error('File not found: ' + imagepath)
        self.tf_worker.ask_pred(
          params['school'], 
          imglist, 
          self.tf_w_index,
        )
        predictions = np.empty((0, len(classes_list)), np.float32)
        while predictions.shape[0] < len(imglist):
          predictions = np.vstack((predictions, self.tf_worker.get_from_outqueue(self.tf_w_index)))
        outlist['data'] = predictions.tolist()
        logger.debug('--> ' + str(outlist))
        await self.send(json.dumps(outlist))

    elif params['command'] == 'checktrainframe':
      frameline = await trainframe.objects.aget(id=params['img'],)
      if await access.check_async('S', frameline.school, self.user, 'W'):
        frameline.checked = True
        await frameline.asave(update_fields=('checked', ))
        outlist['data'] = 'OK'
        logger.debug('--> ' + str(outlist))
        await self.send(json.dumps(outlist))

    elif params['command'] == 'deltrainframe':
      frameline = await trainframe.objects.aget(id=params['img'],)
      if await access.check_async('S', params['school'], self.user, 'W'):
        schoolline = await school.objects.aget(id=params['school'])
        await frameline.adelete()
        framefile = schoolline.dir + 'frames/' + frameline.name
        if await aiofiles.os.path.exists(framefile):
          aiofiles.os.remove(framefile)
        else:
          logger.warning('deltrainframe - Delete did not find: ' + framefile)
      outlist['data'] = 'OK'
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    elif params['command'] == 'checkall':
      if await access.check_async('S', params['school'], self.user, 'W'):
        filterdict = {'school' : params['school']}
        if params['class'] == -2:
          pass
        elif params['class'] == -1:
          for i in range(0,len(classes_list)):
            filterdict['c'+str(i)] = 0
        else:
          filterdict['c'+str(params['class'])] = 1
        filterdict['id__gte'] = params['min_id']
        filterdict['id__lte'] = params['max_id']
        framelines = trainframe.objects.filter(**filterdict)
        #import pdb; pdb.set_trace()
        await framelines.aupdate(checked=1)
        outlist['data'] = 'OK'
        logger.debug('--> ' + str(outlist))
        await self.send(json.dumps(outlist))

    elif params['command'] == 'deleteall':
      if await access.check_async('S', params['school'], self.user, 'W'):
        filterdict = {'school' : params['school']}
        if params['class'] == -2:
          pass
        elif params['class'] == -1:
          for i in range(0,10):
            filterdict['c'+str(i)] = 0
        else:
          filterdict['c'+str(params['class'])] = 1
        filterdict['id__gte'] = params['min_id']
        filterdict['id__lte'] = params['max_id']
        if params['cbnot']:
          if params['cbchecked']:
            pass
          else:
            filterdict['checked'] = 0
        else:
          if params['cbchecked']:
            filterdict['checked'] = 1
          else:
            filterdict = None
        if filterdict is not None:
          schoolline = await school.objects.aget(id=params['school'])
          filepath = schoolline.dir
          framelines = trainframe.objects.filter(**filterdict)
          async for item in framelines:
            await item.adelete()
            framefile = filepath + 'frames/' + item.name
            if await aiofiles.os.path.exists(framefile):
              aiofiles.os.remove(framefile)
            else:
              logger.warning('deleteall - Delete did not find: ' + framefile)
        outlist['data'] = 'OK'
        logger.debug('--> ' + str(outlist))
        await self.send(json.dumps(outlist))

    elif params['command'] == 'copyall':
      # disabled. need check before being reactivated
      if access.check('S', params['school'], self.user, 'W'):
        filterdict = {'school' : params['school']}
        if params['class'] == -2:
          pass
        elif params['class'] == -1:
          for i in range(0,10):
            filterdict['c'+str(i)] = 0
        else:
          filterdict['c'+str(params['class'])] = 1
        filterdict['id__gte'] = params['min_id']
        filterdict['id__lte'] = params['max_id']
        if params['cbnot']:
          if params['cbchecked']:
            pass
          else:
            filterdict['checked'] = 0
        else:
          if params['cbchecked']:
            filterdict['checked'] = 1
          else:
            filterdict = None
        if filterdict is not None:
          schooldictin = await getonelinedict(school, {'id' : params['school'], }, ['dir'])
          sourcepath = schooldictin['dir']
          schooldictout = await getonelinedict(school, {'id' : 1, }, ['dir'])
          destpath = schooldictout['dir']
          list_for_copy = await filterlinesdict(trainframe, filterdict)
          for item in list_for_copy:
            if not (await check_extratags_async(params['school'], item)):
              destfilename = uniquename(destpath, path.splitext(item['name'])[0], 'bmp')  
              await aioshutil.copy(sourcepath + 'frames/' + item['name'], destpath + 'frames/' + destfilename)
              newitem = trainframe(made = item['made'],
                school = 1,
                name = destfilename,
                code = 'NE',
                c0 = item['c0'], c1 = item['c1'], c2 = item['c2'], c3 = item['c3'], 
                c4 = item['c4'], c5 = item['c5'], c6 = item['c6'], c7 = item['c7'], 
                c8 = item['c8'], c9 = item['c9'], 
                checked = False, made_by_id = item['made_by'],
                img_sizes = item['img_sizes'],
              )
              await savedbline(newitem)
        outlist['data'] = 'OK'
        logger.debug('--> ' + str(outlist))
        await self.send(json.dumps(outlist))

    elif params['command'] == 'register_ai':
      self.myschool = int(params['school'])
      if ('logout' in params) and params['logout'] and (self.myschool > 0):
        await self.disconnect(None)
      if self.myschool > 0:
        schoolline = await school.objects.aget(id=self.myschool)
        workerline = await worker.objects.aget(school__id=schoolline.id)
        self.tf_worker = tf_workers[workerline.id]
        self.tf_w_index = self.tf_worker.register()
        self.tf_worker.run_out(self.tf_w_index)
      outlist['data'] = 'OK'
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    elif params['command'] == 'geteventframes':
      framelines = event_frame.objects.filter(event__id=params['event'])
      result = []
      async for item in framelines:
        result.append(item.id)
      outlist['data'] = result
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    elif params['command'] == 'setcrypt':
      streamline = await stream.objects.aget(id=params['stream'])
      if streamline.encrypted:
        self.crypt =  l_crypt(key=streamline.crypt_key)
      else:
        self.crypt = None  
      outlist['data'] = 'OK'
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))

    elif params['command'] == 'settags':
      schoolline = await school.objects.aget(id=params['school'])
      modelpath = schoolline.dir
      if await access.check_async('S', params['school'], self.scope['user'], 'W'):
        eventline = await event.objects.aget(id=params['event']) 
        framelines = event_frame.objects.filter(event=eventline)
        i = 0
        async for item in framelines:
          pathadd = str(randint(0,99))+'/'
          await aiofiles.os.makedirs(modelpath + 'frames/' + pathadd, exist_ok=True)
          ts = datetime.timestamp(item.time)
          newname = await uniquename_async(modelpath + 'frames/', pathadd+ts2filename(ts, noblank=True), 'bmp')
          if eventline.done:
            t = await trainframe.objects.aget(id=item.trainframe)
            updatelist = []
            for j in range(10):
              tagname = 'c'+str(j)
              updatelist.append(tagname)
              setattr(item, tagname, params['cblist'][i][j])
            await t.asave(update_fields=updatelist)
          else:
            if item.encrypted:
              do_crypt = self.crypt
            else:
              do_crypt = None  
            await reduce_image_async(
              schoolframespath + item.name, 
              modelpath + 'frames/' + newname, 
              school_x_max, 
              school_y_max, 
              crypt=do_crypt
            )
            t = trainframe(
              made=item.time,
              school=params['school'],
              name=newname,
              code='NE',
              checked=0,
              made_by_id=self.user.id,
            )
            t.encrypted = False
            t.c0=params['cblist'][i][0]
            t.c1=params['cblist'][i][1] 
            t.c2=params['cblist'][i][2]
            t.c3=params['cblist'][i][3]
            t.c4=params['cblist'][i][4]
            t.c5=params['cblist'][i][5]
            t.c6=params['cblist'][i][6]
            t.c7=params['cblist'][i][7]
            t.c8=params['cblist'][i][8]
            t.c9=params['cblist'][i][9]
            await t.asave()
            item.trainframe = t.id
            await item.asave(update_fields=('trainframe', ))
          i += 1 
        eventline.done = True  
        await eventline.asave(update_fields=('done', ))

      outlist['data'] = 'OK'
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))		

    elif params['command'] == 'delevent':
      try:
        if params['eventnr'] == -1:
          eventlines = event.objects.filter(camera__id=params['streamnr'], xmax__gt=0)
          streamnr =  params['streamnr']
        elif params['eventnr'] == 0:
          eventlines = event.objects.filter(camera__id=params['streamnr'], xmax__gt=0, done=True)
          streamnr =  params['streamnr']
        else:
          eventlines = event.objects.filter(id=params['eventnr'])
          streamnr =  params['streamnr']
        if await access.check_async('C', streamnr, self.scope['user'], 'W'):
          async for eventline in eventlines:
            eventline.deleted = True
            await eventline.asave(update_fields = ['deleted'])
      except event.DoesNotExist:
        logger.warning('delevent - Did not find DB line: ' + str(params['eventnr']))
      outlist['data'] = 'OK'
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))			

    elif params['command'] == 'delitem':
      if params['dtype'] == 0:
        frameline = await event_frame.objects.aget(id=params['nr_todel'])
        eventline = await event.objects.aget(id=params['event_nr'])
        streamline = await stream.objects.aget(event__id=eventline.id)
        if await access.check_async('C', streamline.id, self.scope['user'], 'W'):
          frameline.deleted = True
          await frameline.asave(update_fields=('deleted', ))
      elif params['dtype'] == 1:
        eventline = await event.objects.aget(id=params['nr_todel'])
        streamline = await stream.objects.aget(event__id=eventline.id)
        if await access.check_async('C', streamline.id, self.scope['user'], 'W'):
          if await event.objects.filter(videoclip=eventline.videoclip).acount() <= 1:
            videofile = recordingspath + eventline.videoclip
            if await aiofiles.os.path.exists(videofile + '.mp4'):
              await aiofiles.os.remove(videofile + '.mp4')
            else:
              logger.warning('delitem - Delete did not find: ' + videofile + '.mp4')
            if await aiofiles.os.path.exists(videofile + '.webm'):
              await aiofiles.os.remove(videofile + '.webm')
            else:
              logger.warning('delitem - Delete did not find: ' + videofile + '.webm')
            if await aiofiles.os.path.exists(videofile + '.jpg'):
              await aiofiles.os.remove(videofile + '.jpg')
            else:
              logger.warning('delitem - Delete did not find: ' + videofile + '.jpg')
          eventline.videoclip = ''
          await eventline.asave(update_fields=('videoclip', ))
      outlist['data'] = 'OK'
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))		

    elif params['command'] == 'remfrschool':
      eventline = await event.objects.aget(id=params['event'])
      streamline = await stream.objects.aget(event__id=eventline.id)
      if await access.check_async('C', streamline.id, self.scope['user'], 'W'):
        eventline.done = True
        await eventline.asave(update_fields=('done', ))
      outlist['data'] = 'OK'
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))			

    elif params['command'] == 'setonetag':
      frameline = await trainframe.objects.aget(id=params['img'],)
      schoolline = await school.objects.aget(id=params['school'],)
      if access.check('S', schoolline.id, self.scope['user'], 'W'):
        fieldtochange = 'c'+params['cnt']
        setattr(frameline, fieldtochange, params['value'])
        await frameline.asave(update_fields=(fieldtochange, ))
        outlist['data'] = 'OK'
        logger.debug('--> ' + str(outlist))
        await self.send(json.dumps(outlist))		

    elif params['command'] == 'importimages':
      schoolline = await school.objects.aget(id=params['school'])
      modelpath = schoolline.dir
      if await access.check_async('S', params['school'], self.scope['user'], 'W'):
        for item in glob('temp/unpack/' + params['filesdir'] + '/*'):
          pathadd = str(randint(0,99))+'/'
          await aiofiles.os.makedirs(modelpath + 'frames/' + pathadd, exist_ok=True)
          filename = item.split('/')[-1]
          newname = await uniquename_async(modelpath + 'frames/', 
              pathadd + filename, 'bmp')
          await reduce_image_async(
            item, 
            modelpath + 'frames/' + newname, 
            school_x_max, 
            school_y_max, 
          )
          t = trainframe(
            made=timezone.make_aware(datetime.now()),
            school=params['school'],
            name=newname,
            code='NE',
            checked=0,
            made_by_id=self.user.id,
          )
          t.encrypted = False
          for i in range(10):
            tagname = 'c'+str(i)
            if params['tag'] == i:
              setattr(t, tagname, 1)
            else:
              setattr(t, tagname, 0)  
          await t.asave()
        await aioshutil.rmtree('temp/unpack/' + params['filesdir'])
      outlist['data'] = 'OK'
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))			

    elif params['command'] == 'delschool':
      if await access.check_async('S', params['school'], self.scope['user'], 'W'):
        schoolline = await school.objects.aget(id=params['school'])
        modelpath = schoolline.dir
        if (count := await stream.objects.filter(
            active=True, 
            eve_school=schoolline).acount()
          ):
          outlist['data'] = {
            'status' : 'streams_linked', 
            'count' : count, 
          }
        else:  
          await aioshutil.rmtree(modelpath)
          schoolline.active = False
          await schoolline.asave(update_fields=('active', ))
          outlist['data'] = {'status' : 'OK', }
      else:  
        outlist['data'] = {'status' : 'no_priv', }
      logger.debug('--> ' + str(outlist))
      await self.send(json.dumps(outlist))		

#*****************************************************************************
# SchoolUtil
#*****************************************************************************

class schoolutil(AsyncWebsocketConsumer):		
    
  async def check_create_school_priv(self, userid):
    if self.scope['user'].is_superuser:
      return(True)
    else:
      userinfoline = await userinfo.objects.aget(user=userid)
      limit = userinfoline.allowed_schools
      schoolcount = await school.objects.filter(creator__id=userid, active=True).acount()
      return((schoolcount, limit))

  async def receive(self, text_data=None, bytes_data=None):
    logger.debug('<-- ' + str(text_data))
    indict=json.loads(text_data)
    if indict['code'] == 'makeschool':
      userline = await dbuser.objects.aget(id=indict['user'])
      hash = userline.password
      if not check_password(indict['pass'], hash):
        result = {'status' : 'noauth'}
        await self.send(json.dumps(result))
        return()
      quota =  await self.check_create_school_priv(indict['user'])
      if quota[0] >= quota[1]:
        result = {'status' : 'nomore', 'quota' : quota}
        await self.send(json.dumps(result))
        return()
      quota = (quota[0] + 1, quota[1])
      newschool = school()
      newschool.name = indict['name']
      await newschool.asave()
      result = {'status' : 'OK', 'school' : newschool.id, 'quota' : quota }
      newaccess = access_control()
      newaccess.vtype = 'S'
      newaccess.vid = newschool.id
      newaccess.u_g = 'U'
      newaccess.u_g_nr = indict['user']
      newaccess.r_w = 'W'
      await newaccess.asave()
      await access.read_list_async()
      schooldir = schoolsdir + 'model' + str(newschool.id) + '/'
      await aiofiles.os.makedirs(schooldir+'frames', exist_ok=True)
      await aiofiles.os.makedirs(schooldir+'model', exist_ok=True)
      await aioshutil.copy(schoolsdir + 'model1/model/' + newschool.model_type + '.h5',
        schooldir + 'model/' + newschool.model_type + '.h5')
      newschool.dir = schooldir
      newschool.creator_id = indict['user']
      await newschool.asave(update_fields = ('dir', 'creator_id'))
      await self.send(json.dumps(result))				

