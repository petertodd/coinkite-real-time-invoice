#
# Fun class to make receipts, easier...
# 
# Copyright (C) 2014 Coinkite Inc. (https://coinkite.com) ... See LICENSE.md
#
# Full docs at: https://docs.coinkite.com/
#
import functools

class CKPrintList(list):
    '''
    Holds a number of 'steps' to be printed, ie. the contents of a receipt

    See <https://docs.coinkite.com/api/receipt-cmds.html> for full details of the protocol.

    Also, a GET to <https:api.coinkite.com/v1/terminal/preview/print> will print help message.

    As of writing, these are the commands and their arguments.

        cmd: add_banner     [msg: REQUIRED]
        cmd: ck_footer     
        cmd: ck_header     
        cmd: double_copy    [first_label:  CUSTOMER COPY ] [second_label:  MERCHANT COPY ]
        cmd: huge           [msg: REQUIRED] [underlined: False]
        cmd: large          [msg: REQUIRED] [underlined: False]
        cmd: print_hash     [hex64: REQUIRED] [label: REQUIRED]
        cmd: qrcode         [data: REQUIRED]
        cmd: separator      [width: DEFAULT]
        cmd: skip           [height: REQUIRED]
        cmd: small          [msg: REQUIRED] [underlined: False]
        cmd: story          [text: REQUIRED] [gap: 20] [boxed: False]
        cmd: tear_off      
        cmd: tiny           [msg: REQUIRED] [underlined: False]
        cmd: xhuge          [msg: REQUIRED] [underlined: False]

    Resulting object (a list) is ready to be JSON'ified and passed to server.
    '''

    def _example_usage(self):
        "An example of how to use this class"
        self.ck_header()
        self.qrcode(data="https://coinkite.com")
        self.story(text="This is some long text about stuff", boxed=True)
        self.ck_footer()


    def __getattr__(self, name):
        def _new_instruction(cmd, **args):
            args['cmd'] = cmd
            self.append(args)
        return functools.partial(_new_instruction, name)
        

def test_paper():
    #
    # Call this with "py.test paper.py -s", or "python paper.py"
    #
    l = CKPrintList()
    l._example_usage()
    assert len(l) == 4

    from pprint import pprint
    pprint(l)

    k = [{'cmd': 'huge', 'msg': 'Hello World!'},
         {'cmd': 'qrcode', 'data': 'https://google.com?q=cats'},
         {'cmd': 'tiny', 'msg': 'This is a little message'}]

    k2 = CKPrintList()
    k2.huge(msg = 'Hello World!')
    k2.qrcode(data = 'https://google.com?q=cats')
    k2.tiny(msg = 'This is a little message')

    assert k2 == k
    
if __name__ == '__main__':
    test_paper()

# EOF
