nginx-fileserver
================

Docker for file servers to be used in conjuncation with CouchDB in the nEDM experiment.

## Information

This docker is based off of nginx/latest and includes a reverse proxy in front
of the nEDM CouchDB server.

Most requests are simply forwarded to the CouchDB backend and the nginx server
listens on both the 80 and 5984 ports (serving up the same content on both).

The main functionality of this server is also to provide an additional
file-server which is exposed on the `_attachments` URI path.  This allows
uploading 'attachments' associated with documents in the DB, but storing them
externally.  This is particularly useful when storing large files which do not
perform well stored directly in a CouchDB database.

Authenticaton is handled by the file server backend by forwarding requests back
to the CouchDB server and checking for the correct priveleges.  The file server
supports the following syntax:

`/_attachments/db_name/doc_id/attachment`

and the HTTP verbs: `GET, PUT, DELETE`

For `GET`, the user requires read access to the CouchDB document.
For `PUT and DELETE`, the user requires write access to the CouchDB document.

docker run -it -p 80:80 -p 15984:5984 -v ~/tmp/uwsgi:/var/log/supervisor -v  --link db:db webapp1
### Setup options

1. Mount attachments directory (R/W) to `/database_attachments`
1. (Optional) Mount supervisor log directory (R/W) to view the output of the file-server backend to `/var/log/supervisor`
1. Link to the nEDM couchdb container (`--line name_of_container:db`)
1. Export port(s) 80 and/or 5984

Note, that it is important that no ports are forwarded in the CouchDB container
to the external world.  This is because the nginx container sits in front of
the CouchDB instance.

