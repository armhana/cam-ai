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

from collections import OrderedDict
from .l_tools import version_flat, version_full

proc_dict = OrderedDict()

def temp_func():
  print('Upgrading to 1.4.5')  
proc_dict[version_flat('1.4.5')] = temp_func

def temp_func():
  print('Upgrading to 1.4.5a')  
proc_dict[version_flat('1.4.5a')] = temp_func

def temp_func():
  print('Upgrading to 1.4.6')  
proc_dict[version_flat('1.4.6')] = temp_func

def version_upgrade(old_str, new_str):
  oldflat = version_flat(old_str)
  newflat = version_flat(new_str)
  lastflat = oldflat
  if newflat <= oldflat:
    return()
  print('########## VersionUpgrade:', old_str, '--->',new_str)
  for item in proc_dict:
    if item > oldflat and item <= newflat:
      print(version_full(lastflat), '>', version_full(item))
      proc_dict[item]()
      lastflat = item
