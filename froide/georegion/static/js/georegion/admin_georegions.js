(function(){
  const initUrl = '/api/v1/georegion/?id='
  const regions = JSON.parse(document.getElementById('georegions_data').textContent)
  const geoGetter = window.location.hash.indexOf('centroid') !== -1 ? 'centroid' : 'geom'
  const features = []

  window.addEventListener("map:init", function (event) {
    const map = event.detail.map
    const regionIds = []
    for (var reg in regions) {
      regionIds.push('' + reg)
    }
    getData(initUrl + regionIds.join(','), map)

    const button = document.querySelector('#generate-geojson')
    button.addEventListener('click', generateGeoJson)
  });

  function generateGeoJson() {
    const fc = { type: 'FeatureCollection', features: features }
    const blob = new Blob([JSON.stringify(fc)], {
      type: 'application/json',
      name: 'data.geojson'
    })
    const link = document.querySelector('#download-geojson')
    link.download = 'data.geojson'
    link.target = '_blank'
    link.rel = 'noopener'
    link.href = window.URL.createObjectURL(blob)
  }

  function getData(url, map) {
    window
      .fetch(url)
      .then(function (response) {
        return response.json()
      })
      .then(function (data) {
        if (data.meta.next) {
          getData(data.meta.next, map)
        }
        const geoData = data.objects.map(function (x) {
          const feature = {
            type: 'Feature',
            geometry: x[geoGetter],
            properties: {
              pb_id: regions[x.id],
              name: x.name,
              population: x.population,
              kind: x.kind,
              kind_detail: x.kind_detail,
              region_id: x.id
            }
          }
          features.push(feature)

          return feature
        })
        console.log(geoData)
        console.log(geoData.length)
        var layer = L.geoJson(geoData, {
          onEachFeature: (f, l) => {
            l.bindPopup(
              '<pre>' + f.properties.name + ' (' + f.properties.pb_id + ') </pre>'
            )
          },
          style: function () {
            return {
              fillOpacity: 0.9
            }
          }
        })
        layer.addTo(map)
        map.fitBounds(layer.getBounds())
      })
  }
}());
