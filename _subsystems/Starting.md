---
title: Starting
description: How to start the container 
layout: basic
---

## Starting the docker container 

An example command (to run as a daemon, swap `-it` with `-d`):

{% highlight bash %}
docker run -it -p 5984:5984 -p 80:80\
  -v /volume1/Measurements:/database_attachments\
  -e "NGX_VIRTUAL_SERVER_2=db.nedm1@/nedm_head/_design/nedm_head/_rewrite"\
  -e "NGX_VIRTUAL_SERVER_1=raid.nedm1@"\
  --name nEDM-FileServer --link nEDM-CouchDB:db registry.hub.docker.com/mgmarino/fileserver-docker:latest
{% endhighlight %}

The particular steps are explained in the following:

1. Mount attachments directory (R/W) to `/database_attachments`
1. Pass environment variables to the container to define virtual servers
(multiple may be passed, the must simply have a different `_my_suffix`):

    ```
    -e 'NGX_VIRTUAL_SERVER[_my_suffix]=db.name.org@/path/to/rewrite'
    ```
Note that the path should *never* end with a slash.

1. (optional) Pass environment variables to set readonly status:

    ```
    -e 'READ_ONLY_FILESERVER=yes'
    ```

1. (experimental) Pass environment variables to set CHMOD of written files:

    ```
    -e 'FILE_MODE_FILESERVER=0664'
    ```

1. (optional) Mount supervisor log directory (R/W) to view the output of the file-server backend to `/var/log/supervisor`
1. Link to the nEDM couchdb container, here the `db` name must be kept! (`--link name_of_container:db`)
1. Export port(s) `80` and/or `5984`.

Note, that it is important that no ports are forwarded in the CouchDB container
to the external world.  This is because the nginx container sits in front of
the CouchDB instance and routes the commands to it.

### Disable httpd on Synology Station
Port 80 must be available for the nginx to listen on. In DSM, a httpd service is using it by default.
Then the nEDM-FileServer container cannot be started with the error message
{% highlight bash %}
Error starting userland proxy: listen tcp 0.0.0.0:80: bind: address already in use
{% endhighlight %}
A solution to disable httpd is given [here](http://stackoverflow.com/a/30985335). A DSM-update might restore the default behaviour and it has to be deactivated again.
