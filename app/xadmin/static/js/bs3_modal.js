setTimeout(function () {
    var frm = $('.modal form');
    frm.ajaxForm(function(resp) {
        var prnt = frm.parent('.modal-content')
        prnt.html('')
        prnt.html(resp);
        // console.log('ajaxForm resp ==> ', resp);
           // alert("Thank you for your comment!");
      });
}, 100);

// $('body').on('submit', '.modal form', function (e) {
//  var frm = $(this);
//  console.log('before submit', this, e);
//  e.preventDefault();
//  frm.ajaxForm(function(resp) {
//      var prnt = frm.parent('.modal-content')
//      prnt.html('')
//      prnt.html(resp);
//      console.log('ajaxForm resp ==> ', arguments);
//            // alert("Thank you for your comment!");
//       });
//  console.log('---------------------------');
//  return false;
// });