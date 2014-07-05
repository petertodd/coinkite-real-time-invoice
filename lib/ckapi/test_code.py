#!/usr/bin/env python
#
# Test code for API. Calls the API remotely. Needs CK_API_KEY and CK_API_SECRET to be already
# defined in the environment. Key must have at least "read" permission.
#
# Requires: "pytest", so:
#
#   pip install pytest
#
# Usage: 
#   cd (into this directory)
#   py.test                             [runs all tests, nice tidy output]
#   py.test -s -k test_balances         [runs just test_balances, shows output]
#
#
import os, sys, time, random
from requestor import CKRequestor
from exc import *
import pytest

@pytest.fixture(scope="module")
def req():
    return CKRequestor(host='http://lh:5001')
    #return CKRequestor()

def test_basics(req):
    print req.get('/public/endpoints')
    print req.get('/v1/my/self')

def test_detail(req):
    # random object
    refnum = req.get('/v1/my/self').api_key.ref_number
    
    print req.get_detail(refnum)

    with pytest.raises(CKMissingError) as ei:
        print req.get_detail(refnum[:-6] + '000000')
    assert ei.value.json.status == 404

def test_paging(req):
    rv = req.get('/v1/list/activity', limit=1)
    assert len(rv.results) == 1
    assert rv.paging.total_count == req.get_list('activity', just_count=True)

def test_balances(req):
    accts = req.get_accounts()
    assert len(accts) > 0
    for a in accts:
        print repr(req.get_balance(a))

def test_receipt(req):
    k = [{'cmd': 'huge', 'msg': 'Hello World!'},
         {'cmd': 'qrcode', 'data': 'https://google.com?q=cats'},
         {'cmd': 'tiny', 'msg': 'This is a little message'}]

    rv = req.terminal_print(k, preview_only=True).printed
    print rv.text_apx
    assert 'http' in rv.web_apx_url

    #import webbrowser
    #webbrowser.open(rv.web_apx_url)

# TODO: need a "test_put" that doesn't change anything?

def test_pubnub(req):
    perms = req.get('/v1/my/self').api_key.permissions

    if 'events' not in perms:
        pytest.skip("API Key doesnt have 'events' permission")

    pn, chan = req.pubnub_start()

    readback = {}

    def rx_callback(_msg, _chan):
        print "MSG on %s: %r" % (_chan, _msg)
        readback.update(_msg)
        raise SystemExit

    pn.subscribe(chan, rx_callback)
    time.sleep(2.0)         # need at least 1 sec here
    
    msg = dict(testing=1234, rnd = random.randint(0,100000))
    req.pubnub_send(msg)

    while not readback:
        time.sleep(0.250)

    assert readback == msg

def test_print_help(req):
    lst = req.terminal_print_help()

    print '\n'.join(lst)
        
# EOF
