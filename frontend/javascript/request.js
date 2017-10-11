import $ from 'jquery'

import 'bootstrap/js/src/tooltip'
import 'bootstrap/js/src/tab'

$(function () {
  $('form').submit(function () {
    $(this).find('button[type="submit"]').prop('disabled', true)
  })
  $('*[data-toggle=tooltip]').tooltip()

  $(document).on('click', 'a.toggle', function (e) {
    e.preventDefault()
    var obj = $('#' + $(this).attr('href').split('#')[1])
    if (obj.css('display') === 'none') {
      obj.slideDown()
    } else {
      obj.slideUp()
    }
  })
  $('.comment-form').hide()

  $('a.show-text').on('click', function (e) {
    e.preventDefault()
    $(this).parent().find('.hidden-text').toggle()
  })

  $('#id_resolution').change(function () {
    // Froide.app.statusSet()
  })

  $('input[name="status"]').change(function () {
    // Froide.app.statusSet()
  })

  // Froide.app.statusSet()
})
