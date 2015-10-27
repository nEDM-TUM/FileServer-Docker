---
title: API usage 
description: Description of how to use the HTTP API
layout: basic
---

## HTTP API 

Authenticaton is handled by the file server backend by forwarding requests back
to the CouchDB server and checking for the correct priveleges.  This means that
the authentication should be sent in the cookies 
The file server attachment endpoint is at the URL: 

`/_attachments/[db_name]/[doc_id]/[attachment]`

* `GET` - returns the document assuming the user has read access.  Also can handle `Range` requests.
* `PUT` - puts file (transferred in body of request) at `[attachment]`
associated with document with `[doc_id]`.  Require write access to the CouchDB document.
* `DELETE` - removes associated file, requires write access to the CouchDB document.

For digitizer files (e.g. `.dig` files), there is an additional option that can
be added to downsample the data, e.g.:

`/_attachments/[db_name]/[doc_id]/[attachment].dig/downsample/8`

where `[attachment].dig` will be downsampled by 8.

See the documentation on [pynedm]({{ site.url }}/Python-Slow-Control) for more
information.
