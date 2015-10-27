---
title: Python backend 
description: Description of backend
layout: basic
---

## Python backend

The python backend is defined in `handle_req.py` and requests are passed from
nginx via [uwsgi](http://uwsgi-docs.readthedocs.org/en/latest/WSGIquickstart.html).

### Authorization

Cookies and http authorization are forward directly to the CouchDB server.  For
`GET` and `HEAD` requests, the backend checks to see if it can perform the
command on the associated document and returns the appropriate error code if
not.  For `PUT` and `DELETE` requests, the backend relies on the fact that an
update function is available on the CouchDB database at the endpoint: 

`[db]/_design/nedm_default/_update/attachment/[doc_id]`

This function is part of the [nEDM-Interface]({{ site.url }}/nEDM-Interface)
and looks like:

{% highlight javascript %}
function(doc, req) {
    if (!doc) {
        return [null, JSON.stringify({msg : 'No document', error : true})];
    }
    if (!req.body) {
        return [null, JSON.stringify({msg : 'No request', error : true})];
    }
    var _ref = JSON.parse(req.body);
    var k;
    if (req.query.remove) {
      if (!doc.external_docs) {
        return [null, JSON.stringify({msg : 'No attachments', error : true})];
      }
      for (k in _ref) {
        if (doc.external_docs[k]) {
          delete doc.external_docs[k];
        }
      }
    } else {
      if (!doc.external_docs) {
        doc.external_docs = {};
      }
      for (k in _ref) {
        doc.external_docs[k] = _ref[k];
      }
    }
    return [doc, JSON.stringify({attachments : doc.external_docs, id : doc._id, ok : true})];
}
{% endhighlight %}

Note that on a change (e.g. `PUT` or `DELETE`) a field is added or removed from
the field `external_docs` on the document.  The resulting document will be run
through the [appropriate validate
functions](http://docs.couchdb.org/en/1.6.1/couchapp/ddocs.html#validate-document-update-functions),
which will check to see if the change is allowed.

### Adding and Deleting 

When a request comes in to add or delete a file, the process looks like the following:

On `PUT`:
{% highlight bash %}
  Add entry to doc.external_docs
             |
             v
  Proceed with upload
             |
             v
  Populate entry in doc.external_docs
{% endhighlight %} 

where 'populate entry' adds the fields:
{% highlight javascript %}
  "name_of_file":  {
            "ondiskname" : "name_of_file",
            "time" : {
              "atime" : /*access time*/, 
              "ctime" : /*create time*/,
              "crtime": /*create time*/, 
              "mtime" : /*modify time*/
            },
            "size" : //size in bytes 
          }
{% endhighlight %}
to `doc.external_docs`.

A delete is similar, except the fields are removed.  If it fails at any point,
the appropriate HTTP code is returned.

### Reading

If normal files are requested (e.g. without downsample requests), then these
are served directly by nginx using the `X-Accel-Redirect` header (see e.g.
[here](https://www.nginx.com/resources/wiki/start/topics/examples/x-accel/)).
This is generally the most efficient way to serve files statically from disk. 
Requests with `downsample` are processed by the python backend and served from
it (not directly from nginx).

### Notes

* If a document is deleted, then all associated attachments are also deleted
