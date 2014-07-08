from ckapi import CKRequestor

# Copy the API Key (first) and API Secret (second) from Coinkite into these strings.
#
CK_API = CKRequestor(
            'Kxxxx-xxxx-xxxxxxxx',
            'Sxxxx-xxxxx-xxxxxxxx')

# We need to know which account will be used for each currency.
#
# You can provide a number (subaccount number), name (exact match) or CK refnumber here.
#
# TODO: this would be better as a list of names / accounts and currencies, so you can 
# have multiple target accounts.
#
ACCOUNT_MAP = dict(BTC=0, LTC=2, XTN=3, BLK=4)

# DELETE THIS LINE once you've done the above.
raise NotImplementedError
