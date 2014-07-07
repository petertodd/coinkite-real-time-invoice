#!/usr/bin/env python
#

# Search for libraries also under ./lib
import os, sys
sys.path.insert(1, os.path.join(os.path.abspath('.'), 'lib'))

import webapp2, jinja2
from decimal import Decimal
import qrcode
from cStringIO import StringIO
from jinja2 import Markup

from qrcode.image.svg import SvgPathImage, SvgFragmentImage
from qrcode.image.pil import PilImage
from urllib import urlencode
from urllib import quote as url_quote
from base64 import b32encode

from ckapi import CKRequestor, CKReqReceive, CKObject

from models import MyInvoice, MAX_PAY_TIME

# path to CK API
JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# setup for access to Coinkite API
# TODO: add cct => account number map, and isolate into a config file.
CK_API = CKRequestor(
            'K3103c4b1-dd9db888-fb813e6144cb48b5',
            'S607d57a8-f5405072-4959f4a92c982fd5')


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
            ctx.payable = Decimal('1.12345678')
            ctx.payable_cct = cct
            ctx.amount_cct = 'USD'
            ctx.amount = Decimal('100.00')
            ctx.show_fiat = True
            ctx.label = 'Doggy Dash Crypto Cash'
            ctx.pubkey = 'n1EeygjWd6WSWxMyUx8Y6RBts3Mo8aZr3S'
            ctx.time_left = 10*60
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
            
        if ctx.show_fiat: 
            ctx.exchange_rates = [
                ('1 %s' % cct, '$612 USD'), 
                ('%s %s' % (ctx.amount, cct), '$612 USD'), 
            ]

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

class MakeHandler(webapp2.RequestHandler):
    def get(self):
        # provide a blank form.
        template = JINJA_ENV.get_template('make.html')
        ctx = CKObject()
        ctx.recent_invoices = MyInvoice.recent_invoices().fetch(40)

        self.response.write(template.render(ctx))
        

    def post(self):
        # build it and redirect to something.

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
        
        # save it.
        key = n.put()

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
    ('/invoice/(example).(\w+)', InvoiceHandler),
    ('/qr/(\w+).(png|svg)', QRHandler),
], debug=True)

# EOF
