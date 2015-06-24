import os
import shutil

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
base_conf = open("/nginx-base.conf.in").read().replace("@DB_NAME@", os.environ["DB_PORT_5984_TCP_ADDR"])
for nm,val in os.environ.items():
    if nm[:len(_env_prefix)] != _env_prefix: continue
    server_name, redirect = val.split('@')
    redirect = base_conf.replace("@REDIRECT_URI@", redirect)
    with open(os.path.join(_nginx_conf, nm + ".conf"), "w") as af:
        af.write(
          _conf_template.format(server_name=server_name,base_conf=redirect)
        )

