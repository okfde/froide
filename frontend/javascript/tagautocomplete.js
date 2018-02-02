import $ from 'jquery'

import 'select2/src/scss/core.scss'
import 'select2/dist/js/select2.min.js'

function setupTagging (objectid, sourceurl) {
  $(`#${objectid}_select2`).on('change.select2', function (e) {
    var tagString = $(this).select2('data').map(function (el) {
      return '"' + el.id + '"'
    }).join(', ')

    $(`#${objectid}`).val(tagString)
  }).select2({
    width: '75%%',
    tags: true,
    tokenSeparators: [',', ' '],
    ajax: {
      url: sourceurl,
      data: function (params) {
        if (params.term.length === 0) {
          return null
        }
        return { query: params.term }
      },
      processResults: function (data) {
        return {
          results: data.map(function (el) {
            return { id: el, text: el }
          })
        }
      }
    }
  })
}

module.exports = {
  setupTagging
}
export default module.exports
