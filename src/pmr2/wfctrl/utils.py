import sys

if sys.version_info > (3, 0): # pragma: no cover
    from urllib.parse import urlsplit, urlunsplit
else: # pragma: no cover
    from urlparse import urlsplit, urlunsplit

def set_url_cred(url, username=None, password=None,
        _protocols=('http', 'https')):
    urlparts = list(urlsplit(url))
    if urlparts[0] not in _protocols:
        return url

    if '@' in urlparts[1]:
        urlparts[1] = urlparts[1].split('@')[-1]

    if username is None or password is None:
        return urlunsplit(urlparts)

    urlparts[1] = '%s:%s@%s' % (username, password, urlparts[1])

    return urlunsplit(urlparts)
