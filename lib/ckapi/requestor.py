#
# Coinkite API: Make requests of the API easily.
#
# Full docs at: https://docs.coinkite.com/
# 
# Copyright (C) 2014 Coinkite Inc. (https://coinkite.com) ... See LICENSE.md
#
import os, sys, datetime, time, logging, itertools, functools
from decimal import Decimal
from http_client import new_default_http_client
from utils import json_decoder, json_encoder
from hmac import HMAC
from hashlib import sha256
from urlparse import urljoin, urlparse
from urllib import urlencode
from exc import CKArgumentError, CKServerSideError, CKMissingError

logger = logging.getLogger('ckapi')

class CKRequestor(object):
    "Use this object to get and put resources to api.coinkite.com"

    def __init__(self, api_key=None, api_secret=None, host='https://api.coinkite.com', client=None):
        "Provide API Key and secret, or use values from Environment"

        self.api_key = api_key or os.environ.get('CK_API_KEY', None)
        self.api_secret = api_secret or os.environ.get('CK_API_SECRET', None)
        self.host = host

        self.client = client or new_default_http_client(verify_ssl_certs=True)

    def request(self, method, endpt, **kws):
        '''
        Low level method to perform API request: provide HTTP method and endpoint

        Optional args:
            _data = JSON document to be PUT (instead of **kws as dict)
            _headers = Extra headers to put on request (not useful?)

        NOTE: Any other arguments will end up as arguments to the API call itself.

        '''
        assert method in ('GET', 'PUT'), method

        # Compose the abs URL required
        url = urljoin(self.host, endpt)
        endpt = urlparse(url).path

        hdrs = {}

        if '_headers' in kws:
            # User may supply some headers? Probably not useful
            hdrs.update(kws.pop('_headers'))

        data = None
        if kws:
            assert '?' not in url, "Please don't mix keyword args and query string in URL"

            if method == 'GET':
                # encode as query args.
                url += '?' + urlencode(kws)
            else:
                # submit a JSON document, based on either the keyword args (made into a dict)
                # or whatever object is in "_data" argument
                data = json_encoder.encode(kws.get('_data', kws))
                hdrs['Content-Type'] = 'application/json'

        logger.info('%s %s' % (method, url))

        # we will retry rate-limited responses, so be prepared to retry here.
        while 1:
            if not endpt.startswith('/public'):
                # Almost always add AUTH headers
                hdrs.update(self._auth_headers(endpt))

            body, status = self.client.request(method, url, hdrs, data)
        
            # decode JSON
            body = json_decoder.decode(body)

            if status == 429 and 'wait_time' in body:
                # delay and retry
                logging.info("Rate limited: waiting %s seconds" % body.wait_time)
                time.sleep(body.wait_time)
            else:
                break

        if status == 400:
            raise CKArgumentError(body)
        if status == 404:
            raise CKMissingError(body)
        elif status != 200:
            raise CKServerSideError(body)

        return body

    def _make_signature(self, endpoint, force_ts=None):
        #
        # Pick a timestamp and perform the signature required.
        #
        assert endpoint[0] == '/' and 'api.coinkite.com' not in endpoint, \
                    "Expecting abs url, got: %s" % endpoint
        assert '?' not in endpoint, endpoint
         
        ts = force_ts or datetime.datetime.utcnow().isoformat()
        data = endpoint + "|" + ts
        hm = HMAC(self.api_secret, msg=data, digestmod=sha256)

        return hm.hexdigest(), ts

    def _auth_headers(self, endpoint, force_ts=None):
        #
        # Make the authorization headers that are needed to access indicated endpoint
        #

        if not self.api_key:
            raise RuntimeError("API Key for Coinkite is required. "
                                "We recommend setting CK_API_KEY in environment")
        if not self.api_secret:
            raise RuntimeError("API Secret for Coinkite is required. "
                        "We recommend setting CK_API_SECRET in environment!")

        signature, timestamp = self._make_signature(endpoint, force_ts=force_ts)

        return {
            'X-CK-Key': self.api_key,
            'X-CK-Timestamp': timestamp,
            'X-CK-Sign': signature,
        }

    def get(self, endpt, **kws):
        "Perform a GET on indicated resource (endpoint) with optional arguments"
        return self.request('GET', endpt, **kws)

    def put(self, endpt, **kws):
        "Perform a PUT on indicated resource (endpoint) with optional arguments"
        return self.request('PUT', endpt, **kws)

    def get_iter(self, endpoint, offset=0, limit=None, batch_size=25, safety_limit=500, **kws):
        '''Return a generator that will iterate over all results, regardless of how many.
    
           This should work on any endpoint that has a offset/limit argument and
           returns paging data. Can provide offset or limit as well.
        '''

        def doit(offset, limit, batch_size):
            args = dict(kws)

            while 1:
                # Fetch as many results as we can at this offset
                if limit and limit < batch_size:
                    batch_size = limit

                rv = self.get(endpoint, offset=offset, limit=batch_size, **args)

                # look at paging situation
                here = rv.paging.count_here
                total = rv.paging.total_count

                # rescue drowning programs.
                if total > safety_limit:
                    raise Exception("Too many results (%d); consider another approach" % total)

                # are we done?
                if not here:
                    return

                # give up the results for the page of values
                for i in rv.results:
                    yield i

                # on to next page of data
                offset += here
                if limit != None:
                    limit -= here
                    if limit <= 0:
                        return

        return itertools.chain(doit(offset, limit, batch_size))

    #
    # Simple wrappers / convenience functions.
    #

    def check_myself(self):
        # ... before you wreck myself?
        return r.get('/v1/my/self')

    def get_detail(self, refnum):
        "Get detailed-view of any CK object by reference number"
        return self.get('/v1/detail/' + refnum).detail

    def get_accounts(self):
        "Get a list of accounts, doesn't include balances"
        return self.get('/v1/my/accounts').results

    def get_balance(self, account):
        "Get account details, including balance, by account name, number or refnum"
        return self.get('/v1/account/%s' % getattr(account, 'ref_number', account)).account

    def get_list(self, what, account=None, just_count=False, **kws):
        '''
        Get a list of objects, using /v1/list/WHAT endpoints, where WHAT is:

                activity
                credits
                debits
                events
                notifications
                receives
                requests
                sends
                transfers
                unauth_sends

        This is a generator function, so keep that in mind.
        '''
        ep = '/v1/list/%s' % what

        if account != None:
            kws['account'] = account

        if just_count:
            # return total number of records
            return self.get(ep, limit=0, **kws).paging.total_count

        return self.get_iter(ep, **kws)

    def pubnub_send(self, msg):
        "Send a test message via Coinkite > Pubnub > back to you"
        return self.put('/v1/pubnub/send', **msg).enabled_keys

    def pubnub_start(self):
        '''
        Create a Pubnub object and return it, ready to be used, and the name
        of the channel you need to subscribe to.
        '''
        v = self.put('/v1/pubnub/enable')

        try:
            from Pubnub import Pubnub
        except ImportError:
            raise RuntimeError("You need Pubnub's python module installed (>= 3.5.2), "
                               "see: https://github.com/pubnub/python")

        pn = Pubnub(None, v.subscribe_key, auth_key=v.auth_key, ssl_on=True)

        return pn, v.channel

    def terminal_print(self, receipt_doc, preview_only=False, terminal='any'):
        "Send a document to be printed"
        ep = '/v1/terminal/%s/print' % ('preview' if preview_only else terminal)
        return self.put(ep, _data = receipt_doc)

    def terminal_print_help(self):
        "return a helpful list of instructions (commands) for receipt printing"
        return self.get('/v1/terminal/preview/print').command_spec

# EOF
