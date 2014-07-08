#!/usr/bin/env python
#

# Search for libraries also under ./lib
import os, sys, logging
sys.path.insert(1, os.path.join(os.path.abspath('.'), 'lib'))

import webapp2, jinja2
from decimal import Decimal
from base64 import b32encode
from cStringIO import StringIO
from jinja2 import Markup
from urllib import urlencode
from urllib import quote as url_quote
from google.appengine.api import memcache

import qrcode
from qrcode.image.svg import SvgPathImage, SvgFragmentImage
from qrcode.image.pil import PilImage

from ckapi import CKRequestor, CKReqReceive, CKObject

from models import MyInvoice, MAX_PAY_TIME

logger = logging.getLogger(__name__)

# path to CK API
JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# API Keys and other unique configuration goes into "settings.py"
try:
    # normally, you should put your settings into settings.py
    from settings import *
except NotImplementedError:
    # if "settings_dev.py" exists, use that instead (so I don't have to commit my keys)
    from settings_dev import *

def get_pubnub_auth():
    # Get the auth details needed for Pubnub (cached)
    d = memcache.get('pubnub')
    if d:
        return d

    d = CK_API.pubnub_enable()
    memcache.add('pubnub', d)

    return d

def get_ck_detail(refnum, cache_ttl=15):
    # Get the info on an CK object, with cache
    rk = 'detail.%s' % refnum
    d = memcache.get(rk)
    if d: return d

    d = CK_API.get_detail(refnum)
    memcache.add(rk, d, time=cache_ttl)

    return d


class MainHandler(webapp2.RequestHandler):
    def get(self):
        #self.response.write('Hello world!')

        template_values = {}
        template = JINJA_ENV.get_template('index.html')
        self.response.write(template.render(template_values))

class InvoiceHandler(webapp2.RequestHandler):
    def get(self, token, example='btc'):
        ctx = CKObject(max_time = MAX_PAY_TIME)
        if token == 'example':
            cct = example.upper()
            ctx.cct = cct
            ctx.payable = Decimal('0.1612')
            ctx.payable_cct = cct
            ctx.amount_cct = 'USD'
            ctx.amount = Decimal('100.00')
            ctx.show_fiat = True
            ctx.label = 'Doggy Dash Crypto Cash'
            ctx.pubkey = 'n1EeygjWd6WSWxMyUx8Y6RBts3Mo8aZr3S'
            ctx.time_left = 10*60
            ctx.is_paid = False
        else:
            # find in DB
            inv = MyInvoice.get_by_token(token)

            if not inv:
                ctx.token = token
                template = JINJA_ENV.get_template('missing.html')
                self.response.write(template.render(ctx))
                return

            ctx.update(inv.to_dict())
            cct = inv.payable_cct
            ctx.label = ctx.label or ''
            ctx.time_left = inv.get_time_left()

            d = get_ck_detail(inv.ck_refnum)
            print "details = %r" % d

            # Has it been paid?? Limitations here:
            # - should handle amounts less that desired total, for wallets that sometimes
            #   round down by a few satoshis.
            # - check # of confirmations are suitable for risk preferences
            #
            ctx.is_paid = d.is_completed or (d.amount_so_far.decimal >= ctx.payable)

            assert ctx.pubkey == d.coin.address
            
        if ctx.show_fiat: 
            ctx.exchange_rates = [
                ('1 %s' % cct, '$612 USD'), 
                ('%s %s' % (ctx.amount, cct), '$612 USD'), 
            ]

        # a small dictionary of values we need to connect to pubnub
        ctx.pubnub_auth = get_pubnub_auth()

        ctx.bitcoin_link = ('bitcoin:%s?' % ctx.pubkey) + urlencode(dict(
                            amount = ctx.amount, message = ctx.label[0:40]))
    
        template = JINJA_ENV.get_template('invoice.html')
        self.response.write(template.render(ctx))

class QRHandler(webapp2.RequestHandler):
    def get(self, nonce, extension):

        # Render a QR into an image.
        qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_H)
        qr.add_data("Hello bitcoin world...")
        
        mime, factory = {
            'svg': ('image/svg+xml', SvgPathImage),
            'png': ('image/png', PilImage),
        }[extension]

        qr_img = qr.make_image(image_factory = factory)

        self.response.content_type = mime
        self.response.content_type_params = {}

        body = StringIO()
        qr_img.save(body)
        self.response.write(body.getvalue())

