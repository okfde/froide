(function(){
    const prefillMap = JSON.parse(document.getElementById('prefill-map').textContent);

    for (const [key, value] of Object.entries(prefillMap)) {
        const element = document.getElementById(key);
        if (element) {
            element.value = value || '';
        }
    }
}())
