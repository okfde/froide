var Froide = Froide || {};
var loggedInCallback;

Froide.app = Froide.app || {};

Froide.app.justSelected = false;

Froide.app.getPublicBodyResultListItem = function(el, result){
    var name = el.attr("data-inputname");
    var li = '<li class="result"><label class="radio">';
    li += '<input type="radio" name="' + name + '" value="' + result.id + '"/>\n';
    li += result.name + ' (' + result.jurisdiction +') ';
    li += Mustache.to_html(Froide.template.publicBodyListingInfo, {url: result.url});
    li += '</label></li>';
    return li;
};

Froide.app.selectSearchListItem = function(el, li){
    var html = '<div class="selected-result">' + li.html() + '</div>';
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
        q.push(jQuery.trim(t.parent().text()));
    }
    var subject = $("#id_subject").val();
    if (subject.length > 0){
        q.push(subject);
    }
    if (q.length === 0){
        return;
    }
    query = q[q.length - 1];
    $.getJSON(Froide.url.searchRequests, {"q": query}, function(results){
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
        if (lastPublicBodyQuery === query && lastJurisdiction === juris){
            el.find(".search-results").slideDown();
            return;
        }
        el.find(".search-spinner").fadeIn();
        el.find(".search-results").hide();
        $.getJSON(Froide.url.searchPublicBody, params, function(results){
            var result, i;
            lastPublicBodyQuery = query;
            lastJurisdiction = juris;
            el.find(".search-spinner").hide();
            el.find(".search-results .result").remove();
            if (results.length === 0){
                if ($('.selected-result').length === 0){
                    el.find(".empty-result").show();
                    el.find(".search-results").show();
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
                el.find(".result input").change(function(e){
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
            if (!el.attr("checked")){
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
    
    var no_greetings = function(str){
        var result, i;
        for (i = 0; i< Froide.regex.greetings.length; i += 1){
            result = Froide.regex.greetings[i].exec(str);
            if (result !== null){
                return Mustache.to_html(Froide.template.foundGreeting, {find: result[0]});
            }
        }
        return undefined;
    };
    
    var no_closings = function(str){
        var result, i;
        for (i = 0; i< Froide.regex.closings.length; i += 1){
            result = Froide.regex.closings[i].exec(str);
            if (result !== null){
                return Mustache.to_html(Froide.template.foundClosing, {find: result[0]});
            }
        }
        return undefined;
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
    var formChecks = {
        "id_subject": [non_empty_subject],
        "id_body": [non_empty_body, no_email, no_greetings, no_closings]
    };

    var openLightBox = function(){
        var currentScrollTop = $("#write-request").offset().top;
        var box = $('#step-review');
        box.fadeIn();
        box.css({
            'margin-top' : -(box.height() + 80) / 2,
            'margin-left' : -(box.width() + 80) / 2
        });
        $('#lightbox-background').css({'filter' : 'alpha(opacity=80)'}).fadeIn();
        var closeLightBox = function(){
            $("body").css({"overflow": "auto"});
            $('#lightbox-background, .lightbox').fadeOut();
            window.setTimeout(function(){
                $(window).scrollTop(currentScrollTop);
            }, 100);
        };
        $('#lightbox-background').live('click', closeLightBox);
        $('.lightbox a.close').live('click', closeLightBox);
        $("body").css({"overflow": "hidden"});
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
            reviewWarnings = $("#review-warnings"),
            subject, from, to;
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
            reviewWarnings.parent().hide();
        } else {
            for(i=0; i < warnings.length; i += 1){
                reviewWarnings.append("<li>" + warnings[i] + "</li>");
            }
            reviewWarnings.show();
        }
        $("#review-from").text(getFullName() + " <" + getEmail() +">");
        $("#review-to").text(getPublicBody());
        $("#review-subject").text($("#id_subject").val());
        text = resolve_forms($('#letter_start').clone());
        text += '\n\n<div class="highlight">' + $("#id_body").val() + "</div>\n\n";
        text += resolve_forms($('#letter_end').clone());
        text += "\n" + getFullName();
        text += "\n\n" + getAddress();
        $("#review-text").html(text);
        openLightBox();
    };
}());

Froide.app.publicBodyChosen = (function(){
    var doneChoice;
    var showFormForLaw = function(law){
        $('#letter_start').html(law.letter_start_form);
        $('#letter_end').html(law.letter_end_form);
        if (law.description_markdown.length) {
            $('#law-description-text').html(law.description_markdown);
            $('#law-description').show();
        } else {
            $('#law-description').hide();
        }
    };
    return function(currentPublicBodyChoice, publicBodyPrefilled){
        if(publicBodyPrefilled){
            return;
        }
        var list = $("#check-list").html("");
        var query = $("#search-public_bodies").val();
        // if(query !== ""){
        //     list.append(Mustache.to_html(Froide.template.searchInternet,
        //             {url: Mustache.to_html(Froide.template.searchEngineUrl,
        //             {query: query, domain: ""})}));
        // }
        if (currentPublicBodyChoice !== undefined &&
                currentPublicBodyChoice !== "" &&
                currentPublicBodyChoice !== "new"){
            (function(lastChoice){
                $.getJSON(Froide.url.showPublicBody.replace(/0\.json/,
                    currentPublicBodyChoice +".json"),{},
                    function(result){
                        if (lastChoice !== currentPublicBodyChoice){
                            return;
                        }
                        if (lastChoice === doneChoice){
                            return;
                        }
                        var request_note = result.laws[0].request_note_markdown + result.request_note_markdown;
                        if (request_note){
                            $("#request-note").html(request_note).slideDown();
                        } else {
                            $("#request-note").hide();
                        }
                        if (result.url){
                            list.append('<li><a href="'+result.url+'">' + Froide.template.visitPublicBodyWebsite + '</a></li>');
                            $("#publicbody-link").attr("href", result.url);
                            $("#publicbody-link").text(Froide.template.visitPublicBodyWebsite);
                        }
                        if (result.domain){
                            list.append(Mustache.to_html(
                                Froide.template.searchPublicBodyWebsite,
                                {url: Mustache.to_html(
                                    Froide.template.searchEngineUrl,
                                    {query: query, domain: result.domain})}
                            ));
                        }
                            // TODO: Create law chooser here
                        var chosenLaw = $('#id_law');
                        if(chosenLaw.length){
                            chosenLaw.val(result.laws[0].pk);
                        } else {
                            $("#public-body").append('<input id="chosen-law" type="hidden" name="law" value="'+result.laws[0].pk+'"/>');
                        }
                        showFormForLaw(result.laws[0]);
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
        $(".status-redirected").hide();
        var status = $("#id_status").val();
        if (/refus/.exec(status) !== null || /partial/.exec(status) !== null) {
            $(".status-refusal").slideDown();
        } else if (/redirect/.exec(status) !== null){
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
    $("a.target-new").live('click', function(e){
        e.preventDefault();
        window.open($(this).attr("href"));
    });
    $("a.target-small").live('click', function(e){
        e.preventDefault();
        var win = window.open($(this).attr("href"), "",
                'height=500,width=800,resizable=yes,scrollbars=yes');
        win.focus();
    });
    $(".sticky").each(function(i, el){
         $(el).scrollToFixed({marginTop: 10});
    });
    $("a.show-target").live("click", function(e){
        var obj = $('#' + $(this).attr("href").split('#')[1]).find(".toggle");
        $(obj.attr("href")).show();
    });
    $("a.toggle").live("click", function(e){
        e.preventDefault();
        var obj = $('#' + $(this).attr("href").split('#')[1]);
        if (obj.css("display") === "none"){
            obj.slideDown();
        } else {
            obj.slideUp();
        }
    });

    $("a.hideparent").live("click", function(e){
        e.preventDefault();
        $(this).parent().hide();
    });
    $(".goto-form").each(function(i, el){
        window.location.href = "#" + $(el).attr("id");
    });
    $(".search-public_bodies-submit").click(function(e){
        Froide.app.performPublicBodySearch($(this).closest('.public_body-chooser'));
    });
    $(".search-public_bodies").keydown(function(e){
        if(e.keyCode === 13){
            e.preventDefault();
            Froide.app.performPublicBodySearch($(this).closest('.public_body-chooser'));
        }
    });
    $(".publicbody-search .searchexample").click(function(e){
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

/*
 * ScrollToFixed by Joseph Cava-Lynch
 * https://github.com/bigspotteddog/ScrollToFixed
*/
(function(a){a.ScrollToFixed=function(c,f){var i=this;i.$el=a(c);i.el=c;i.$el.data("ScrollToFixed",i);var b=false;var u=i.$el;var t=0;var l=0;var g=-1;var d=-1;var n=null;function o(){h();d=-1;t=u.offset().top;l=u.offset().left;if(g==-1){orginalOffsetLeft=l}b=true;if(i.options.bottom!=-1){q()}}function k(){return u.css("position")=="fixed"}function r(){return u.css("position")=="absolute"}function e(){return !(k()||r())}function q(){if(!k()){n.css({display:u.css("display"),width:u.outerWidth(true),height:u.outerHeight(true),"float":u.css("float")});u.css({width:u.width(),position:"fixed",top:i.options.bottom==-1?m():"",bottom:i.options.bottom==-1?"":i.options.bottom})}}function h(){if(!e()){d=-1;n.css("display","none");u.css({width:"",position:"",left:"",top:""})}}function p(v){if(v!=d){u.css("left",l-v);d=v}}function m(){return i.options.marginTop}function s(){if(!b){o()}var v=a(window).scrollLeft();var w=a(window).scrollTop();if(i.options.bottom==-1){if(i.options.limit>0&&w>=i.options.limit-m()){if(!r()){j();u.trigger("preAbsolute");u.css({width:u.width(),position:"absolute",top:i.options.limit,left:l});u.trigger("unfixed")}}else{if(w>=t-m()){if(!k()){j();u.trigger("preFixed");q();d=-1;u.trigger("fixed")}p(v)}else{if(k()){j();u.trigger("preUnfixed");h();u.trigger("unfixed")}}}}else{if(i.options.limit>0){if(w+a(window).height()-u.outerHeight(true)>=i.options.limit-m()){if(k()){j();u.trigger("preUnfixed");h();u.trigger("unfixed")}}else{if(!k()){j();u.trigger("preFixed");q()}p(v);u.trigger("fixed")}}else{p(v)}}}function j(){var v=u.css("position");if(v=="absolute"){u.trigger("postAbsolute")}else{if(v=="fixed"){u.trigger("postFixed")}else{u.trigger("postUnfixed")}}}i.init=function(){i.options=a.extend({},a.ScrollToFixed.defaultOptions,f);if(navigator.platform=="iPad"||navigator.platform=="iPhone"||navigator.platform=="iPod"){return}i.$el.css("z-index",i.options.zIndex);n=a("<div/>");i.$el.after(n);a(window).bind("resize",function(v){o();s()});a(window).bind("scroll",function(v){s()});if(i.options.preFixed){u.bind("preFixed",i.options.preFixed)}if(i.options.postFixed){u.bind("postFixed",i.options.postFixed)}if(i.options.preUnfixed){u.bind("preUnfixed",i.options.preUnfixed)}if(i.options.postUnfixed){u.bind("postUnfixed",i.options.postUnfixed)}if(i.options.preAbsolute){u.bind("preAbsolute",i.options.preAbsolute)}if(i.options.postAbsolute){u.bind("postAbsolute",i.options.postAbsolute)}if(i.options.fixed){u.bind("fixed",i.options.fixed)}if(i.options.unfixed){u.bind("unfixed",i.options.unfixed)}if(i.options.bottom!=-1){if(!k()){j();u.trigger("preFixed");q()}}};i.init()};a.ScrollToFixed.defaultOptions={marginTop:0,limit:0,bottom:-1,zIndex:1000};a.fn.scrollToFixed=function(b){return this.each(function(){(new a.ScrollToFixed(this,b))})}})(jQuery);