---
title: nginx details 
description: Information about nginx and associated settings 
layout: basic
---

## nginx 

The configuration of nginx in the docker container is generally very simple and
only adds the endpoints `/_attachments` and `/_delete`.  All other requests are
forwarded directly to the CouchDB server.  `DELETE` requested are intercepted
and rewritten to use the `/_delete` endpoint.  This ensures that, if a document
is deleted, the associated attachments are also deleted.

### Privileged access

A _privileged_ server is also setup to allow admin access to the CouchDB
server without authentication.  This server listens on container port `5983`,
but this is _not_ exported publicly.  This can only be used by other containers
which link explicitly to the File-Server container, e.g. the [munin
container]({{ site.url }}/Munin-Docker), where those programs may have a need
for administrative access.

### Proxying requests to CouchDB 

In principle, it would be possible to limit the requests being forwarded to the
CouchDB server to a subset of the CouchDB endpoints.  However, at least at the
time of writing, this did not seem like an appropriate step to take.

