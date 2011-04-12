$(function(){
    $(".hidden-div-wrapper");
    $("a.target-new").click(function(e){
        e.preventDefault();
        window.open($(this).attr("href"));
    });
    $("a.target-small").click(function(e){
        e.preventDefault();
        var win = window.open($(this).attr("href"), "",
                'height=500,width=800,resizable=yes,scrollbars=yes');
        win.focus();
    });
});