class TestHandler(webapp2.RequestHandler):
    def get(self, token, test_case):
        # Hack to simulate payment.
        inv = MyInvoice.get_by_token(token)

        if test_case == '0':
            msg = dict(event_code = 'credit_0',
                        activity = 'acccc-acccccc',
                        desc = "Unconfirmed credit", 
                        request = inv.ck_refnum)
            ret = CK_API.pubnub_send(msg)

        else:
            self.error(404)

        self.response.content_type = 'text/plain'
        self.response.write(repr(ret))
        

class MakeHandler(webapp2.RequestHandler):
    def get(self):
        # provide a blank form.
        template = JINJA_ENV.get_template('make.html')
        ctx = CKObject()
        ctx.valid_coins = ACCOUNT_MAP.keys()
        recent = MyInvoice.recent_invoices().fetch(40)
        ctx.recent_invoices = recent

        for inv in recent:
            if inv.paid_at != None:
                inv.text_status = 'PAID'
                continue

            # check if paid.
            try:
                d = get_ck_detail(inv.ck_refnum)
            except:
                logger.error("Failed on %s" % inv.ck_refnum, exc_info=1)
                continue

            inv.details = d
            if d.is_completed or d.amount_so_far.decimal:
                # TODO: should expose total paid so far (for tips and underpayment)
                # and link to transaction numbers displayed at blockr and so on.
                conf = d.events[0].confirmed_at
                if conf != None:
                    inv.paid_at = conf
                    inv.text_status = 'PAID'
                    inv.put_async()
                else:
                    inv.text_status = 'pending'
            else:
                inv.text_status = 'unpaid'

        self.response.write(template.render(ctx))
        

    def post(self):
        # build it and redirect to something.
        # NOTE: setting in app.yaml protects this for admin-only access.

        # NOTE: A real program would have validation here
        amount = Decimal(self.request.get('amount', 0))
        amount_cct = self.request.get('amount_cct', 'BTC')[0:3].upper()
        payable_cct = self.request.get('payable_cct', 'BTC')[0:3].upper()
        label = self.request.get('label', None)
        show_fiat = self.request.get('show_fiat', False)

        n = MyInvoice()
        n.amount_cct = amount_cct
        n.payable_cct = payable_cct

        if amount_cct == payable_cct:
            n.payable = amount
            n.amount = amount
        else:
            # get a spot quote.
            q = CK_API.get('/v1/spot_quote/%s/%s/%s' % (payable_cct, amount_cct, amount))
            n.payable = q.result.decimal.quantize(Decimal('0.0001'))
            n.amount = amount

        n.label = label[0:190] if label else None
        n.show_fiat = bool(show_fiat)

        n.token = b32encode(os.urandom(10))

        # TODO get a pubkey for the request
        acct = ACCOUNT_MAP[payable_cct]
        r = CK_API.put('/v1/new/receive', account = acct,
                            memo = 'See %s' % n.get_url(), amount = n.payable)

        req = r.result
        n.pubkey = req.coin.address
        n.ck_refnum = req.ref_number
        
        # save it.
        key = n.put()

        # bugfix: not seeing the new entry in the list after redirect
        # TODO: this doesn't help! need a fix for this issue
        from google.appengine.ext import ndb
        ndb.get_context().clear_cache()

        # redirect to making page.
        self.redirect('/make')

def inline_svg_qr(contents, boxsize=10):
    # provide SVG inline, which is a SVG image of QR needed!
    qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_H, box_size=boxsize)
    qr.add_data(contents)
    qr_img = qr.make_image(image_factory = SvgPathImage)

    body = StringIO()
    qr_img.save(body)

    return Markup(body.getvalue())

        
# Add some custom filters
JINJA_ENV.filters.update({
    'svg_qr': inline_svg_qr,
    'urlencode': url_quote,       # very poor verison of Jinja 2.7 code, but good enough?
})

# Explicit routing goes here.
#
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/make', MakeHandler),
    ('/invoice/(\w+)', InvoiceHandler),
    ('/test/(\w+)/(\w+)', TestHandler),
    ('/invoice/(example).(\w+)', InvoiceHandler),
    ('/qr/(\w+).(png|svg)', QRHandler),
], debug=True)

# EOF
