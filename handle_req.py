import cloudant
import json
import requests
import logging
import os
import subprocess
logging.basicConfig(filename='/var/log/supervisor/wsgi.log',level=logging.DEBUG)

_nginx_prefix = "protected"
_save_dir = "/database_attachments"
_file_mode = @FILEMODE@

class LocalException(Exception):
    def __init__(self, msg=None):
        self.msg = ""
        if msg is not None:
            self.msg = json.dumps(msg)

class Authorized(LocalException):
    msg_type = "200 Ok"

class Denied(LocalException):
    msg_type = "403 Forbidden"

class NotFound(LocalException):
    msg_type = "404 Not Found"

class BadRequest(LocalException):
    msg_type = "400 Bad Request"

def log(msg):
    logging.info(msg)

def replace_special_characters(file_name):
    tmp = file_name
    for re_, repl in [
      (":", "-")
      ]: tmp = tmp.replace(re_, repl)
    return tmp

def down_sample_file(start_resp, file_name, flags, header_only):
    """
    File structure is:
       bytes 0..3: length of json header N (excluding header word)
       bytes 4..4+N: json header (ASCII data)
       bytes 4+N+1..EOF: binary data of channels

    The binary data format depends on what's in the json header:
      header["channel_list"] ---> ordered list of channels
      header["byte_depth"]    ---> size of binary word
      header["bit_shift"]    ---> amount to shift right

	Every channel is listed one after another for each time point (fully
    interlaced)

    """
    import urllib
    import struct
    import numpy
    file_name = urllib.url2pathname(file_name)
    if not os.path.exists(file_name):
        raise NotFound()

    ds = 2
    try:
      assert(flags[0] == "downsample")
      ds = int(flags[1])
    except:
      raise BadRequest({"error" : True, "reason" : "url flags not correct"})

    base, ext = os.path.splitext(os.path.basename(file_name))
    new_file_name = base + "_downsample" + ext

    if ds < 2:
      raise BadRequest({"error" : True, "reason" : "Downsample must be greater than 1"})

    def send_header(fn, length):
       start_resp("200 OK", [
         ("Content-Type" ,"application/octet-stream"),
         ("Content-Disposition", "attachment; filename=\"{}\"".format(fn)),
         ("Content-Length", "{} ".format(length))
       ])

    with open(file_name, "rb") as o:
        header_length = struct.unpack("<L", o.read(4))[0]
        data_length = os.path.getsize(file_name) - header_length

        o.seek(4)
        hdr = json.loads(o.read(header_length))
        try:
            bit_depth = hdr["bit_depth"]
        except:
            bit_depth = hdr["byte_depth"]
        bit_shift = hdr["bit_shift"]
        dt = None
        if bit_depth == 2: dt = numpy.int16
        elif bit_depth ==4: dt = numpy.int32
        else: raise Exception("unknown bit_depth")

        # Reads from position 4 + header_length
        o.seek(4+header_length)

        # Do a right shift if necessary
        cl = hdr["channel_list"]
        total_ch = len(cl)
        hdr["downsample"] = ds
        hdr["bit_shift"] = 0

        # output header
        hdr_as_str = json.dumps(hdr)
        chunk_size = total_ch*bit_depth*ds
        expected_length = 4 + len(hdr_as_str) + (data_length/chunk_size)*total_ch*bit_depth

        send_header(new_file_name, expected_length)
        if header_only:
            return
        yield numpy.array([len(hdr_as_str)], dtype=numpy.uint32).tostring()
        yield hdr_as_str
        # Read file in chunks

        while True:
            dat = o.read(10*1024*chunk_size)
            if not dat: break
            leng_read = len(dat)
            if leng_read % chunk_size != 0:
              new_length = leng_read / chunk_size
              dat = dat[:new_length*chunk_size]
            new_arr = numpy.fromstring(dat, dtype=dt)
            if bit_shift != 0:
                new_arr = numpy.right_shift(new_arr, bit_shift)
            new_arr = new_arr.reshape(-1, ds, total_ch)
            yield new_arr.mean(axis=1).astype(dt).tostring()

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
        if fn in ["GET", "HEAD"]:
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
        os.chmod(save_path, _file_mode)
        #md5 = subprocess.check_output(["md5sum", save_path]).split(' ')[0]
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
            #"md5" : md5,
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
        all_cookies = self.env.get("HTTP_COOKIE", "").split("; ")
        ret_dict = dict([c.split('=') for c in all_cookies if c.find("=") != -1])
        acct = cloudant.Account("http://db:5984")
        headers = {}
        if "HTTP_AUTHORIZATION" in self.env:
            headers["Authorization"] = self.env["HTTP_AUTHORIZATION"]
        return getattr(acct, verb)(path, cookies=ret_dict, headers=headers,**kwargs)

    def verify_user(self, path, **kwargs):
        func_type = None
        verb = self.function
        if verb in ["GET", "HEAD"]:
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
        apath = [p for p in self.env["REQUEST_URI"].split('/') if p != '']
        if len(apath) < 4:
            raise Denied(dict(error=True, reason="malformed request'"))
        return {
          "function" : self.env["REQUEST_METHOD"],
          "db" : apath[1],
          "id" : apath[2],
          "attachment" : replace_special_characters(apath[3]),
          "flags" : apath[4:]
        }


def application(env, start_response):
    try:
      handler = Handler(env)
      #handler.output_env()
      handler.authorization()
    except (Authorized,Denied) as d:
      start_response(d.msg_type, [
            ('Content-Type', 'application/json'),
      ])
      return json.dumps(d.msg)
    except:
      import traceback
      log(traceback.format_exc())

    # Now handle normal requests
    try:
      fn = handler.function
      info = handler.path()
      info["db_esc"] = info["db"].replace("%2F", "/")
      if fn in ["GET", "HEAD"]:
          base, ext = os.path.splitext(info["attachment"])
          if len(info["flags"]) > 0 and ext == ".dig":
              try:
                 return down_sample_file(start_response,
                  "{save_dir}/{db_esc}/{id}/{attachment}".format(save_dir=_save_dir, **info),
                  info["flags"], fn == "HEAD")
              except LocalException as e:
                start_response(e.msg_type, [])
          else:
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
