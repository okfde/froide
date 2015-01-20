/* jshint strict: true, quotmark: false, es3: true */
/* global $: false, Mustache: false */

var Froide = Froide || {};

(function(){
"use strict";

Froide.app = Froide.app || {};
Froide.app.justSelected = false;

Froide.app.getPublicBodyResultListItem = function(el, result){
    return Mustache.to_html(Froide.template.publicBodyListingInfo, {
        data_name: el.attr("data-inputname"),
        result_id: result.id,
        result_url: result.site_url,
        result_name: result.name,
        result_jurisdiction: result.jurisdiction.name
    });
};

Froide.app.selectSearchListItem = function(el, li){
    var html = '<div class="search-result selected-result">' + li.html() + '</div>';
    el.find(".selected-result").remove();
    el.find(".search-results").after(html);
    el.find(".selected-result input").attr("checked", "checked");
    el.find(".search-results").slideUp();
    el.trigger("publicBodyChosen");
};


Froide.app.performPublicBodySearch = (function(){
    var lastPublicBodyQuery = null, lastJurisdiction = null;
    return function(el){
        var query = el.find(".search-public_bodies").val();
        var juris = el.find('.search-public_bodies-jurisdiction');
        var params = {q: query};
        if (juris.length){
            juris = juris.val();
            params.jurisdiction = juris;
        }
        if (query === '') {
            return;
        }
        if (lastPublicBodyQuery === query && lastJurisdiction === juris){
            el.find(".search-results").slideDown();
            return;
        }
        el.find(".search-spinner").fadeIn();
        el.find(".search-results").hide();
        $.getJSON(Froide.url.searchPublicBody, params, function(data){
            var result, i, results = data.objects;
            lastPublicBodyQuery = query;
            lastJurisdiction = juris;
            el.find(".search-spinner").hide();
            el.find(".search-results .search-result").remove();
            if (results.length === 0){
                if ($('.selected-result').length === 0){
                    el.find(".empty-result").show();
                    el.find(".search-results").hide();
                    el.find('#request-note').hide();
                }
                return;
            } else {
                el.find(".empty-result").hide();
                if (Froide.app.justSelected) {
                    return;
                }
                for(i = 0; i < results.length; i += 1){
                    result = results[i];
                    var li = Froide.app.getPublicBodyResultListItem(el, result);
                    el.find(".search-results").append(li);
                }
                el.find(".search-result input").change(function(){
                    var li = $(this).closest('li');
                    Froide.app.selectSearchListItem(el, li);
                });
                el.find(".search-results").slideDown();
            }
        });
    };
}());


Froide.app.statusSet = function(){
    $(".status-refusal").hide();
    var resolution = $("#id_resolution").val();
    if (/refus/.exec(resolution) !== null || /partial/.exec(resolution) !== null) {
        $(".status-refusal").slideDown();
    }
    var redirected = $("input[name='status'][value='request_redirected']").prop('checked');
    $(".status-redirected").hide();
    if (redirected){
        $(".status-redirected").slideDown();
    }
};


$(function(){

    $(document).on('click', "a.target-new", function(e){
        e.preventDefault();
        window.open($(this).attr("href"));
    });
    $(document).on('click', "a.target-small", function(e){
        e.preventDefault();
        var win = window.open($(this).attr("href"), "popup",
                'height=500,width=800,resizable=yes,scrollbars=yes');
        win.focus();
    });
    $(document).on("click", "a.show-target", function(){
        var obj = $('#' + $(this).attr("href").split('#')[1]).find(".toggle");
        $(obj.attr("href")).show();
    });
    $('a.show-text').on('click', function(e){
        e.preventDefault();
        $(this).parent().find('.hidden-text').toggle();
    });
    $(document).on("click", "a.toggle", function(e){
        e.preventDefault();
        var obj = $('#' + $(this).attr("href").split('#')[1]);
        if (obj.css("display") === "none"){
            obj.slideDown();
        } else {
            obj.slideUp();
        }
    });

    $(document).on("click", "a.hideparent", function(e){
        e.preventDefault();
        $(this).parent().hide();
    });
    $(".goto-form").each(function(i, el){
        window.location.href = "#" + $(el).attr("id");
    });
    $(".search-public_bodies-submit").click(function(){
        Froide.app.performPublicBodySearch($(this).closest('.public_body-chooser'));
    });
    $(".search-public_bodies").keydown(function(e){
        if(e.keyCode === 13){
            e.preventDefault();
            Froide.app.performPublicBodySearch($(this).closest('.public_body-chooser'));
        }
    });
    $(".publicbody-search .search-examples a").click(function(e){
        e.preventDefault();
        var term = $(this).text();
        var par = $(this).closest('.public_body-chooser');
        par.find(".search-public_bodies").val(term);
        Froide.app.performPublicBodySearch(par);
    });

    $(".search-public_bodies").each(function(i, input){
        if($(input).val() !== ""){
            Froide.app.performPublicBodySearch($(this).closest('.public_body-chooser'));
        }
    });
    $("button.upload-button").click(function(e){
        var elem = $(this);
        var file = elem.parent().find("input[type='file']");
        if (file.length !== 0){
            if (file.val() === ""){
                e.preventDefault();
                file.click();
                file.change(function(){
                    if ($(this).val() !== ""){
                        elem.click();
                    }
                });
            }
        }
    });

    var activeTab = $('.nav a[href=' + location.hash + ']');
    if (activeTab) {
        activeTab.tab('show');
    }

    $('a[data-tabgo="tab"]').click(function(e){
      $(this).tab('show');
      activateNav(e);
    });

    $('a[data-toggle="tab"]').on('shown', activateNav);

    var activateNav = function (e) {
        $('.nav a[href="' + e.target.hash + '"]').closest('.nav').find('li').removeClass("active");
        $('.nav a[href="' + e.target.hash + '"]').parent().addClass("active");
    };

    $('.copyinput').click(function(){
        $(this).select();
    });

    $('form.ajaxified').submit(function(e){
        e.preventDefault();
        var form = $(this);
        $.ajax({
            type: form.attr('method'),
            url: form.attr('action'),
            data: form.serialize(),
            success: function() {
                var id = form.attr('id');
                form.hide();
                $('#' + id + '-success').fadeIn();
            }
        });
        form.find('button').attr('disabled', 'disabled');
        form.find('input').attr('disabled', 'disabled');
    });

    if (Froide && Froide.url && Froide.url.autocompletePublicBody){
        $(".publicbody-search").each(function(i, el){
            var input = $(el).find('.search-public_bodies');
            var params = {};
            var juris = $(el).find('.search-public_bodies-jurisdiction');
            if (juris.length){
                params.jurisdiction = juris.val();
            }
            var auto = input.autocomplete({
                serviceUrl: Froide.url.autocompletePublicBody,
                minChars: 3,
                params: params,
                onSelect: function(value, data){
                    Froide.app.justSelected = true;
                    window.setTimeout(function(){
                        Froide.app.justSelected = false;
                    }, 1000);
                    var li = Froide.app.getPublicBodyResultListItem(input.closest('.public_body-chooser'), data);
                    Froide.app.selectSearchListItem(input.closest('.public_body-chooser'), $(li));
                }
            });
            if (juris.length){
                juris.change(function(){
                    auto.options.params.jurisdiction = juris.val();
                    auto.clearCache();
                    auto.onValueChange();
                });
            }
        });
    }
});
}());
