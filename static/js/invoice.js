

var CK_INVOICE = (function () {
    var my = {};

    // These are overriden by the template code.
    my.max_time = 15 * 60;
    my.time_left = my.max_time;

    function set_expired() {
        $('#js-expired').height($('#js-most-stuff').height());
        $('#js-most-stuff').hide()
        $('#js-expired').show()

        $('#js-time-percent').width(0);
        $('#js-time-left').text('expired');

        my.time_left = 0;
    }

    function tick_handler() {
        // called once per second
        if(my.time_left <= 0) return;

        my.time_left -= 1;

        if(my.time_left) {
            $('#js-time-left').text(numeral(my.time_left).format('0:00:00') + ' left');
            $('#js-time-percent').width(((100*my.time_left) / my.max_time) + '%');
        } else {
            // done.
            set_expired();
        }
    }

    my.select_contents = function(evt) {
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

    my.startup = function() {
        console.log("Startup code");

        $(".js-tooltip").tooltip();
        $(".js-popover").popover();

        $(".js-selectable").on('click', my.select_contents)
                    .attr('title', 'Click to select for copying').tooltip();

        if(typeof(THIS_INVOICE) != 'undefined') {
            my.time_left = THIS_INVOICE.time_left;
            my.max_time = THIS_INVOICE.max_time;

            if(my.time_left <= 0) {
                set_expired();
            } else {
                my.tick_id = window.setInterval(tick_handler, 1000);
            }
        }
    };

    return my;
}());

head.ready(document, function () {
    CK_INVOICE.startup()
});

