#
# All Exceptions for Coinkite API
#
# Full docs at: https://docs.coinkite.com/
# 
# Copyright (C) 2014 Coinkite Inc. (https://coinkite.com) ... See LICENSE.md
#

class CKAPIConnectionError(RuntimeError):
    "A problem with the HTTPS connection to the Coinkite server"
    pass

class CKJSONErrorBase(object):
    "See self.json for error details, as returned by the server"
    def __init__(self, json):
        self.json = json
        for k in json:
            setattr(self, k, json[k])

        msg = ' \n  '.join(filter(None, [json.get(i) for i in ['message', 'help_msg']]))

        super(CKJSONErrorBase, self).__init__(msg)

class CKServerSideError(CKJSONErrorBase, RuntimeError):
    "Any error reported by the server, except 400, 404"

class CKMissingError(CKJSONErrorBase, KeyError):
    "A 404 was reported bythe server"

class CKArgumentError(CKJSONErrorBase, ValueError):
    "Bad request errors from server side, typically due to bad arugments"


# EOF
