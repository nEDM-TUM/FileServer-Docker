import os
import shutil


_attachments_header = """
    limit_except PUT GET DELETE  { deny all; }
    client_body_buffer_size    10M;
    client_body_temp_path      /database_attachments/_tmp/;
    client_body_in_file_only   on;

    uwsgi_param X-FILE $request_body_file;
"""

if "READ_ONLY_FILESERVER" in os.environ:
    _attachments_header = """
    limit_except HEAD GET { deny all; }
"""


_base_conf = "/etc/nginx/nginx-base.conf"
_nginx_conf = "/etc/nginx/conf.d"
_env_prefix = "NGX_VIRTUAL_SERVER"
_conf_template = """
server {{
  server_name {server_name};
  {base_conf}
}}
"""

# Clean up
shutil.rmtree(_nginx_conf, ignore_errors=True)

os.makedirs(_nginx_conf)

# Grab the base-conf file
base_conf = open("/nginx-base.conf.in").read()
auth_conf = open("/nginx-auth.conf.in").read()
for re_, repl in [
    ("@DB_NAME@", os.environ["DB_PORT_5984_TCP_ADDR"]),
    ("@ATTACHMENTS_HEADER@", _attachments_header),
    ]:
    base_conf = base_conf.replace(re_, repl)
    auth_conf = auth_conf.replace(re_, repl)

def get_hash_key(priv_key, user_name):
    import hmac
    import hashlib
    return hmac.new(priv_key, user_name,
      hashlib.sha1).hexdigest()

try:
    priveleged = os.environ["DB_ENV_PRIVATE_KEY"]
    add_information = """
    proxy_set_header X-Auth-CouchDB-UserName admin;
    proxy_set_header X-Auth-CouchDB-Roles _admin,;
    proxy_set_header X-Auth-CouchDB-Token {};
""".format(get_hash_key(priveleged, "admin"))
    auth_conf = auth_conf.replace("@PRIVELEGED_INFORMATION@", add_information)
except:
    import traceback; traceback.print_exc()
    print("Error setting up auth file")
    auth_conf = None

for nm,val in os.environ.items():
    if nm[:len(_env_prefix)] != _env_prefix: continue
    server_name, redirect = val.split('@')
    red_1 = base_conf.replace("@REDIRECT_URI@", redirect)
    with open(os.path.join(_nginx_conf, nm + ".conf"), "w") as af:
        af.write(
          _conf_template.format(server_name=server_name,base_conf=red_1)
        )
    if auth_conf is not None:
        red_1 = auth_conf.replace("@REDIRECT_URI@", redirect)
        with open(os.path.join(_nginx_conf, nm + "-auth.conf"), "w") as af:
            af.write(
              _conf_template.format(server_name=server_name,base_conf=red_1)
            )



_filemode = str(os.environ.get("FILE_MODE_FILESERVER", 0444))

_pyscript = "/home/uwsgi/handle_req.py"
new_file = open(_pyscript).read()
for re_, repl in [
    ("@FILEMODE@", _filemode),
    ]:
  new_file = new_file.replace(re_, repl)

open(_pyscript, "w").write(new_file)

