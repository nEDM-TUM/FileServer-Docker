---
title: File Server 
layout: basic
---

## File server docker container 

The docker container encapsulates a [nginx](http://nginx.org/) reverse proxy as well as a python
backend that serves files associated with documents in a CouchDB database (also
run in a docker container, see [here]({{ site.url }}/CouchDB-Docker).

This docker is based off of nginx/latest and includes a reverse proxy in front
of the nEDM CouchDB server.

Most requests are simply forwarded to the CouchDB backend and the nginx server
listens on both the 80 and 5984 ports (serving up the same content on both).

### Available pages
   {% for post in site.subsystems %}
* [{{ post.title }}]({{ site.baseurl }}{{ post.url }}) - {{ post.description }}
   {% endfor %}
