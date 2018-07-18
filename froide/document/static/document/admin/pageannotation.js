window.django.jQuery(function () {
  var $ = window.django.jQuery
  var left = null
  var top = null
  var pageRect = $('#page_rect')
  var image = $('#page_image')
  var naturalWidth = image[0].naturalWidth
  var naturalHeight = image[0].naturalHeight
  image.on('load', function () {
    naturalWidth = image[0].naturalWidth
    naturalHeight = image[0].naturalHeight
  })
  image.on('mousedown', function (e) {
    if (left !== null) {
      var offsetWidth = image[0].offsetWidth
      var offsetHeight = image[0].offsetHeight
      var ratioX = naturalWidth / offsetWidth
      var ratioY = naturalHeight / offsetHeight
      $('#id_left').val(Math.round(left * ratioX))
      $('#id_top').val(Math.round(top * ratioY))
      var w = Math.round((e.offsetX - left) * ratioX)
      var h = Math.round((e.offsetY - top) * ratioY)
      $('#id_width').val(w)
      $('#id_height').val(h)

      left = null
      top = null
      return
    }
    left = e.offsetX
    top = e.offsetY
    pageRect.css('left', left)
    pageRect.css('top', top)
    pageRect.css('width', left)
    pageRect.css('height', top)
  })
  image.on('mousemove', function (e) {
    if (left === null) {
      return
    }
    pageRect.css('width', e.offsetX - left)
    pageRect.css('height', e.offsetY - top)
  })
})
