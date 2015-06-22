#!/bin/bash
set -e

if [ "$1" = 'nginx' ]; then
  sed -e "s/@DB_NAME@/$DB_PORT_5984_TCP_ADDR/" /nginx.conf.in > /etc/nginx/nginx.conf
  service supervisor start
  rm -rf /database_attachments/_tmp
  mkdir /database_attachments/_tmp
fi

exec "$@"
