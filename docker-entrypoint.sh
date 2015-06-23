#!/bin/bash
set -e

if [ "$1" = 'nginx' ]; then
  python /build-conf-files.py
  service supervisor start
  rm -rf /database_attachments/_tmp
  mkdir /database_attachments/_tmp
fi

exec "$@"
