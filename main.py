#!/usr/bin/env python
#
#
import os, sys, webapp2

import jinja2
import webapp2

# path to CK API
sys.path.insert(1, os.path.join(os.path.abspath('.'), 'ckapi/ckapi'))

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

app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
