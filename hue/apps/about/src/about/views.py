#!/usr/bin/env python
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import sys
import time

from multiprocessing import Process
from desktop.lib.django_util import render
from desktop.lib.paths import get_run_root, get_var_root
from django.http import HttpResponse
import simplejson as json

from sh import ErrorReturnCode, bash, sudo, service, chkconfig
from about import conf
import subprocess

LOG = logging.getLogger(__name__)

HUE_VERSION = "2.3.0"  # default version if VERSIONS file not exists

def index(request):
  if request.method == 'POST':
    error = ''
    try:
      bash(conf.TUTORIALS_UPDATE_SCRIPT.get())
    except Exception, ex:
      error = unicode(ex)
    result = {
      'tutorials': _get_tutorials_version(),
      'error': error
    }
    return HttpResponse(json.dumps(result))
  components, HUE_VERSION = _get_components()

  RAM = int(os.popen("free -m").readlines()[1].split()[1])/1024.
  return render('index.mako', request, {
    'components': components,
    'hue_version': HUE_VERSION,
    'ambari_status': _get_ambari_status(),
    'hbase_status': _get_hbase_status(),
    'RAM_ALERT': RAM < 3.5,
    'RAM': "%0.1f" % RAM,
  })

# ====== Ambari =======

def ambari(request, action):
  if request.method == 'POST':
    action = action.lower()
    if action == 'enable':
      return _enable_ambari(request)
    elif action == 'disable':
      return _disable_ambari(request)
    elif action == 'status':
      return _ambari_status(request)


def _fork(kill_parent=False, do_in_fork=None):
    try: 
        pid = os.fork() 
        if pid == 0:
          if do_in_fork:
            do_in_fork()
        else:
          if kill_parent:
            sys.exit(0)
    except OSError, e: 
        print >>sys.stderr, 'Unable to fork: %d (%s)' % (e.errno, e.strerror) 
        sys.exit(1)


def ambari_fork_start():
  def _in_fork():
    # remove references from the main process
    os.chdir('/')
    os.setsid()
    os.umask(0)

    def _doublefork():
      subprocess.call("sudo service ambari start", shell=True)

    _fork(kill_parent=True, do_in_fork=_doublefork)
    sys.exit(0)

  _fork(kill_parent=True, do_in_fork=_in_fork)

def _enable_ambari(request):
  error = ''
  ret = ''
  try:
    ret = sudo.chkconfig("ambari", "on").stdout

    # FIXME: sh module uses os.fork() to create child process, which is not appropriate to run ambari
    # ret += sudo.service("ambari", "start").stdout
    p = Process(target=ambari_fork_start)
    p.start()
    time.sleep(10)
    # subprocess.Popen(["sudo", "service", "ambari", "start"])
  except Exception, ex:
    error = unicode(ex)
  result = {
    'return': ret,
    'error': error
  }
  return HttpResponse(json.dumps(result))

def _disable_ambari(request):
  error = ''
  ret = ''
  try:
    ret = sudo.chkconfig("ambari", "off").stdout
    # ret += sudo.service("ambari", "stop").stdout
    subprocess.Popen(["sudo", "service", "ambari", "stop"])
  except Exception, ex:
    error = unicode(ex)
  result = {
    'return': ret,
    'error': error
  }
  return HttpResponse(json.dumps(result))

def _get_ambari_status():
  """Returns True if ambari-agent started and False otherwise."""
  from sh import ambari_agent
  try:
    ambari_agent("status")
  except ErrorReturnCode:
    return False
  return True

def _ambari_status(request):
  val = "on" if _get_ambari_status() else "off"
  result = {
    'return': val,
  }
  return HttpResponse(json.dumps(result))

# ====== HBase =======

def hbase(request, action):
  if request.method == 'POST':
    action = action.lower()
    if action == 'enable':
      return _enable_hbase(request)
    elif action == 'disable':
      return _disable_hbase(request)
    elif action == 'status':
      return _hbase_status(request)


def _enable_hbase(request):
  error = ''
  ret = ''
  try:
    ret = sudo.chkconfig("hbase-starter", "on").stdout
    ret += sudo.service("hbase-starter", "start").stdout
  except Exception, ex:
    error = unicode(ex)
  result = {
    'return': ret,
    'error': error
  }
  return HttpResponse(json.dumps(result))

def _disable_hbase(request):
  error = ''
  ret = ''
  try:
    ret = sudo.chkconfig("hbase-starter", "off").stdout
    ret += sudo.service("hbase-starter", "stop").stdout
  except Exception, ex:
    error = unicode(ex)
  result = {
    'return': ret,
    'error': error
  }
  return HttpResponse(json.dumps(result))

def _get_hbase_status():
  """Returns True if hbase master started and False otherwise."""
  try:
    sudo.kill("-0", file(conf.HBASE_PID_FILE.get()).read().strip())
  except (ErrorReturnCode, IOError):
    return False
  return True

def _hbase_status(request):
  val = "on" if _get_hbase_status() else "off"
  result = {
    'return': val,
  }
  return HttpResponse(json.dumps(result))

# ==================


def _get_tutorials_version():
  TUTORIAL_VERSION_FILE = os.path.join(conf.TUTORIALS_PATH.get(), 'version')
  try:
    with open(TUTORIAL_VERSION_FILE, 'r') as file_obj:
      tutorial_version = file_obj.readlines()[0].strip()
  except IOError, ex:
    tutorial_version = "undefined"
    msg = "Failed to open file '%s': %s" % (TUTORIAL_VERSION_FILE, ex)
    LOG.error(msg)
  return tutorial_version


def _read_versions(filename):
  global HUE_VERSION
  components = []
  with open(filename) as f:
    for line in f:
      l = line.strip().split("=")
      if len(l) < 2 or line.strip()[:1] == '#':
        continue
      component, version = l
      if component == "HUE_VERSION":
        HUE_VERSION, buildnumber = version.split("-")
        components.append(('Hue', version))
      elif component == "Sandbox":
        components.append(('Sandbox Build', version))
      elif component == "Ambari-server":
        components.append(('Ambari', version))
      else:
        components.append((component, version))
  return components


def _get_components():
  components = []
  try:
    components += _read_versions(os.path.join(get_run_root(), "VERSIONS"))
    extra_versions_path = os.path.join(get_var_root(), "EXTRA_VERSIONS")
    if os.path.exists(extra_versions_path):
      components += _read_versions(extra_versions_path)
  except ValueError:#Exception:
    components = [
      ('HDP', "2.0.6"),
      ('Hadoop', "1.2.0.1.3.0.0-107"),
      ('HCatalog', "0.11.0.1.3.0.0-107"),
      ('Pig', "0.11.1.1.3.0.0-107"),
      ('Hive', "0.11.0.1.3.0.0-107"),
      ('Oozie', "3.3.2.1.3.0.0-107")
    ]

  if conf.TUTORIALS_INSTALLED.get():
    components.insert(0, ('Tutorials', _get_tutorials_version()))
    components.insert(0, ("Sandbox", conf.SANDBOX_VERSION.get()))
  return components, HUE_VERSION
