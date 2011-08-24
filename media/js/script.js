var Froide = Froide || {};
var loggedInCallback;

Froide.app = Froide.app || {};

Froide.app.getPublicBodyResultListItem = function(el, result){
    var name = el.attr("data-inputname");
    var li = '<li class="result"><label>';
    li += '<input type="radio" name="' + name + '" value="' + result.id + '"/> ';
    li += result.name + '</label> - ';
    li += Mustache.to_html(Froide.template.publicBodyListingInfo, {url: result.url});
    li += '</li>';
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
    var lastPublicBodyQuery = null;
    return function(el){
        var query = el.find(".search-public_bodies").val();
        if (lastPublicBodyQuery === query){
            el.find(".search-results").slideDown();
            return;
        }
        el.find(".search-spinner").fadeIn();
        el.find(".search-results").hide();
        $.getJSON(Froide.url.searchPublicBody, {"q": query}, function(results){
            var result, i;
            lastPublicBodyQuery = query;
            el.find(".search-spinner").hide();
            el.find(".search-results .result").remove();
            if (results.length === 0){
                el.find(".empty-result").show();
                el.find(".search-results").show();
                return;
            } else {
                el.find(".empty-result").hide();
                for(i = 0; i < results.length; i += 1){
                    result = results[i];
                    var li = Froide.app.getPublicBodyResultListItem(el, result);
                    el.find(".search-results").append(li);
                }
                el.find(".result input").change(function(e){
                    var li = $(this).parent().parent();
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
                $.getJSON(Froide.url.showPublicBody
                        .replace(/0\.json/, 
                    currentPublicBodyChoice +".json"),{},
                    function(result){
                        if (lastChoice !== currentPublicBodyChoice){
                            return;
                        }
                        if (lastChoice === doneChoice){
                            return;
                        }
                        if (result.request_note_markdown){
                            $("#request-note").html(result.request_note_markdown).slideDown();
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
                        // $("#public-body").append('<input type="hidden" name="law" value="'+result.laws[0].pk+'"/>');
                        // $('#letter_start').text(result.laws[0].letter_start);
                        // $('#letter_end').text(result.laws[0].letter_end);
                        doneChoice = lastChoice;
                    });
            }(currentPublicBodyChoice));
        } else {
            doneChoice = currentPublicBodyChoice;
            $("#request-note").slideUp();
            // $('#letter_start').text(letter_start);
            // $('#letter_end').text(letter_end);
        }
    };
}());

Froide.app.statusSet = (function(){
    return function(){
        $(".status-refusal").hide();
        $(".status-payment").hide();
        $(".status-redirected").hide();
        var status = $("#id_status").val();
        if (/refus/.exec(status) !== null) {
            $(".status-refusal").slideDown();
        } else if (/payment|costs/.exec(status) !== null){
            $(".status-payment").slideDown();
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
};

var conditionalFixed = function(id){
    /* Quick hack, probably better solutions out there */
    var elem = $("#"+id),
        top = elem.offset().top,
        left = elem.offset().left,
        height = elem.height(),
        parent = elem.parent(),
        fixed = 1;
    var adjust = function(){
        var scrollTop = $(window).scrollTop();
        threshold = top + parent.height() - 2*height;
        if(fixed > 0  && scrollTop < top) {
            fixed = 0;
            elem.css({"position": "static", "top": "auto", "left": "auto"});
        } else if (fixed !== 1 && (scrollTop > top && scrollTop < threshold)) {
            fixed = 1;
            elem.css({"position": "fixed", "top": "0px", "left": left+"px"});
        }
    };
    $(window).resize(function(){
        fixed = 0;
        elem.css({"position": "static", "top": "auto", "left": "auto"});
        left = elem.offset().left;
        adjust();
    });
    $(window).scroll(adjust);
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
    $("a.toggle").live("click", function(e){
        e.preventDefault();
        var obj = $($(this).attr("href"));
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
        Froide.app.performPublicBodySearch($(this).parent().parent());
    });
    $(".search-public_bodies").keydown(function(e){
        if(e.keyCode === 13){
            e.preventDefault();
            Froide.app.performPublicBodySearch($(this).parent().parent());
        }
    });
    $(".publicbody-search .searchexample").click(function(e){
        e.preventDefault();
        var term = $(this).text();
        var par = $(this).parent().parent();
        par.find(".search-public_bodies").val(term);
        Froide.app.performPublicBodySearch(par.parent());
    });

    $(".search-public_bodies").each(function(i, input){
        if($(input).val() !== ""){
            Froide.app.performPublicBodySearch();
        }
    });

    if (Froide && Froide.url && Froide.url.autocompletePublicBody){
        $(".search-public_bodies").each(function(i, input){
            $(input).autocomplete({
                serviceUrl: Froide.url.autocompletePublicBody,
                minChars: 2,
                onSelect: function(value, data){
                    var li = Froide.app.getPublicBodyResultListItem($(input).parent().parent(), data);
                    Froide.app.selectSearchListItem($(input).parent().parent(), $(li));
                }
            });
        });
    }
});
