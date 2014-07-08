#
# Database Models
#
import datetime
from google.appengine.ext import ndb

# Max time, in seconds, for customer to pay the invoice.
MAX_PAY_TIME = 16*60

def NOW():
    return datetime.datetime.utcnow()

class DecimalProperty(ndb.PickleProperty):
    pass

class MyInvoice(ndb.Model):
    """Model for one invoice"""
    created_at = ndb.DateTimeProperty(auto_now_add=True)
    token = ndb.StringProperty(indexed = True)

    # the "ask" amount
    amount = DecimalProperty(required = True)
    amount_cct = ndb.StringProperty(required = True)

    # actual amount expected after conversion
    payable = DecimalProperty(required = True)
    payable_cct = ndb.StringProperty(choices = ['BTC', 'LTC', 'XTN', 'BLK'])

    label = ndb.StringProperty()
    show_fiat = ndb.BooleanProperty()

    # After we talk to CK:
    pubkey = ndb.StringProperty(required=True)
    ck_refnum = ndb.StringProperty(required=True)
    paid_at = ndb.DateTimeProperty(default=None)

    @classmethod
    def recent_invoices(cls):
        return cls.query().order(-cls.created_at)

    @classmethod
    def get_by_token(cls, token_key):
        return cls.query(cls.token == token_key).get()

    def get_url(self):
        return '/invoice/%s' % self.token

    @property
    def has_no_conversion(self):
        return self.payable_cct == self.amount_cct

    @property
    def is_expired(self):
        if self.has_no_conversion: return False
        return (NOW() - self.created_at).total_seconds() > MAX_PAY_TIME

    @property
    def is_recent(self):
        # created in last 30 seconds; for highlight in table
        return (NOW() - self.created_at).total_seconds() < 30

    def get_time_left(self):
        if self.has_no_conversion: return MAX_PAY_TIME
        return max(0, MAX_PAY_TIME - (NOW() - self.created_at).total_seconds())
        

# EOF
