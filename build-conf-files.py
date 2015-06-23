import os
import shutil

_base_conf = "/etc/nginx/nginx-base.conf"
_nginx_conf = "/etc/nginx/conf.d"
_env_prefix = "NGX_VIRTUAL_SERVER"
_conf_template = """
server {{
  server_name {server_name};
  {redirect_uri}
  include {base_conf};
}}
"""

# Clean up
shutil.rmtree(_nginx_conf, ignore_errors=True)

os.makedirs(_nginx_conf)
for nm,val in os.environ.items():
    if nm[:len(_env_prefix)] != _env_prefix: continue
    server_name, redirect = val.split('@')
    test = "set $redirect_uri {redirect};".format(redirect=redirect)
    if redirect == "" or redirect == "/": test = ""
    with open(os.path.join(_nginx_conf, nm + ".conf"), "w") as af:
        af.write(
          _conf_template.format(server_name=server_name,redirect_uri=test,base_conf=_base_conf)
        )

# Write the nginx-base.conf file
af = open("/nginx-base.conf.in").read()
open(_base_conf, "w").write(af.replace("@DB_NAME@", os.environ["DB_PORT_5984_TCP_ADDR"]))
