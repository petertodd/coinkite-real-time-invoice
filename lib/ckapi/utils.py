#
# Coinkite API: Make requests of the API easily.
#
# Full docs at: https://docs.coinkite.com/
# 
# Copyright (C) 2014 Coinkite Inc. (https://coinkite.com) ... See LICENSE.md
# 
#
import logging
from objs import make_db_object
from decimal import Decimal

try:
    import simplejson

    json_encoder = simplejson.JSONEncoder(use_decimal=True, for_json=True)
    json_decoder = simplejson.JSONDecoder(object_hook=make_db_object, parse_float=Decimal)
except ImportError:
    # Sorry, but we cannot make do with the stock json library, because
    # we need Decimal to be encoded corrected both for read and write
    #raise RuntimeError("Coinkite API requires the 'simplejson' package")
    import json
    json_decoder = json.JSONDecoder(object_hook=make_db_object, parse_float=Decimal)

    # Take from http://stackoverflow.com/questions/1960516
    class DecimalEncoder(json.JSONEncoder):
        def _iterencode(self, o, markers=None):
            if isinstance(o, Decimal):
                return (str(o) for o in [o])
            return super(DecimalEncoder, self)._iterencode(o, markers)

        def default(self, o):
            if hasattr(o, 'for_json'):
                return o.for_json()
            return JSONEncoder.default(self, o)

    json_encoder = DecimalEncoder()


# EOF
