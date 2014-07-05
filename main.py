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

from ckapi import CKRequestor, CKReqReceive, CKObject

# path to CK API
JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class MainHandler(webapp2.RequestHandler):
    def get(self):
        #self.response.write('Hello world!')

        template_values = {}
        template = JINJA_ENV.get_template('index.html')
        self.response.write(template.render(template_values))

class InvoiceHandler(webapp2.RequestHandler):
    def get(self, token, example='btc'):
        cct = example.upper()
        ctx = CKObject(req = CKReqReceive(), amount = Decimal('1.12345678'), cct = cct)
        ctx.exchange_rates = [
            ('1 %s' % cct, '$612 USD'), 
            ('%s %s' % (ctx.amount, cct), '$612 USD'), 
        ]
        ctx.label = 'Doggy Dash Crypto Cash'
        ctx.pubkey = '1blahxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        ctx.bitcoin_link = ('bitcoin:%s?' % ctx.pubkey) + urlencode(dict(
                            amount = ctx.amount, message = ctx.label))
    
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
})

# Explicit routing goes here.
#
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/invoice/(\w+)', InvoiceHandler),
    ('/invoice/(example).(\w+)', InvoiceHandler),
    ('/qr/(\w+).(png|svg)', QRHandler),
], debug=True)

# EOF
