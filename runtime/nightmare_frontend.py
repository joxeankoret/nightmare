#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nightmare Fuzzing Project web frontend
Created on Sat May 18 21:35:33 2013
@author: joxean
"""

import os
import sys
import web
import json


from hashlib import sha1
from zipfile import ZipFile
from tempfile import mkstemp
from base64 import b64decode
from web import form, background
from web.background import background, backgrounder

from nfp_db import init_web_db, webpy_connect_db as connect_db
from nfp_queue import get_queue
from config import NFP_USER, NFP_PASS
from kfuzzy import CKoretFuzzyHashing
from diff_match_patch import diff_match_patch

from inmemoryzip import InMemoryZip

#-----------------------------------------------------------------------
urls = (
    '/', 'index',
    '/config', 'config',
    '/users', 'users',
    '/projects', 'projects',
    '/engines', 'mutation_engines',
    '/project_engines', 'project_engines',
    '/nodes', 'nodes',
    '/results', 'results',
    '/bugs', 'bugs',
    '/statistics', 'statistics',
    '/login', 'login',
    '/logout', 'logout',
    '/favicon.ico', 'favicon',
    '/add_project', 'add_project',
    '/edit_project', 'edit_project',
    '/del_project', 'del_project',
    '/add_mutation_engine', 'add_mutation_engine',
    '/edit_mutation_engine', 'edit_mutation_engine',
    '/del_mutation_engine', 'del_mutation_engine',
    '/update_project_engine', 'update_project_engine',
    '/view_crash', 'view_crash',
    '/download_sample', 'download_sample',
    '/find_samples', 'find_samples',
    '/find_original', 'find_original',
    '/show_diff', 'show_diff',
    '/download_project', 'download_project',
    '/triggers', 'triggers'
)

app = web.application(urls, globals())
render = web.template.render('templates/')
if web.config.get('_session') is None:
  session = web.session.Session(app, web.session.DiskStore('sessions'), {'user':None})
  web.config._session = session
else:
  session = web.config._session

register_form = form.Form(
  form.Textbox("username", description="Username"),
  form.Password("password", description="Password"),
  form.Button("submit", type="submit", description="Login"),
  validators = [
    form.Validator("All fields are mandatory", lambda i: i.username == "" or i.password == "")]
)

#-----------------------------------------------------------------------
# FUNCTIONS

#-----------------------------------------------------------------------
def myrepr(buf):
  if buf:
    return repr(buf)
  return

#-----------------------------------------------------------------------
# CLASSES

#-----------------------------------------------------------------------
class favicon: 
  def GET(self): 
    f = open("static/favicon.ico", 'rb')
    return f.read()

#-----------------------------------------------------------------------
class login:
  def POST(self):
    i = web.input(username="", password="")
    if i.username == "" or i.password == "":
      return render.error("Invalid username or password")
    elif i.username != NFP_USER or sha1(i.password).hexdigest() != NFP_PASS:
      return render.error("Invalid username or password")
    session.user = i.username
    return web.seeother("/")

#-----------------------------------------------------------------------
class logout:
  def GET(self):
    session.user = None
    del session.user
    return web.seeother("/")

#-----------------------------------------------------------------------
class nodes:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    return render.nodes()

#-----------------------------------------------------------------------
class index:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    return render.index()

#-----------------------------------------------------------------------
class config:
  def POST(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    
    i = web.input(samples_path="", templates_path="", nightmare_path="")
    if i.samples_path == "" or i.templates_path == "" or \
       i.nightmare_path == "":
      render.error("Invalid samples, templates or nightmare path")
    
    db = init_web_db()
    with db.transaction():
      sql = "select 1 from config where name = 'SAMPLES_PATH'"
      res = list(db.query(sql))
      if len(res) > 0:
        sql = "update config set value = $value where name = 'SAMPLES_PATH'"
      else:
        sql = "insert into config (name, value) values ('SAMPLES_PATH', $value)"
      db.query(sql, vars={"value":i.samples_path})

      sql = "select 1 from config where name = 'TEMPLATES_PATH'"
      res = list(db.query(sql))
      if len(res) > 0:
        sql = "update config set value = $value where name = 'TEMPLATES_PATH'"
      else:
        sql = "insert into config (name, value) values ('TEMPLATES_PATH', $value)"
      db.query(sql, vars={"value":i.templates_path})
      
      sql = "select 1 from config where name = 'NIGHTMARE_PATH'"
      res = list(db.query(sql))
      if len(res) > 0:
        sql = "update config set value = $value where name = 'NIGHTMARE_PATH'"
      else:
        sql = "insert into config (name, value) values ('NIGHTMARE_PATH', $value)"
      db.query(sql, vars={"value":i.nightmare_path})
      
      sql = "select 1 from config where name = 'QUEUE_HOST'"
      res = list(db.query(sql))
      if len(res) > 0:
        sql = "update config set value = $value where name = 'QUEUE_HOST'"
      else:
        sql = "insert into config (name, value) values ('QUEUE_HOST', $value)"
      db.query(sql, vars={"value":i.queue_host})

      sql = "select 1 from config where name = 'QUEUE_PORT'"
      res = list(db.query(sql))
      if len(res) > 0:
        sql = "update config set value = $value where name = 'QUEUE_PORT'"
      else:
        sql = "insert into config (name, value) values ('QUEUE_PORT', $value)"
      db.query(sql, vars={"value":i.queue_port})

    return web.redirect("/config")

  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    
    db = init_web_db()
    sql = """select name, value
               from config
              where name in ('SAMPLES_PATH', 'TEMPLATES_PATH', 'NIGHTMARE_PATH',
                             'QUEUE_HOST', 'QUEUE_PORT')"""
    res = db.query(sql)
    
    samples_path = ""
    templates_path = ""
    nightmare_path = ""
    queue_host = "localhost"
    queue_port = 11300
    for row in res:
      name, value = row.name, row.value
      if name == 'SAMPLES_PATH':
        samples_path = value
      elif name == 'TEMPLATES_PATH':
        templates_path = value
      elif name == 'NIGHTMARE_PATH':
        nightmare_path = value
      elif name == 'QUEUE_HOST':
        queue_host = value
      elif name == 'QUEUE_PORT':
        queue_port = value

    return render.config(samples_path, templates_path, nightmare_path,
                          queue_host, queue_port)

#-----------------------------------------------------------------------
class users:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    return render.users()

#-----------------------------------------------------------------------
class projects:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)

    i = web.input(show_all=0)
    db = init_web_db()
    sql = "select * from projects order by date desc"
    res = db.query(sql)
    return render.projects(res, i.show_all)

#-----------------------------------------------------------------------
class add_project:
  def POST(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    
    i = web.input(name="", description="", subfolder="", tube_prefix="",
                  max_files=100, max_iteration=1000000)
    if i.name == "":
      return render.error("No project name specified")
    elif i.description == "":
      return render.error("No project description specified")
    elif i.tube_prefix == "":
      return render.error("Invalid tube prefix")
    
    db = init_web_db()
    with db.transaction():
      db.insert("projects", name=i.name, description=i.description,
              subfolder=i.subfolder, tube_prefix=i.tube_prefix, 
              maximum_samples=i.max_files, archived=0,
              maximum_iteration=i.max_iteration,
              date=web.SQLLiteral("CURRENT_DATE"))

    return web.redirect("/projects")

#-----------------------------------------------------------------------
class edit_project:
  def POST(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    i = web.input(id=-1, name="", description="", subfolder="",
                  tube_prefix="", enabled="", archived="")
    if i.id == -1:
      return render.error("Invalid project identifier")
    elif i.name == "":
      return render.error("No project name specified")
    elif i.description == "":
      return render.error("No project description specified")
    elif i.tube_prefix == "":
      return render.error("No tube prefix specified")

    if i.enabled == "on":
      enabled = 1
    else:
      enabled = 0
    
    if i.archived == "on":
      archived = 1
    else:
      archived = 0

    db = init_web_db()
    with db.transaction():
      enabled = i.enabled == "on"
      archived = i.archived == "on"
      db.update("projects", name=i.name, description=i.description, 
                subfolder=i.subfolder, tube_prefix=i.tube_prefix,
                maximum_samples=i.max_files, enabled=enabled,
                maximum_iteration=i.max_iteration,
                archived=archived, where="project_id = $project_id",
                vars={"project_id":i.id})
    return web.redirect("/projects")
  
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    i = web.input(id=-1)
    if i.id == -1:
      return render.error("Invalid project identifier")
    
    db = init_web_db()
    what = """project_id, name, description, subfolder, tube_prefix,
              maximum_samples, enabled, date, archived,
              maximum_iteration """
    where = "project_id = $project_id"
    vars = {"project_id":i.id}
    res = db.select("projects", what=what, where=where, vars=vars)
    res = list(res)
    if len(res) == 0:
      return render.error("Invalid project identifier")
    return render.edit_project(res[0])

#-----------------------------------------------------------------------
class del_project:
  def POST(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    i = web.input(id=-1, sure="")
    if i.id == -1:
      return render.error("Invalid project identifier")
    elif i.sure != "on":
      return render.error("You must check the \"I'm sure\" field.")
    
    db = init_web_db()
    with db.transaction():
      vars={"project_id":i.id}
      where = "project_id=$project_id"
      db.delete("projects", where=where, vars=vars)
    return web.redirect("/projects")

  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    i = web.input(id=-1)
    if i.id == -1:
      return render.error("Invalid project identifier")
    return render.del_project(i.id)

#-----------------------------------------------------------------------
class triggers:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)

    db = init_web_db()
    sql = "select * from triggers order by date desc"
    res = db.query(sql)
    return render.triggers(res)

#-----------------------------------------------------------------------
class mutation_engines:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    
    db = init_web_db()
    res = db.select("mutation_engines", order="date desc")
    return render.mutation_engines(res)

#-----------------------------------------------------------------------
class add_mutation_engine:
  def POST(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    i = web.input(name="", description="", command="")

    if i.name == "":
      return render.error("No mutation engine name specified")
    elif i.description == "":
      return render.error("No mutation engine description specified")
    elif i.command == "":
      return render.error("No mutation engine command specified")
    elif i.command.find("%INPUT%") == -1 and i.command.find("%TEMPLATES_PATH%") == -1:
      return render.error("No input template filename specified in the mutation engine command")
    elif i.command.find("%OUTPUT%") == -1:
      return render.error("No output mutated filename specified in the mutation engine command")
    
    db = init_web_db()
    with db.transaction():
      db.insert("mutation_engines", name=i.name, command=i.command,
                description=i.description, date=web.SQLLiteral("CURRENT_DATE"))
    return web.redirect("/engines")

#-----------------------------------------------------------------------
class edit_mutation_engine:
  def POST(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    i = web.input(id=-1, name="", description="", command="")
    if i.id == -1:
      return render.error("Invalid mutation engine identifier")
    elif i.name == "":
      return render.error("No mutation engine name specified")
    elif i.description == "":
      return render.error("No mutation engine description specified")
    elif i.command == "":
      return render.error("No mutation engine command specified")
    elif i.command.find("%INPUT%") == -1 and i.command.find("%TEMPLATES_PATH%") == -1:
      return render.error("No input template filename specified in the mutation engine command")
    elif i.command.find("%OUTPUT%") == -1:
      return render.error("No output mutated filename specified in the mutation engine command")
    
    db = init_web_db()
    with db.transaction():
      where = "mutation_engine_id = $id"
      vars = {"id":i.id}
      db.update("mutation_engines", name=i.name, command=i.command,
                description=i.description, where=where, vars=vars)
    return web.redirect("/engines")
  
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    i = web.input(id=-1)
    if i.id == -1:
      return render.error("Invalid project identifier")
    
    db = init_web_db()
    what = "mutation_engine_id, name, description, command, date"
    where = "mutation_engine_id = $id"
    vars = {"id":i.id}
    res = db.select("mutation_engines", what=what, where=where, vars=vars)
    res = list(res)
    if len(res) == 0:
      return render.error("Invalid mutation engine identifier")
    return render.edit_mutation_engine(res[0])

#-----------------------------------------------------------------------
class del_mutation_engine:
  def POST(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    i = web.input(id=-1, sure="")
    if i.id == -1:
      return render.error("Invalid mutation engine identifier")
    elif i.sure != "on":
      return render.error("You must check the \"I'm sure\" field.")
    
    db = init_web_db()
    with db.transaction():
      where = "mutation_engine_id = $id"
      vars = {"id":i.id}
      db.delete("mutation_engines", where=where, vars=vars)
    return web.redirect("/engines")
  
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    i = web.input(id=-1)
    if i.id == -1:
      return render.error("Invalid mutation engine identifier")
    return render.del_mutation_engine(i.id)

#-----------------------------------------------------------------------
class project_engines:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)

    db = init_web_db()
    what="project_id, name"
    where="archived != 1"
    order="enabled desc, project_id desc"
    projects = db.select("projects", what=what, where=where, order=order)

    what = "project_id, mutation_engine_id"
    rows = db.select("project_engines")
    project_engines = {}
    for row in rows:
      try:
        project_engines[row.project_id].append(row.mutation_engine_id)
      except:
        project_engines[row.project_id] = [row.mutation_engine_id]

    what = "mutation_engine_id, name"
    engines = list(db.select("mutation_engines", what=what))

    return render.project_engines(projects, project_engines, engines)

#-----------------------------------------------------------------------
class update_project_engine:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    
    i = web.input(engines=[], project_id=None)
    if i.project_id is None:
      return render.error("Invalid project identifier")

    db = init_web_db()
    with db.transaction():
      vars = {"id":i.project_id}
      where = "project_id = $id"
      db.delete("project_engines", where=where, vars=vars)

      # And insert ignoring errors all selected ones
      for engine in i.engines:
        try:
          db.insert("project_engines", project_id=i.project_id, 
                    mutation_engine_id = engine)
        except:
          pass

    web.seeother("/project_engines")

#-----------------------------------------------------------------------
class results:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    
    i = web.input(show_all=0)

    db = init_web_db()
    # XXX: There is neither CONV nor CONCAT functions in either PgSQL or
    # SQLite so, in order to support them, I have to create a function
    # for both SQLite and PgSQL to mimic this behaviour.
    sql = """ select crash_id, p.project_id, p.name, sample_id,
                     concat("0x", CONV(program_counter, 10, 16)) pc,
                     crash_signal, exploitability, disassembly, c.date
                from crashes c,
                     projects p
               where p.project_id = c.project_id
                 and p.enabled = 1
               order by crash_id desc """
    res = db.query(sql)
    results = {}
    for row in res:
      project_name = row.name
      try:
        results[project_name].append(row)
      except:
        results[project_name] = [row]

    return render.results(results, i.show_all)

#-----------------------------------------------------------------------
class bugs:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    
    db = init_web_db()
    sql = """ select concat('0x???????', substr(conv(program_counter, 10, 16), length(conv(program_counter, 10, 16))-2)) address,
                     crash_signal, substr(disassembly, instr(disassembly, ' ')+1) dis, count(*) count
                from crashes c,
                     projects p
               where p.project_id = c.project_id
                 and crash_signal != 'UNKNOWN'
                 and p.enabled = 1
               group by 1
               order by 4 desc"""
    bugs = list(db.query(sql))
    return render.bugs(bugs)

#-----------------------------------------------------------------------
class view_crash:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)

    i = web.input()
    if not i.has_key("id"):
      return render.error("No crash identifier given")

    # XXX: FIXME: Joxean, why do 2 queries instead of one????
    # Get the project_id from the crash_id
    crash_id = i.id
    db = init_web_db()
    vars = {"id":crash_id}
    res = db.select("crashes", where="crash_id=$id", vars=vars)
    crash_row = res[0]

    # Get the project name
    where = "project_id=$id"
    vars = {"id":crash_row.project_id}
    res = db.select("projects", what="name", where=where, vars=vars)
    project_name = res[0].name
    
    crash_data = {}
    crash_data["crash_id"] = crash_row.crash_id
    crash_data["project_id"] = crash_row.project_id
    crash_data["sample_id"] = crash_row.sample_id
    crash_data["program_counter"] = crash_row.program_counter
    crash_data["crash_signal"] = crash_row.crash_signal
    crash_data["exploitability"] = crash_row.exploitability
    crash_data["disassembly"] = crash_row.disassembly
    crash_data["date"] = crash_row.date
    crash_data["total_samples"] = crash_row.total_samples

    additional = json.loads(crash_row.additional)
    crash_data["additional"] = additional

    return render.view_crash(project_name, crash_data, str=str, map=map, repr=myrepr, b64=b64decode)

#-----------------------------------------------------------------------
class download_sample:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)

    i = web.input()
    if not i.has_key("id"):
      return render.error("No crash identifier given")
    if i.has_key("diff"):
      is_diff = True
    else:
      is_diff = False

    db = init_web_db()
    what = "sample_hash"
    where = "sample_id = $id"
    vars = {"id":i.id}
    res = db.select("samples", what=what, where=where, vars=vars)
    res = list(res)
    if len(res) == 0:
      return render.error("Invalid crash identifier")
    row = res[0]
    sample_hash = row.sample_hash

    res = db.select("config", what="value", where="name='SAMPLES_PATH'")
    res = list(res)
    if len(res) == 0:
      return render.error("Invalid configuration value for 'SAMPLES_PATH'")
    row = res[0]

    path = os.path.join(row.value, "crashes")
    path = os.path.join(path, sample_hash)
    if not os.path.exists(path):
      return render.error("Crash sample does not exists! %s" % path)

    if is_diff:
      if not os.path.exists(path + ".diff"):
        return render.error("No diff file for this sample. It may be because the mutation engine doesn't generate a diff file.")
      else:
        sample_hash += ".diff"
        path += ".diff"

    web.header("Content-type", "application/octet-stream")
    web.header("Content-disposition", "attachment; filename=%s" % sample_hash)
    f = open(path, 'rb')
    return f.read()

#-----------------------------------------------------------------------
class statistics:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    
    # XXX: TODO: IFNULL is not supported in PgSQL
    sql = """ select p.name,
                     sum(total) total_samples,
                     ifnull((
                        select count(*)
                          from samples s,
                               crashes c
                         where c.sample_id = s.sample_id
                           and project_id = p.project_id
                         group by project_id
                     ), 0) crashes,
                     (
                      select iteration
                        from statistics st
                       where st.project_id = p.project_id
                         and st.mutation_engine_id = -1
                     ) iteration
                from statistics s,
                     projects p,
                     mutation_engines m
               where p.project_id = s.project_id
                 and m.mutation_engine_id = s.mutation_engine_id
                 and p.enabled = 1
               group by p.name """
    db = init_web_db()
    project_stats = db.query(sql)

    sql = """ select distinct exploitability, count(*) count
                from crashes c,
                     projects p
               where p.project_id = c.project_id
                 and p.enabled = 1
               group by exploitability """
    exploitables = db.query(sql)

    sql = """ select distinct crash_signal, count(*) count
                from crashes c,
                     projects p
               where p.project_id = c.project_id
                 and p.enabled = 1
               group by crash_signal """
    signals = db.query(sql)

    sql = """select substr(disassembly, instr(disassembly, ' ')+1) dis, count(*) count
               from crashes c,
                    projects p
               where p.project_id = c.project_id
                and p.enabled = 1
              group by 1"""
    disassemblies = db.query(sql)

    # XXX: TODO: Neither concat nor conv are supported in either PgSQL
    # or SQLite so I need to create a function for these databases.
    sql = """ select concat('0x???????', substr(conv(program_counter, 10, 16), length(conv(program_counter, 10, 16))-2)) address,
                     crash_signal, substr(disassembly, instr(disassembly, ' ')+1) dis, count(*) count
                from crashes c,
                     projects p
               where p.project_id = c.project_id
                 and crash_signal != 'UNKNOWN'
                 and p.enabled = 1
               group by 1
               order by 4 desc"""
    bugs = db.query(sql)

    tubes = {}
    q = get_queue(watch=True, name="delete")
    for tube in q.tubes():
      if tube != "default":
        tubes[tube] = q.stats_tube(tube)["current-jobs-ready"]

    return render.statistics(project_stats, exploitables, signals, disassemblies, bugs, tubes)

#-----------------------------------------------------------------------
class find_samples:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)
    
    db = init_web_db()
    res = list(db.select("config", what="value", where="name = 'TEMPLATES_PATH'"))
    res = list(res)
    if len(res) == 0:
      return render.error("Samples path is not yet configured. Please configure it in the configuration section.")
    return render.find_samples(res[0].value)

  def POST(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)

    i = web.input()
    if not i.has_key('samples_dir'):
      return render.error("No samples sub-directory specified.")
    if not i.has_key('magic'):
      return render.error("No magic header specified.")
    if not i.has_key('extension'):
      return render.error("No file extension specified.")
    if not i.has_key('search'):
      search = ""
    else:
      search = i["search"]
    if i["samples_dir"].find(".") > -1 or \
       i["samples_dir"].find("/") > -1 or \
       i["samples_dir"].find("\\") > -1:
      return render.error("Invalid sub-directory")

    db = init_web_db()
    res = db.select("config", what="value", where="name = 'TEMPLATES_PATH'")
    res = list(res)
    if len(res) == 0:
      return render.error("Samples path is not yet configured. Please configure it in the configuration section.")
    whole_dir = os.path.join(res[0].value, i.samples_dir)

    if not os.path.exists(whole_dir):
      os.makedirs(whole_dir)

    from find_samples import CSamplesFinder
    finder = CSamplesFinder()
    finder.find(i.extension, i.magic, whole_dir, search)
    return render.message("Process finished.")

#-----------------------------------------------------------------------
def find_original_file(db, id):
  
  vars = {"id":id}
  where = "sample_id = $id"
  res = db.select("samples", what="sample_hash", where=where, vars=vars)
  res = list(res)
  if len(res) == 0:
    raise Exception("Invalid crash identifier")
  sample_hash = res[0].sample_hash

  res = db.select("config", what="value", where="name='SAMPLES_PATH'")
  res = list(res)
  if len(res) == 0:
    raise Exception("Invalid configuration value for 'SAMPLES_PATH'")

  path = os.path.join(res[0].value, "crashes")
  path = os.path.join(path, sample_hash)
  if not os.path.exists(path):
    raise Exception("Crash sample does not exists! %s" % path)

  magic = open(path, "rb").read(3)
  if magic == "PK\x03":
    z = ZipFile(path, "r")
    cmt = z.comment
    z.close()
    if cmt == "NIGHTMARE":
      raise Exception("Cannot find the original sample for ZIP archives created by Nightmare, sorry.")

  res = db.select("config", what="value", where="name = 'TEMPLATES_PATH'")
  res = list(res)
  if len(res) == 0:
    raise Exception("Invalid configuration value for 'TEMPLATES_PATH'")
  templates_path = res[0].value

  sql = """select p.subfolder subfolder
             from projects p,
                  crashes c
            where c.sample_id = $id
              and p.project_id = c.project_id"""
  vars = {"id":id}
  res = db.query(sql, vars=vars)
  res = list(res)
  if len(res) == 0:
    raise Exception("Cannot find the project associated to the crash identifier")

  project_path = os.path.join(templates_path, res[0].subfolder)
  if not os.path.exists(project_path):
    raise Exception("Cannot find path '%s'" % project_path)

  kfh = CKoretFuzzyHashing()
  kfh.bsize = 16
  h1, h2, h3 = kfh.hash_file(path).split(";")

  original_file = None
  for f in os.listdir(project_path):
    filename = os.path.join(project_path, f)
    if not os.path.isfile(filename):
      continue

    tmp1, tmp2, tmp3 = kfh.hash_file(filename).split(";")
    if h1 == tmp1 and h2 == tmp2 and h3 == tmp3:
      original_file = filename
      break
    elif h1 == tmp1 or h2 == tmp2 or h3 == tmp3:
      original_file = filename
      break

  return original_file, path

#-----------------------------------------------------------------------
class find_original:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)

    i = web.input()
    if not i.has_key("id"):
      return render.error("No crash identifier given")
    if i.has_key("diff"):
      is_diff = True
    else:
      is_diff = False

    db = init_web_db()

    try:
      original_file, crash_file = find_original_file(db, i.id)
    except:
      return render.error(sys.exc_info()[1])

    if original_file is not None:
      basename = os.path.basename(original_file)
      web.header("Content-type", "application/octet-stream")
      web.header("Content-disposition", "attachment; filename=%s" % basename)
      f = open(original_file, 'rb')
      return f.read()

    return render.error("Cannot find original sample.")

#-----------------------------------------------------------------------
def hexdump(src, length=16):
  FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
  lines = []
  for c in xrange(0, len(src), length):
    chars = src[c:c+length]
    hex = ' '.join(["%02x" % ord(x) for x in chars])
    printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or '.') for x in chars])
    lines.append("%04x  %-*s  %s\n" % (c, length*3, hex, printable))
  return ''.join(lines)

#-----------------------------------------------------------------------
class show_diff:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)

    i = web.input()
    if not i.has_key("id"):
      return render.error("No crash identifier given")
    if i.has_key("diff"):
      is_diff = True
    else:
      is_diff = False

    db = connect_db()

    original_file, crash_file = find_original_file(db, i.id)
    if original_file is None:
      return render.error("Cannot find original sample.")

    dmp = diff_match_patch()
    buf1 = open(original_file, "rb").read()
    buf2 = open(crash_file, "rb").read()
    differences = dmp.diff_main(buf1, buf2, False, False)

    return render.show_diff(original_file, crash_file, buf1, buf2, \
                             differences, hexdump)

#-----------------------------------------------------------------------
def get_sample_files(db, i, crash_id):
  sql = """ select sample_hash
              from samples s,
                   crashes c
             where c.crash_id = $id
               and s.sample_id = c.sample_id """
  res = db.query(sql, vars={"id":crash_id})
  res = list(res)
  if len(res) == 0:
    return render.error("Invalid crash identifier")
  row = res[0]
  sample_hash = row.sample_hash

  res = db.select("config", what="value", where="name = 'SAMPLES_PATH'")
  res = list(res)
  if len(res) == 0:
    return render.error("Invalid configuration value for 'SAMPLES_PATH'")
  
  path = os.path.join(res[0].value, "crashes")
  path = os.path.join(path, sample_hash)
  print path
  if not os.path.exists(path):
    return render.error("Crash sample does not exists! %s" % path)

  ret = [path]
  if os.path.exists(path + ".diff"):
    ret.append(path + ".diff")
  return ret

#-----------------------------------------------------------------------
class download_project:
  def GET(self):
    if not 'user' in session or session.user is None:
      f = register_form()
      return render.login(f)

    i = web.input()
    if not i.has_key("id"):
      return render.error("No project identifier given")

    db = init_web_db()
    sql = """ select min(crash_id) crash_id, concat('0x', substr(conv(program_counter, 10, 16), length(conv(program_counter, 10, 16))-2)) address,
                     crash_signal, substr(disassembly, instr(disassembly, ' ')+1) dis, count(*) count
                from crashes c,
                     projects p
               where p.project_id = c.project_id
                 and crash_signal != 'UNKNOWN'
                 and c.project_id = $id
               group by 2
               order by 5 desc """
    res = db.query(sql, vars={"id":i.id})

    imz = InMemoryZip()
    i = 0
    for row in res:
      i += 1
      samples = get_sample_files(db, i, row.crash_id)
      folder = "bug%d" % i
      imz.append("%s/notes.txt" % folder, ", ".join(map(str, row.values())) + "\n")
      for sample in samples:
        try:
          imz.append("%s/%s" % (folder, os.path.split(sample)[1]), open(sample, "rb").read())
          
          if sample.endswith(".diff"):
            with open(sample, "rb") as f:
              line = f.readline().strip("\r").strip("\n")
              pos = line.find(" was ")
              if pos > -1:
                original_file = line[pos+5:]
                imz.append("%s/original" % folder, open(original_file, "rb").read())
        except:
          imz.append("%s/error.txt" % folder, "Error reading file: %s" % str(sys.exc_info()[1]))

    if i == 0:
      return render.error("There are no results for the specified project")

    # This is horrible
    file_handle, filename = mkstemp()
    imz.writetofile(filename)
    buf = open(filename, "rb").read()
    os.remove(filename)
    filename = sha1(buf).hexdigest()
    web.header("Content-type", "application/octet-stream")
    web.header("Content-disposition", "attachment; filename=%s.zip" % filename)
    return buf

if __name__ == "__main__":
  app.run()
