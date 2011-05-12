var Froide = Froide || {};

var loggedInCallback;

Froide.app = Froide.app || {};

Froide.app.getPublicBodyResultListItem = function(result){
    var li = '<li class="result"><label>';
    li += '<input type="radio" name="public_body" value="' + result.id + '"/> ';
    li += result.name + '</label> - ';
    li += Mustache.to_html(Froide.template.publicBodyListingInfo, {url: result.url});
    li += '</li>';
    return li;
};

Froide.app.selectSearchListItem = function(li){
    var html = '<div class="selected-result">' + li.html() + '</div>';
    $("#public_body-chooser .selected-result").remove();
    $("#search-results").after(html);
    $("#public_body-chooser .selected-result input").attr("checked", "checked");
    $("#search-results").slideUp();

};

Froide.app.performPublicBodySearch = (function(){
    var lastPublicBodyQuery = null;
    return function(){
        var query = $("#search-public_bodies").val();
        if (lastPublicBodyQuery === query){
            $("#search-results").slideDown();
            return;
        }
        $("#search-spinner").fadeIn();
        $("#search-results").hide();
        $.getJSON(Froide.url.searchPublicBody, {"q": query}, function(results){
            var result, i;
            lastPublicBodyQuery = query;
            $("#search-spinner").hide();
            $("#search-results .result").remove();
            if (results.length === 0){
                $("#empty-result").show();
                $("#search-results").show();
                return;
            } else {
                $("#empty-result").hide();
                for(i = 0; i < results.length; i += 1){
                    result = results[i];
                    var li = Froide.app.getPublicBodyResultListItem(result);
                    $("#search-results").append(li);
                }
                $(".result input").change(function(e){
                    var li = $(this).parent().parent();
                    Froide.app.selectSearchListItem(li);
                });
                $("#search-results").slideDown();
            }
        });
    };
}());

Froide.app.performReview = (function(){
    var regex_email = /[^\s]+@[^\.\s]+\.\w+/;
    var no_email = function(str){
        var result = regex_email.exec(str);
        if (result !== null){
            return Froide.template.foundEmail;
        }
    };
    var non_empty = function(str){
        if (str.replace(/\s/g, "").length === 0){
            return true;
        }
    };
    var non_empty_body = function(str){
        if (non_empty(str)){
            return Froide.template.emptyBody;
        }
    };
    var non_empty_subject = function(str){
        if (non_empty(str)){
            return Froide.template.emptySubject;
        }
    };
    var formChecks = {
        "id_subject": [non_empty_subject],
        "id_body": [non_empty_body, no_email]
    };

    var openLightBox = function(){
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
        text = $('#letter_start').text();
        text += '\n<div class="highlight">' + $("#id_body").val() + "</div>";
        text += "\n" + $('#letter_end').text();
        text += getFullName();
        $("#review-text").html(text);
        openLightBox();
    };
}());

Froide.app.publicBodyChosen = (function(){
    return function(currentPublicBodyChoice, publicBodyPrefilled){
        if(publicBodyPrefilled){
            return;
        }
        var list = $("#check-list").html("");
        var query = $("#search-public_bodies").val();
        if(query !== ""){
            list.append(Mustache.to_html(Froide.template.searchInternet,
                    {url: Mustache.to_html(Froide.template.searchEngineUrl,
                    {query: query, domain: ""})}));
        }
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
                        list.append(Mustache.to_html(
                            Froide.template.searchPublicBodyWebsite,
                            {url: Mustache.to_html(
                                Froide.template.searchEngineUrl, 
                                {query: query, domain: result.domain})}
                        ));
                        // TODO: Create law chooser here
                        $("#public-body").append('<input type="hidden" name="law" value="'+result.laws[0].pk+'"/>');
                        $('#letter_start').text(result.laws[0].letter_start);
                        $('#letter_end').text(result.laws[0].letter_end);
                });
            }(currentPublicBodyChoice));
        } else {
            $('#letter_start').text(letter_start);
            $('#letter_end').text(letter_end);
        }
    };
}());

Froide.app.statusSet = (function(){
    return function(){
        $(".status-refusal").hide();
        $(".status-payment").hide();
        var status = $("#id_status").val();
        if (/refus/.exec(status) !== null) {
            $(".status-refusal").slideDown();
        } else if (/payment|costs/.exec(status) !== null){
            $(".status-payment").slideDown();
        }
    };
}());

Froide.app.activateMessage = function(){
    $("#public-body").removeClass("active");
    $("#step-message").slideDown()
        .removeClass("hidden")
        .parent().addClass("active");
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
    $("#search-public_bodies-submit").click(function(e){
        Froide.app.performPublicBodySearch();
    });
    $("#search-public_bodies").keydown(function(e){
        if(e.keyCode === 13){
            e.preventDefault();
            Froide.app.performPublicBodySearch();
        }
    });
    $("#publicbody-search .searchexample").click(function(e){
        e.preventDefault();
        var term = $(this).text();
        $("#search-public_bodies").val(term);
        Froide.app.performPublicBodySearch();
    });
    $("#search-public_bodies").autocomplete({
        serviceUrl: Froide.url.autocompletePublicBody,
        minChars:2,
        onSelect: function(value, data){
            var li = Froide.app.getPublicBodyResultListItem(data);
            Froide.app.selectSearchListItem($(li));
            Froide.app.publicBodyChosen($(".foirequest input[name='public_body']:checked").val(), false);
            Froide.app.activateMessage();
        }
    });
    // $("#search-public_bodies").focus();
});
