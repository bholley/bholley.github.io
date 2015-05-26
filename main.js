$(document).ready(function() {
  var ref = document.referrer;
  if (ref.startsWith(location.origin)) {
    $('#topcontainer').removeClass('firstvisit');
  }

  if (ref.length > location.origin.length + 1) {
    $('#fixedcontent').removeClass('firstvisit');
  }
});
