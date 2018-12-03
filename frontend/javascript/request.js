import $ from 'jquery'

import {Tab, Tooltip} from 'bootstrap.native'

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

  var addText = function (dataset) {
    const textField = document.querySelector(dataset.addtextfield)
    let text = textField.value
    let addedText = dataset.addtext
    if (text.indexOf(addedText) !== -1) {
      return
    }
    if (text.indexOf('\n...\n') !== -1) {
      text = text.replace('...', addedText)
    } else {
      let textParts = text.split('\n\n')
      textParts = textParts.slice(0, textParts.length - 1).concat([addedText, textParts[textParts.length - 1]])
      text = textParts.join('\n\n')
    }
    textField.value = text
  }

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

    if (this.dataset && this.dataset.value) {
      var sel = '[name="' + this.dataset.name + '"][value="' + this.dataset.value + '"]'
      el.querySelector(sel).checked = true
    }
    if (this.dataset && this.dataset.addtextfield) {
      addText(this.dataset)
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

  var messages = []
  document.querySelectorAll('.message-container').forEach(function (el) {
    var rect = el.getBoundingClientRect()
    var offset = rect.top + window.pageYOffset
    messages.push({
      top: offset,
      height: rect.height,
      id: el.id
    })
  })
  var activeMessage = null
  document.addEventListener('scroll', function () {
    var py = window.pageYOffset
    for (var i = 0; i < messages.length; i += 1) {
      var message = messages[i]
      if (py >= message.top && py <= message.top + message.height) {
        if (activeMessage !== message.id) {
          activeMessage = message.id
          var navEls = document.querySelectorAll('.message-timeline-listitem a')
          navEls.forEach(function (el) {
            el.classList.remove('active')
          })
          var navEl = document.querySelector('.message-timeline-listitem [href="#' + message.id + '"]')
          navEl.classList.add('active')
        }
        break
      }
    }
  })

  if (!('ontouchstart' in document)) {
    document.querySelectorAll('.message-timeline-item').forEach(function (el) {
      new Tooltip(el)
    })
  } else {
    var click = function () {
      this.click()
    }
    document.querySelectorAll('.message-timeline-item').forEach(function (el) {
      el.addEventListener('touchstart', click)
      // el.addEventListener('touchmove', click)
    })
  }
})
