import cloudant
import json
import requests
import logging
import os
import subprocess
logging.basicConfig(filename='/var/log/supervisor/wsgi.log',level=logging.DEBUG)

_nginx_prefix = "protected"
_save_dir = "/database_attachments"

class StandIn(object):
    status_code = 403
    def json(self):
        return { "standin" : True }

    def raise_for_status(self):
        raise Denied("")
        pass

class LocalException(Exception):
    def __init__(self, msg):
        self.msg = json.dumps(msg)

class Authorized(LocalException):
    msg_type = "200 Ok"

class Denied(LocalException):
    msg_type = "403 Forbidden"

def log(msg):
    logging.info(msg)

class Handler(object):
    def __init__(self, env):
        self.env = env
        self.auth_req = False
        if self.env["PATH_INFO"] == "/auth":
          self.auth_req = True
        self.function = self.env["REQUEST_METHOD"]
        self.file_location = self.env.get("X-FILE", None)

    def authorization(self):
        if not self.auth_req: return
        name = ""
        fn = self.function
        info = self.path()
        data = {}
        if fn == "GET":
            name = '{db}/{id}'
        elif fn in ["PUT", "DELETE"]:
            name = '{db}/_design/nedm_default/_update/attachment/{id}'
            data = { "data" : json.dumps({ info["attachment"] : {} }) }
        else:
            raise Denied(dict(error=True, reason="disallowed method"))
        self.verify_user(name.format(**info), **data)

    def cleanup(self):
        if self.file_location is not None:
          try:
            os.unlink(self.file_location)
          except: pass

    def output_env(self):
        log(json.dumps(dict([(str(k), str(self.env[k])) for k in self.env])))

    def process_upload(self, save_path, db_path):
        adir = os.path.dirname(save_path)
        if not os.path.exists(adir):
            os.makedirs(adir)
        os.rename(self.file_location, save_path)
        md5 = subprocess.check_output(["md5sum", save_path]).split(' ')[0]
        ast = os.stat(save_path)
        fn = os.path.basename(save_path)
        push_dict = {
          fn : {
            "ondiskname" : fn,
            "time" : {
              "atime" : ast.st_atime,
              "ctime" : ast.st_ctime,
              "crtime": ast.st_ctime,
              "mtime" : ast.st_mtime,
            },
            "md5" : md5,
            "size" : ast.st_size
          }
        }
        return self.interact_with_db(db_path, 'put',data=json.dumps(push_dict))

    def process_delete(self, save_path, db_path):
        if os.path.exists(save_path):
            os.unlink(save_path)
        fn = os.path.basename(save_path)
        return self.interact_with_db(db_path, 'put',data=json.dumps({ fn : True}))

    def interact_with_db(self, path, verb, **kwargs):
        #return StandIn()
        all_cookies = self.env.get("HTTP_COOKIE", "").split("; ")
        ret_dict = dict([c.split('=') for c in all_cookies if c.find("=") != -1])
        acct = cloudant.Account("http://127.0.0.1:5984")
        return getattr(acct, verb)(path, cookies=ret_dict, **kwargs)

    def verify_user(self, path, **kwargs):
        func_type = None
        verb = self.function
        if verb == "GET":
            func_type = 'get'
        elif verb in ["PUT", "DELETE"]:
            func_type = 'put'
        else:
            raise Denied(dict(error=True, reason="disallowed method"))
        res = self.interact_with_db(path, func_type, **kwargs)
        log(json.dumps(res.json()))
        try:
          res.raise_for_status()
        except:
          log("Request Denied")
          raise Denied(dict(error=True, reason=res.json()))
        log("Authorized")
        raise Authorized(dict(ok=True))

    def path(self):
        apath = self.env["REQUEST_URI"].split('/')
        if len(apath) < 4: 
            raise Denied(dict(error=True, reason="malformed request'"))
        return {
          "function" : self.env["REQUEST_METHOD"],
          "db" : apath[1],
          "id" : apath[2],
          "attachment" : apath[3]
        }

def application(env, start_response):
    try:
      handler = Handler(env)
      handler.output_env()
      handler.authorization()
    except (Authorized,Denied) as d:
      start_response(d.msg_type, [ 
            ('Content-Type', 'application/json'),
      ])
      return json.dumps(d.msg)
     
    # Now handle normal requests
    try:
      fn = handler.function
      info = handler.path()
      info["db_esc"] = info["db"].replace("%2F", "/")
      if fn == "GET":
          start_response('200 OK', [
             ('X-Accel-Redirect', '/protected/{db_esc}/{id}/{attachment}'.format(**info)),
             ('Content-Type', 'application/octet-stream'),
             ('Content-Disposition', 'attachment; filename={attachment}'.format(**info)),
          ])
      elif fn == "PUT":
          push_to_path = '{db}/_design/nedm_default/_update/attachment/{id}'.format(**info)
          ret = handler.process_upload("/{save_dir}/{db_esc}/{id}/{attachment}".format(save_dir=_save_dir,**info), push_to_path)
          log("Registered upload")
          start_response(str(ret.status_code), [
            ('Content-Type', 'application/json'),
          ])
          return json.dumps(ret.json())
      elif fn == "DELETE":
          push_to_path = '{db}/_design/nedm_default/_update/attachment/{id}?remove=true'.format(**info)
          ret = handler.process_delete("/{save_dir}/{db_esc}/{id}/{attachment}".format(save_dir=_save_dir,**info), push_to_path)
          log("Deleted")
          start_response(str(ret.status_code), [
            ('Content-Type', 'application/json'),
          ])
          return json.dumps(ret.json())
      else:
          raise Denied(dict(error=True, reason="disallowed method"))
    except:
      import traceback
      log(traceback.format_exc())
      start_response(handler.error_code(), [('Content-Type','application/json')])
      return json.dumps(dict(error=True, reason=traceback.format_exc()))
    finally:
      handler.cleanup()
