import $ from 'jquery'

import {Tab} from 'bootstrap.native'

$(function () {
  $('form').submit(function () {
    $(this).find('button[type="submit"]').prop('disabled', true)
  })

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

  var requestNav = document.querySelector('.request-nav')

  // let's give the initialization a JavaScript reference for the "target" option
  var myTabsCollection = requestNav.getElementsByTagName('A')
  for (var i = 0; i < myTabsCollection.length; i++) {
    /* eslint-disable no-new */
    new Tab(myTabsCollection[i], {height: false})
  }

  $('#id_resolution').change(setStatus)

  $('input[name="status"]').change(setStatus)

  setStatus()

  $('a[data-tabgo="tab"]').click(function (e) {
    var href = this.attributes.getNamedItem('href').value
    var el = document.querySelector(href)
    var display = window.getComputedStyle(el, null).display
    if (display === 'none') {
      document.querySelector('.nav-link[href="' + href + '"]').Tab.show()
    }
    if (el.scrollIntoView) {
      e.preventDefault()
      el.scrollIntoView({behavior: 'smooth'})
    }
  })

  let activeTab = requestNav.dataset.activetab
  if (activeTab && activeTab !== 'info') {
    requestNav.querySelector('a[href="#' + activeTab + '"]').Tab.show()
  } else {
    var hash = document.location.hash
    hash = hash.replace(/[^#\w\-]/g, '')
    var hashNav = $('.request-nav a[href="' + hash + '"]')
    if (hashNav.length > 0) {
      requestNav.querySelector('a[href="' + hash + '"]').Tab.show()
    } else if (activeTab !== 'info') {
      requestNav.querySelector('a[href="#info"]').Tab.show()
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
