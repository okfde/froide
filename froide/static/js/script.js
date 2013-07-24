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
        text = resolve_forms($('#letter_start').clone());
        text += '\n\n<div class="highlight">' + $("#id_body").val() + "</div>\n\n";
        text += $('#letter_end').text();
        text += "\n\n" + getFullName();
        text += "\n\n" + getAddress();
        $("#review-text").html(text);
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
        $(el).scrollToFixed({marginTop: 10, minWidth: 768});
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

    $('.copyinput').click(function(e){
        $(this).select();
    });

    $('form.ajaxified').submit(function(e){
        e.preventDefault();
        var form = $(this);
        $.ajax({
            type: form.attr('method'),
            url: form.attr('action'),
            data: form.serialize(),
            success: function(response) {
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

/*
 * ScrollToFixed by Joseph Cava-Lynch
 * https://github.com/bigspotteddog/ScrollToFixed
*/
(function(a){a.isScrollToFixed=function(b){return a(b).data("ScrollToFixed")!==undefined};a.ScrollToFixed=function(d,h){var k=this;k.$el=a(d);k.el=d;k.$el.data("ScrollToFixed",k);var c=false;var F=k.$el;var G;var D;var p;var C=0;var q=0;var i=-1;var e=-1;var t=null;var y;var f;function u(){F.trigger("preUnfixed.ScrollToFixed");j();F.trigger("unfixed.ScrollToFixed");e=-1;C=F.offset().top;q=F.offset().left;if(k.options.offsets){q+=(F.offset().left-F.position().left)}if(i==-1){i=q}G=F.css("position");c=true;if(k.options.bottom!=-1){F.trigger("preFixed.ScrollToFixed");w();F.trigger("fixed.ScrollToFixed")}}function m(){var H=k.options.limit;if(!H){return 0}if(typeof(H)==="function"){return H.apply(F)}return H}function o(){return G==="fixed"}function x(){return G==="absolute"}function g(){return !(o()||x())}function w(){if(!o()){t.css({display:F.css("display"),width:F.outerWidth(true),height:F.outerHeight(true),"float":F.css("float")});F.css({width:F.width(),position:"fixed",top:k.options.bottom==-1?s():"",bottom:k.options.bottom==-1?"":k.options.bottom,"margin-left":"0px"});F.addClass("scroll-to-fixed-fixed");if(k.options.className){F.addClass(k.options.className)}G="fixed"}}function b(){var I=m();var H=q;if(k.options.removeOffsets){H=0;I=I-C}F.css({width:F.width(),position:"absolute",top:I,left:H,"margin-left":"0px",bottom:""});G="absolute"}function j(){if(!g()){e=-1;t.css("display","none");F.css({width:"",position:D,left:"",top:p.top,"margin-left":""});F.removeClass("scroll-to-fixed-fixed");if(k.options.className){F.removeClass(k.options.className)}G=null}}function v(H){if(H!=e){F.css("left",q-H);e=H}}function s(){var H=k.options.marginTop;if(!H){return 0}if(typeof(H)==="function"){return H.apply(F)}return H}function z(){if(!a.isScrollToFixed(F)){return}var J=c;if(!c){u()}var H=a(window).scrollLeft();var K=a(window).scrollTop();var I=m();if(k.options.minWidth&&a(window).width()<k.options.minWidth){if(!g()||!J){n();F.trigger("preUnfixed.ScrollToFixed");j();F.trigger("unfixed.ScrollToFixed")}}else{if(k.options.bottom==-1){if(I>0&&K>=I-s()){if(!x()||!J){n();F.trigger("preAbsolute.ScrollToFixed");b();F.trigger("unfixed.ScrollToFixed")}}else{if(K>=C-s()){if(!o()||!J){n();F.trigger("preFixed.ScrollToFixed");w();e=-1;F.trigger("fixed.ScrollToFixed")}v(H)}else{if(!g()||!J){n();F.trigger("preUnfixed.ScrollToFixed");j();F.trigger("unfixed.ScrollToFixed")}}}}else{if(I>0){if(K+a(window).height()-F.outerHeight(true)>=I-(s()||-l())){if(o()){n();F.trigger("preUnfixed.ScrollToFixed");if(D==="absolute"){b()}else{j()}F.trigger("unfixed.ScrollToFixed")}}else{if(!o()){n();F.trigger("preFixed.ScrollToFixed");w()}v(H);F.trigger("fixed.ScrollToFixed")}}else{v(H)}}}}function l(){if(!k.options.bottom){return 0}return k.options.bottom}function n(){var H=F.css("position");if(H=="absolute"){F.trigger("postAbsolute.ScrollToFixed")}else{if(H=="fixed"){F.trigger("postFixed.ScrollToFixed")}else{F.trigger("postUnfixed.ScrollToFixed")}}}var B=function(H){if(F.is(":visible")){c=false;z()}};var E=function(H){z()};var A=function(){var I=document.body;if(document.createElement&&I&&I.appendChild&&I.removeChild){var K=document.createElement("div");if(!K.getBoundingClientRect){return null}K.innerHTML="x";K.style.cssText="position:fixed;top:100px;";I.appendChild(K);var L=I.style.height,M=I.scrollTop;I.style.height="3000px";I.scrollTop=500;var H=K.getBoundingClientRect().top;I.style.height=L;var J=(H===100);I.removeChild(K);I.scrollTop=M;return J}return null};var r=function(H){H=H||window.event;if(H.preventDefault){H.preventDefault()}H.returnValue=false};k.init=function(){k.options=a.extend({},a.ScrollToFixed.defaultOptions,h);k.$el.css("z-index",k.options.zIndex);t=a("<div />");G=F.css("position");D=F.css("position");p=a.extend({},F.offset());if(g()){k.$el.after(t)}a(window).bind("resize.ScrollToFixed",B);a(window).bind("scroll.ScrollToFixed",E);if(k.options.preFixed){F.bind("preFixed.ScrollToFixed",k.options.preFixed)}if(k.options.postFixed){F.bind("postFixed.ScrollToFixed",k.options.postFixed)}if(k.options.preUnfixed){F.bind("preUnfixed.ScrollToFixed",k.options.preUnfixed)}if(k.options.postUnfixed){F.bind("postUnfixed.ScrollToFixed",k.options.postUnfixed)}if(k.options.preAbsolute){F.bind("preAbsolute.ScrollToFixed",k.options.preAbsolute)}if(k.options.postAbsolute){F.bind("postAbsolute.ScrollToFixed",k.options.postAbsolute)}if(k.options.fixed){F.bind("fixed.ScrollToFixed",k.options.fixed)}if(k.options.unfixed){F.bind("unfixed.ScrollToFixed",k.options.unfixed)}if(k.options.spacerClass){t.addClass(k.options.spacerClass)}F.bind("resize.ScrollToFixed",function(){t.height(F.height())});F.bind("scroll.ScrollToFixed",function(){F.trigger("preUnfixed.ScrollToFixed");j();F.trigger("unfixed.ScrollToFixed");z()});F.bind("detach.ScrollToFixed",function(H){r(H);F.trigger("preUnfixed.ScrollToFixed");j();F.trigger("unfixed.ScrollToFixed");a(window).unbind("resize.ScrollToFixed",B);a(window).unbind("scroll.ScrollToFixed",E);F.unbind(".ScrollToFixed");k.$el.removeData("ScrollToFixed")});B()};k.init()};a.ScrollToFixed.defaultOptions={marginTop:0,limit:0,bottom:-1,zIndex:1000};a.fn.scrollToFixed=function(b){return this.each(function(){(new a.ScrollToFixed(this,b))})}})(jQuery);
