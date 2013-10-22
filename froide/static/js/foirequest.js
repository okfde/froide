$(function(){
    loggedInCallback = function(data){
        $(".user_data_form").html("<p>"+data.name+" "+data.last_name+"</p>"+
                    "<p>"+data.address+"</p><p>"+data.email+"</p>");
    };


    Froide.cachedLaw = {
        letter_start_form: $('#letter_start').html(),
        letter_end_form: $('#letter_end').html(),
        description_markdown: $('#law-description-text').html()
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


    $(document).on("publicBodyChosen", ".foirequest .public_body-chooser", function(e){
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
        $('#id_full_text').change(function(e){
            if (!combinedLetter) {
                combinedLetter = $('#letter_start').text() +
                    '\n\n\n' +$('#letter_end').text();
            }
            var checked = $(this).prop('checked');
            var body = $('#id_body').val();

            $('#letter_start').toggle(!checked);
            $('#letter_complete_end').toggle(!checked);

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

    $("form.foirequest").submit(function(e){
        $("#send-request-button").attr("disabled", "disabled");
    });

    if (publicBodyPrefilled){
        publicBodyChosen();
    }
    else if($(".foirequest input[name='public_body']:checked").length > 0){
        $(".foirequest .public_body-chooser").trigger("publicBodyChosen");
    }
    $(document).on("change", ".foirequest input[name='public_body']", function(e){
        $(".foirequest .public_body-chooser").trigger("publicBodyChosen");
    });
    // $("#option-newpublicbody").change(function(e){
    //     $(".foirequest .public_body-chooser").trigger("publicBodyChosen");
    // });
    // $("#option-emptypublicbody").change(function(e){
    //     $(".foirequest .public_body-chooser").trigger("publicBodyChosen");
    // });
});
