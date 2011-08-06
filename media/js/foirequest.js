$(function(){
    var publicBodyPrefilled = $("#search-public_bodies").length === 0;

    loggedInCallback = function(data){
        $("#user_data_form").html("<p>"+data.name+" "+data.last_name+"</p>"+
                    "<p>"+data.email+"</p>");
    };


 
    var letter_start = $('#letter_start').text();
    var letter_end = $('#letter_end').text();

    $(".foirequest input").keydown(function(e){
        if(e.keyCode === 13){
            e.preventDefault();
        }
    });

    var publicBodyChosen = function(){
        Froide.app.publicBodyChosen($(".foirequest input[name='public_body']:checked").val(),
                                    publicBodyPrefilled);
        Froide.app.searchSimilarRequests();
        Froide.app.activateFoiCheck();
    };
    
    $("#continue-foicheck").click(function(e){
        e.preventDefault();
        $("#foicheck-form").slideUp();
        if ($("#option-check_foi_personal").attr("checked")){
            $("#write-request").hide();
            $("#review-and-submit").hide();
            $("#nofoi-personal").slideDown();
            $("#publicbody-link");
        } else if ($("#option-check_foi_opinion").attr("checked")){
            $("#write-request").hide();
            $("#review-and-submit").hide();
            $("#nofoi-opinion").slideDown();
        } else if ($("#option-check_foi").attr("checked")){
            Froide.app.activateMessage();
        }
    });

    var highlightRegex = function(elem, regex){
        elem.html(elem.html().replace(regex, "<em>$&</em>"));
    };
    var i;
    for(i = 0; i < Froide.regex.greetings.length; i += 1){
        highlightRegex($("#letter_start"), Froide.regex.greetings[i]);
    }
    for(i = 0; i < Froide.regex.closings.length; i += 1){
        highlightRegex($("#letter_end"), Froide.regex.closings[i]);
    }


    $(".foirequest input[name='public_body']").live("change", function(e){
        if ($("#option-newpublicbody").attr("checked")){
            $("#new-public_body").slideDown();
        } else {
            $("#new-public_body").slideUp();
        }
        publicBodyChosen();
    });
    
    $("#id_subject").blur(Froide.app.searchSimilarRequests);

    $("#review-button").click(function(){
        Froide.app.performReview();
    });

    $("form.foirequest").submit(function(e){
        $("#send-request-button").attr("disabled", "disabled");
    });

    if (publicBodyPrefilled){
        publicBodyChosen();
    }
    if($("#search-public_bodies").length === 1 && $("#search-public_bodies").val() !== ""){
        Froide.app.performPublicBodySearch();
    }
    if($(".foirequest input[name='public_body']:checked").length > 0){
        publicBodyChosen();
    }
    if ($("#option-newpublicbody").attr("checked")){
        $("#new-public_body").slideDown();
    }
    conditionalFixed("similar-requests-container");
});
