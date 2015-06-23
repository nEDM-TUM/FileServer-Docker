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

An example command:

```sh
docker run -it -p 80:80 -p 5984:5984 -v ~/tmp/uwsgi:/var/log/supervisor --link db:db webapp1
```

### Setup options

1. Mount attachments directory (R/W) to `/database_attachments`
1. Pass environment variables to the container to define virtual servers
(multiple may be passed, the must simply have a different `_my_suffix`):

    ```bash
    -e 'NGX_VIRTUAL_SERVER[_my_suffix]=db.name.org@/path/to/rewrite'
    ```

1. (Optional) Mount supervisor log directory (R/W) to view the output of the file-server backend to `/var/log/supervisor`
1. Link to the nEDM couchdb container (`--line name_of_container:db`)
1. Export port(s) 80 and/or 5984

Note, that it is important that no ports are forwarded in the CouchDB container
to the external world.  This is because the nginx container sits in front of
the CouchDB instance.


## API use examples

The following are some examples as to how one can use the API.

### Upload

Using `pycurl` and `cloudant` (unfortunately, requests doesn't handle `100
Expect: continue` at all).

```python
import pycurl
from StringIO import StringIO
import json
from clint.textui.progress import Bar as ProgressBar

def upload_file_with_curl(file_name, post_to_path, cookies=None):
    """
    file_name : full path to file
    post_to_path : of the form "server/{db}/{doc_id}/{attachment_name}
    cookies : Any cookies (as string) to send along with the request
    """
    total_size = os.path.getsize(file_name)
    bar = ProgressBar(expected_size=total_size, filled_char='=')

    class FileReader:
        def __init__(self, fp):
            self.fp = fp
            self.total_read = 0
        def read_callback(self, size):
            x = self.fp.read(size)
            if x is not None:
                self.total_read += len(x)
                bar.show(self.total_read)
            return x

    c = pycurl.Curl()
    storage = StringIO()
    c.setopt(pycurl.URL, post_to_path)
    c.setopt(pycurl.PUT, 1)
    c.setopt(pycurl.READFUNCTION, FileReader(open(file_name, 'rb')).read_callback)
    c.setopt(pycurl.INFILESIZE, total_size)
    c.setopt(c.WRITEFUNCTION, storage.write)
    if cookies is not None:
        print "setting, ", cookies
        c.setopt(c.COOKIE, cookies)
    c.perform()
    c.close()
    content = storage.getvalue()
    try:
        return json.loads(content)
    except:
        return content

# To login, we use cloudant
_server = "http://127.0.0.1"
acct = cloudant.Account(_server)
acct.login(un, password) # give credentials
cookies = '; '.join(['='.join(x) for x in acct._session.cookies.items()])
submit = {
  "db" : "db_name",
  "id" : "doc_id",
  "att_name" : os.path.basename(file_name)
}
o = upload_file_with_curl(file_name, _server + '/_attachments/{db}/{id}/{att_name}'.format(**submit), cookies)

# On success, it should return a json object with information of all
# attachments currently associated with this document
print json.dumps(o, indent=4)
```

# Download

This is notable simpler, and this time we may use `requests`:

```python
...
acct = cloudant.Account(_server)
...
def download_file(file_name, get_from_path):
    r = acct.get(get_from_path, stream=True)
    total_size = int(r.headers['content-length'])
    bar = ProgressBar(expected_size=total_size, filled_char='=')
    with open(file_name, 'wb') as f:
        total = 0
        for chunk in r.iter_content(chunk_size=100*1024):
            if chunk: # filter out keep-alive new chunks
                total += len(chunk)
                bar.show(total)
                f.write(chunk)
                f.flush()

download_file(file_name, _server + '/_attachments/{db}/{id}/{att_name}'.format(**submit))
```

# Delete

```python
...
acct = cloudant.Account(_server)
...
o = acct.delete(_server + '/_attachments/{db}/{id}/{att_name}'.format(**submit)).json()
print json.dumps(o, indent=4)
```
