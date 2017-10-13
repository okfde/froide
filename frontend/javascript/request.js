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

  var setStatus = function () {
    $('.status-refusal').hide()
    var resolution = $('#id_resolution').val()
    if (/refus/.exec(resolution) !== null || /partial/.exec(resolution) !== null) {
      $('.status-refusal').slideDown()
    }
    var redirected = $('input[name="status"][value="request_redirected"]').prop('checked')
    $('.status-redirected').hide()
    if (redirected) {
      $('.status-redirected').slideDown()
    }
  }

  $('#id_resolution').change(setStatus)

  $('input[name="status"]').change(setStatus)

  setStatus()

  $('a[data-tabgo="tab"]').click(function (e) {
    e.preventDefault()
    $(this).tab('show')
  })

  let activeTab = window.Froide.config.activeTab
  if (activeTab) {
    $('.request-nav a[href="#' + activeTab + '"]').tab('show')
  }
})
