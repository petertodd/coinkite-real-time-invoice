

var CK_INVOICE = (function () {
    var my = {};

    // These are overriden on startup.
    my.max_time = 15 * 60;
    my.time_left = my.max_time;
    my.ck_refnum = 'none';

    function set_expired() {
        $('#js-expired').height($('#js-most-stuff').height());
        $('#js-most-stuff').hide()
        $('#js-expired').show()

        $('#js-time-percent').width(0);
        $('#js-time-left').text('expired');

        my.time_left = 0;
    }

    my.set_ispaid = function() {
        $('#js-paid').height($('#js-most-stuff').height());
        $('#js-most-stuff').hide()
        $('#js-paid').show()

        $('#js-time-percent').width(0);
        $('#js-time-left').hide();

        my.time_left = 0;
    }

    function tick_handler() {
        // called once per second
        // NOTE: this is the wrong way to do this, but only a demo!
        if(my.time_left <= 0) return;

        my.time_left -= 1;

        if(my.time_left > 0) {
            $('#js-time-left').text(numeral(my.time_left).format('0:00:00') + ' left');
            $('#js-time-percent').width(((100*my.time_left) / my.max_time) + '%');
        } else {
            // done.
            set_expired();
        }
    }

    my.startup = function(time_left, max_time, ck_refnum) {
		// We have an invoice to work with. Animate it.
        my.time_left = time_left;
        my.max_time = max_time;
        my.ck_refnum = ck_refnum;

        if(my.time_left <= 0) {
            set_expired();
        } else {
            my.tick_id = window.setInterval(tick_handler, 1000);
        }
    }

    my.got_event = function(msg) {
        if(msg.request != my.ck_refnum) return;

        my.set_ispaid()
    }

    return my;
}());

head.ready(document, function () {

    // All pages need these
    $(".js-tooltip").tooltip();
    $(".js-popover").popover();

    select_contents = function(evt) {
      var text = evt.target;
      var doc = document, range, selection;    

      if(doc.body.createTextRange) {
          range = document.body.createTextRange();

          range.moveToElementText(text);
          range.select();
      } else if(window.getSelection) {
          range = document.createRange();
          range.selectNodeContents(text);

          selection = window.getSelection();        

          if(selection != range) {
              selection.removeAllRanges();
              selection.addRange(range);
          }
      }
    };

    $(".js-selectable").on('click', select_contents)
                    .attr('title', 'Click to select for copying').tooltip();

    if(typeof(THIS_INVOICE) != 'undefined') {
        THIS_INVOICE();
    }
});

