/* jshint strict: true, quotmark: false, es3: true */
/* global $: false, Froide: false, Mustache: false */

Froide.app = Froide.app || {};

(function(){
    "use strict";
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

        var htmlEscape = function(s) {
          if (!s) {
            return '';
          }
          return $('<div/>').text(s).html();
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
                text += '<div class="highlight">' + htmlEscape($("#id_body").val()) + "</div>";
            } else {
                text += resolve_forms($('#letter_start').clone());
                text += '\n\n<div class="highlight">' + htmlEscape($("#id_body").val()) + "</div>\n\n";
                text += htmlEscape($('#letter_end').text());
            }
            text += "\n" + htmlEscape(getFullName());
            text += "\n\n" + htmlEscape(getAddress());
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

    window.loggedInCallback = function(data){
        $(".user_data_form").html("<p>"+data.name+" "+data.last_name+"</p>"+
                    "<p>"+data.address+"</p><p>"+data.email+"</p>");
        $('input[name=csrfmiddlewaretoken]').replaceWith(data.csrf_token);
    };

    $(function(){
        Froide.cachedLaw = {
            letter_start_form: $('#letter_start').html(),
            letter_end_form: $('#letter_end').html(),
            description_html: $('#law-description-text').html()
        };

        $(".foirequest input").keydown(function(e){
            if(e.keyCode === 13){
                e.preventDefault();
            }
        });

        var publicBodyPrefilled = $(".foirequest .search-public_bodies").length === 0;

        var publicBodyChosen = function(){
            Froide.app.publicBodyChosen($(".foirequest input[name='public_body']:checked").val(),
                                        publicBodyPrefilled);
            Froide.app.searchSimilarRequests();
            Froide.app.activateFoiCheck();
        };

        $("#continue-foicheck").click(function(e){
            e.preventDefault();
            if ($("#option-check_foi_personal").prop("checked")){
                $("#write-request").hide();
                $("#review-and-submit").hide();
                $("#nofoi-personal").slideDown();
                $("#publicbody-link");
            } else if ($("#option-check_foi_opinion").prop("checked")){
                $("#write-request").hide();
                $("#review-and-submit").hide();
                $("#nofoi-opinion").slideDown();
            } else if ($("#option-check_foi").prop("checked")){
                Froide.app.activateMessage();
            } else {
                $("#select-one-information-kind").show();
                return;
            }
            $("#foicheck-form").slideUp();
        });


        $(document).on("publicBodyChosen", ".foirequest .public_body-chooser", function(){
            $('.foirequest .search-results li').removeClass('active');
            $(".foirequest .search-results input[name='public_body']:checked").parent().parent().addClass('active');
            if ($("#option-newpublicbody").prop("checked")){
                $("#new-public_body").slideDown();
            } else {
                $("#new-public_body").slideUp();
            }
            publicBodyChosen();
        });

        $("#id_subject").blur(Froide.app.searchSimilarRequests);

        (function(){
            var combinedLetter;
            $('#id_full_text').change(function(){
                if (!combinedLetter) {
                    combinedLetter = $('#letter_start').text() +
                        '\n\n\n' +$('#letter_end').text();
                }
                var checked = $(this).prop('checked');
                var body = $('#id_body').val();

                $('#letter_start').toggle(!checked);
                $('#letter_complete_end').toggle(!checked);
                $('#law-select').toggle(checked);

                if (checked && body === '') {
                    $('#id_body').val(combinedLetter);
                } else if(!checked && body === combinedLetter) {
                    $('#id_body').val('');
                }
            });
        }());

        $("#review-button").click(function(){
            Froide.app.performReview();
        });

        $("form.foirequest").submit(function(){
            $("#send-request-button").attr("disabled", "disabled");
        });

        if (publicBodyPrefilled){
            publicBodyChosen();
        }
        else if($(".foirequest input[name='public_body']:checked").length > 0){
            $(".foirequest .public_body-chooser").trigger("publicBodyChosen");
        }
        $(document).on("change", ".foirequest input[name='public_body']", function(){
            $(".foirequest .public_body-chooser").trigger("publicBodyChosen");
        });
        // $("#option-newpublicbody").change(function(e){
        //     $(".foirequest .public_body-chooser").trigger("publicBodyChosen");
        // });
        // $("#option-emptypublicbody").change(function(e){
        //     $(".foirequest .public_body-chooser").trigger("publicBodyChosen");
        // });
    });
}());
