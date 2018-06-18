import $ from 'jquery'

import 'bootstrap/js/src/tooltip'
import 'bootstrap/js/src/tab'

$(function () {
  $('form').submit(function () {
    $(this).find('button[type="submit"]').prop('disabled', true)
  })
  $('*[data-toggle=tooltip]').tooltip()

  $(document).on('click', '.hideparent', function (e) {
    e.preventDefault()
    $(this).parent().hide()
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
    $('.nav-link[href="' + $(this).attr('href') + '"]').tab('show')
  })

  let activeTab = window.Froide.config.activeTab
  if (activeTab && activeTab !== 'info') {
    $('.request-nav a[href="#' + activeTab + '"]').tab('show')
  } else {
    var hashNav = $('.request-nav a[href="' + document.location.hash + '"]')
    if (hashNav.length > 0) {
      $('.request-nav a[href="' + document.location.hash + '"]').tab('show')
    } else {
      $('.request-nav a[href="#info"]').tab('show')
    }
  }

  $('form.ajaxified').submit(function (e) {
    e.preventDefault()
    var form = $(this)
    $.ajax({
      type: form.attr('method'),
      url: form.attr('action'),
      data: form.serialize(),
      success: function (data, status, xhr) {
        if (xhr.status === 302) {
          window.location.href = xhr.getResponseHeader('Location')
        }
        if (data.length > 0) {
          form.closest('.ajax-parent').replaceWith(data)
        }
      }
    })
    form.find('button').attr('disabled', 'disabled')
    form.find('input').attr('disabled', 'disabled')
  })
})
