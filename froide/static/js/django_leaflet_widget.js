(function() {
    const config = document.currentScript.dataset
    window.addEventListener("map:init", function (event) {
        const mapId = config.mapid
        if (event.detail.id !== mapId) {
            return;
        }
        const map = event.detail.map;
        const options = {
            fieldid: config.fieldid,
            modifiable: config.modifiable,
            geometry_field_class: config.geometryfieldclass.split(".").pop(),
            geom_type: config.geomtype,
            srid: config.srid,
            field_store_class: window.L[config.fieldstoreclass.split(".").pop()],
        }
        const layer = new window.L[options.geometry_field_class](options)
        layer.addTo(map);
    })
}());
