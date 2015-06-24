#!/bin/bash
set -e

if [ "$1" = 'nginx' ]; then
  python /build-conf-files.py
  service supervisor start
  if [ x"$READ_ONLY_FILESERVER" = 'x' ]; then
    rm -rf /database_attachments/_tmp
    mkdir /database_attachments/_tmp
  fi
fi

exec "$@"
