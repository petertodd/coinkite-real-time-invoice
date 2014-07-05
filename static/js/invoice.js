

var CK_INVOICE = (function () {
    var my = {},
        privateVariable = 1;

    function privateMethod() {
        // ...
    }

    my.moduleProperty = 1;

    my.selectContents = function(evt) {
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

        $(".js-selectable").on('click', my.selectContents).attr('title', 'Click to select for clipboard copy');
    };

    return my;
}());

head.ready(document, function () {
    CK_INVOICE.startup()
});

