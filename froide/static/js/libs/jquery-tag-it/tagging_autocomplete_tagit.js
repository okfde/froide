if(!jQuery && window.django) var jQuery = window.django.jQuery;

jQuery(function(){
  'use strict';
  var options;
  window.init_jQueryTagit = window.init_jQueryTagit || [];
  options = window.init_jQueryTagit.pop();

  var setUpTagging = function(options){
      jQuery('#' + options.objectId).tagit({
          singleFieldDelimiter: ', ',
          fieldName: options.fieldName,
          tagSource: function(request, response){
              jQuery.getJSON(options.sourceUrl, {
                  query: request.term,
                  kind: options.kind,
                  format: 'json'
              }, response);
          },
          minLength: options.minLength,
          removeConfirmation: options.removeConfirmation,
          caseSensitive: options.caseSensitive,
          animate: options.animate,
          maxLength: options.maxLength,
          maxTags: options.maxTags,
          placeholderText: options.placeholderText,
          allowSpaces: options.allowSpaces,
          // Event callbacks.
          onTagAdded  : options.onTagAdded,
          onTagRemoved: options.onTagRemoved,
          onTagClicked: options.onTagClicked,
          onMaxTagsExceeded: options.onMaxTagsExceeded
      });
  };

  while (options) {
    setUpTagging(options);
    options = window.init_jQueryTagit.pop();
  }
});