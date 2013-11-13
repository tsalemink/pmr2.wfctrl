from urlparse import urlsplit, urlunsplit

def set_url_cred(url, username, password, _protocols=('http', 'https')):
    urlparts = list(urlsplit(url))
    if urlparts[0] not in _protocols:
        return url

    if '@' in urlparts[1]:
        urlparts[1] = urlparts[1].split('@')[-1]

    urlparts[1] = '%s:%s@%s' % (username, password, urlparts[1])

    return urlunsplit(urlparts)
