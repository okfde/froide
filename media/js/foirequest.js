var Froide = Froide || {};

var loggedInCallback;

$(function(){
    var lastPublicBodyQuery = null;
    var currentPublicBodyChoice;
    var publicBodyPrefilled = $("#search-public_bodies").length === 0;

    loggedInCallback = function(data){
        $("#user_data_form").html("<p>"+data.name+" "+data.last_name+"</p>"+
                    "<p>"+data.email+"</p>");
    };

    var performPublicBodySearch = function(){
        $("#search-results").slideDown();
        var query = $("#search-public_bodies").val();
        if (lastPublicBodyQuery === query){
            return;
        }
        $.getJSON(Froide.url.searchPublicBody, {"q": query}, function(results){
            var result, i;
            lastPublicBodyQuery = query;
            $("#search-results .result").remove();
            if (results.length === 0){
                $("#empty-result").show();
                return;
            } else {
                $("#empty-result").hide();
                for(i = 0; i < results.length; i += 1){
                    result = results[i];
                    var li = '<li class="result"><label>';
                    li += '<input type="radio" name="public_body" value="' + result.id + '"/>';
                    li += result.name + '</label> - ';
                    li += Mustache.to_html(Froide.template.publicBodyListingInfo, {url: result.url});
                    li += '</li>';
                    $("#search-results").append(li);
                }
            }
        });
    };
    $("#search-public_bodies").keydown(function(e){
        if(e.keyCode === 13){
            e.preventDefault();
            performPublicBodySearch();
        }
    });

    var populateCheck = function(){
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
                });
            }(currentPublicBodyChoice));
        }

        
    };

    var activateMessage = function(){
        $("#public-body").removeClass("active");
        $("#step-message").slideDown()
            .removeClass("hidden")
            .parent().addClass("active");
    };


    $(".foirequest input").keydown(function(e){
        if(e.keyCode === 13){
            e.preventDefault();
        }
    });

    var publicBodyChosen = function(){
        currentPublicBodyChoice = $(".foirequest input[name='public_body']:checked").val();
        populateCheck();
        activateMessage();
    };

    $(".foirequest input[name='public_body']").live("change", function(e){
        if ($("#option-newpublicbody").attr("checked")){
            $("#new-public_body").slideDown();
        } else {
            $("#new-public_body").slideUp();
        }
        publicBodyChosen();
    });

    $("#review-button").click(function(){
        $("#write-request").removeClass("active");
        $("#step-review").slideDown()
            .removeClass("hidden")
            .parent().addClass("active");
    });

    if (publicBodyPrefilled){
        publicBodyChosen();
    }
    if($("#search-public_bodies").val() !== ""){
        performPublicBodySearch();
    }
    if($(".foirequest input[name='public_body']:checked").length > 0){
        publicBodyChosen();
    }
    if ($("#option-newpublicbody").attr("checked")){
        $("#new-public_body").slideDown();
    }
});
