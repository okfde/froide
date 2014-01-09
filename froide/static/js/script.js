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

Froide.app.searchSimilarRequests = function(){
    var q = [], t, query;
    t = $(".foirequest input[name='public_body']:checked");
    if (t && t.val()!== "" && t.val() !== "new"){
        q.push($.trim(t.parent().text()));
    }
    var subject = $("#id_subject").val();
    if (subject.length > 0) {
        q.push(subject);
        var checkList = $('#check-list');
        checkList.find('.search-internet').remove();
        checkList.append(
            Mustache.to_html(
                Froide.template.searchInternet,
                {
                    url: Mustache.to_html(
                        Froide.template.searchEngineUrl,
                        {query: subject, domain: ""}
                    ),
                    query: subject
                }
            )
        );

    }
    if (q.length === 0){
        return;
    }
    query = q[q.length - 1];
    $.getJSON(Froide.url.searchRequests, {"q": query}, function(data){
        var results = data.objects;
        if (results.length === 0){
            $("#similar-requests-container").css({"visibility": "hidden"});
        } else {
            $("#similar-requests").html("");
            for (var i = 0; i < results.length; i += 1){
                var result = results[i];
                $("#similar-requests").append('<li><a title="' + result.public_body_name + '" href="' + result.url + '">' + result.title + '</a></li>');
            }
            $("#similar-requests").hide();
            $("#similar-requests-container").css({"visibility": "visible"});
            $("#similar-requests").show("normal");
        }
    });
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

Froide.app.performReview = (function(){
    var regex_email = /[^\s]+@[^\.\s]+\.\w+/;

    var resolve_forms = function(html){
        html = $(html);
        html.find('label input').each(function(i, el){
            el = $(el);
            if (!el.prop("checked")){
                el.parent().remove();
            } else {
                el.parent().replaceWith(el.attr("value"));
            }
        });
        return html.text().replace(/\n\n\n/g, "\n\n").replace(/ {2}/g, " ");
    };

    var no_email = function(str){
        var result = regex_email.exec(str);
        if (result !== null){
            return Mustache.to_html(Froide.template.foundEmail, {email: result[0]});
        }
        return undefined;
    };

    var checkRegexWithError = function(regexList, errorTemplate){
        return function(str){
            var result, i;
            for (i = 0; i< regexList.length; i += 1){
                result = regexList[i].exec(str);
                if (result !== null){
                    return Mustache.to_html(errorTemplate, {find: result[0]});
                }
            }
            return undefined;
        };
    };
    var no_greetings = function(str){
        return checkRegexWithError(Froide.regex.greetings, Froide.template.foundGreeting)(str);
    };
    var no_closings = function(str){
        return checkRegexWithError(Froide.regex.closings, Froide.template.foundClosing)(str);
    };


    var non_empty = function(str){
        if (str.replace(/\s/g, "").length === 0){
            return true;
        }
        return undefined;
    };
    var non_empty_body = function(str){
        if (non_empty(str)){
            return Froide.template.emptyBody;
        }
        return undefined;
    };
    var non_empty_subject = function(str){
        if (non_empty(str)){
            return Froide.template.emptySubject;
        }
        return undefined;
    };

    var getFullName = function(){
        var fullname = $("#fullname").length === 0 ? false : $("#fullname").text();
        if (!fullname){
            return $("#id_first_name").val() + " " + $("#id_last_name").val();
        }
        return fullname;
    };

    var getEmail = function(){
        var email = $("#email_address").length === 0 ? false : $("#email_address").text();
        if (!email){
            return $("#id_user_email").val();
        }
        return email;
    };

    var getAddress = function(){
        var address = $("#post_address").length === 0 ? false : $("#post_address").text();
        if (!address){
            return $("#id_address").val();
        }
        return address;
    };

    var getPublicBody = function(){
        var pb = $("#review-publicbody").length === 0 ? false : $("#review-publicbody").text();
        if (!pb){
            return $(".foirequest input[name='public_body']:checked").parent().text();
        }
        return pb;
    };

    return function(){
        var text, result, inputId, i, warnings = [],
            reviewWarnings = $("#review-warnings");
        var fullText = $('#id_full_text').prop('checked');

        var formChecks = {
            "id_subject": [non_empty_subject],
            "id_body": [non_empty_body, no_email]
        };
        if (!fullText) {
            formChecks.id_body.push(no_greetings);
            formChecks.id_body.push(no_closings);
        }
        reviewWarnings.html("");

        for (inputId in formChecks){
            if (formChecks.hasOwnProperty(inputId)){
                for (i = 0; i < formChecks[inputId].length; i += 1){
                    result = formChecks[inputId][i]($("#"+inputId).val());
                    if (result !== undefined){
                        warnings.push(result);
                    }
                }
            }
        }
        if (warnings.length === 0){
            reviewWarnings.hide();
        } else {
            for(i=0; i < warnings.length; i += 1){
                reviewWarnings.append("<li>" + warnings[i] + "</li>");
            }
            reviewWarnings.show();
        }
        $("#review-from").text(getFullName() + " <" + getEmail() +">");
        $("#review-to").text(getPublicBody());
        $("#review-subject").text($("#id_subject").val());
        text = '';
        if (fullText) {
            text += '<div class="highlight">' + $("#id_body").val() + "</div>";
        } else {
            text += resolve_forms($('#letter_start').clone());
            text += '\n\n<div class="highlight">' + $("#id_body").val() + "</div>\n\n";
            text += $('#letter_end').text();
        }
        text += "\n" + getFullName();
        text += "\n\n" + getAddress();
        $("#review-text").html(text);
    };
}());

Froide.app.publicBodyChosen = (function(){
    var doneChoice;
    var checkList = $("#check-list");
    var showFormForLaw = function(law){
        $('#letter_start').html(law.letter_start_form);
        $('#letter_end').html(law.letter_end_form);
        if (law.description_html.length) {
            $('#law-description-text').html(law.description_html);
            $('#law-description').show();
        } else {
            $('#law-description').hide();
        }
    };
    return function(currentPublicBodyChoice, publicBodyPrefilled){
        if(publicBodyPrefilled){
            return;
        }
        checkList.html("");
        var query = $(".search-public_bodies").val();
        if (query) {
            checkList.find('.search-internet').remove();
            checkList.append(Mustache.to_html(Froide.template.searchInternet,
                    {url: Mustache.to_html(Froide.template.searchEngineUrl,
                        {query: query, domain: ""}),
                    query: query
                }));
        }
        if (currentPublicBodyChoice !== undefined &&
                currentPublicBodyChoice !== "" &&
                currentPublicBodyChoice !== "new"){
            (function(lastChoice){
                $.getJSON(Froide.url.showPublicBody.replace(/0/,
                    currentPublicBodyChoice), {},
                    function(result){
                        if (lastChoice !== currentPublicBodyChoice){
                            return;
                        }
                        if (lastChoice === doneChoice){
                            return;
                        }
                        var request_note = result.default_law.request_note_html + result.request_note_html;
                        if (request_note){
                            $("#request-note").html(request_note).slideDown();
                        } else {
                            $("#request-note").hide();
                        }
                        if (result.url){
                            result.domain = result.url.split('/')[2];
                            checkList.find('.visit-public-body-website').remove();
                            checkList.append('<li class="visit-public-body-website"><a href="'+result.url+'">' +
                                Mustache.to_html(Froide.template.visitPublicBodyWebsite) +
                            '</a></li>');
                            $("#publicbody-link").attr("href", result.url);
                            $("#publicbody-link").html(Mustache.to_html(Froide.template.visitPublicBodyWebsite));
                        }
                        if (result.domain){
                            checkList.find('.search-public-body-website').remove();
                            checkList.append(Mustache.to_html(
                                Froide.template.searchPublicBodyWebsite,
                                {url: Mustache.to_html(
                                    Froide.template.searchEngineUrl,
                                    {query: query, domain: result.domain})}
                            ));
                        }
                            // TODO: Create law chooser here
                        var chosenLaw = $('#id_law');
                        if(chosenLaw.length){
                            chosenLaw.val(result.default_law.id);
                        } else {
                            $("#public-body").append('<input id="chosen-law" type="hidden" name="law" value="'+result.default_law.id+'"/>');
                        }
                        showFormForLaw(result.default_law);
                        doneChoice = lastChoice;
                    });
            }(currentPublicBodyChoice));
        } else {
            doneChoice = currentPublicBodyChoice;
            $("#request-note").slideUp();
            showFormForLaw(Froide.cachedLaw);
        }
    };
}());

Froide.app.statusSet = (function(){
    return function(){
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
}());

Froide.app.activateFoiCheck = function(){
    if ($("#check-foi").length === 0){
        Froide.app.activateMessage();
        return;
    }
    if ($("#step-message").css("display") === "block"){
        return;
    }
    $("#public-body").removeClass("active");
    $("#step-checkfoi").slideDown()
        .removeClass("hidden")
        .parent().addClass("active");
};

Froide.app.activateMessage = function(){
    $("#check-foi").removeClass("active");
    $("#step-checkfoi").hide();
    $("#step-message").slideDown()
        .removeClass("hidden")
        .parent().addClass("active");
    $('#id_subject').focus();

};

$(function(){
    $(document).on('click', "a.target-new", function(e){
        e.preventDefault();
        window.open($(this).attr("href"));
    });
    $(document).on('click', "a.target-small", function(e){
        e.preventDefault();
        var win = window.open($(this).attr("href"), "",
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

    $('.btn').on('touchend', function(){ $(this).click(); });

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
