(function() {
    function loadMap(name) {
        const mapElement = document.getElementById(name)
        const optionsElement = document.getElementById(name + '_options')
        const djoptions = JSON.parse(optionsElement.textContent);
        const options = {
            djoptions: djoptions,
            initfunc: loadMap,
            globals: false,
            callback: null
        }

        const map = L.Map.djangoMap(name, options);
        // map.on('load', function() {
        // const event = new CustomEvent("leafletmaploaded", {detail: { map: map, name: name }});
        // mapElement.dispatchEvent(event);
        // });
    }
    const key = 'froide_leafletmapload'
    window[key] = false
    document.addEventListener('DOMContentLoaded', function() {
        if (window[key] === false) {
            window[key] = true
            const maps = document.querySelectorAll('[data-leafletmap]');
            maps.forEach(function(mapElement) {
                const name = mapElement.id.replace(/_options$/, '');
                loadMap(name);
            });
        }
    });
}());
