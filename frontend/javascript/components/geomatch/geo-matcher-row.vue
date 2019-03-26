<template>
  <tr :class="{'loading': georegion.loading }">
    <td>
      <a :href="georegionAdminUrl" target="_blank">
        {{ georegion.name }}
      </a>
    </td>
    <td>{{ georegion.kind_detail }}</td>
    <td>
      <ul v-if="hasLinks">
        <li v-for="link in links" :key="link.id">
          <a :href="link.url" target="_blank">
            {{ link.name }}
          </a>
          (<span v-if="link.categories.length > 0">{{ link.categories[0].name }}</span>)
        </li>
      </ul>
    </td>
    <td>
      <div v-if="georegion.loading" class="spinner-border" role="status">
        <span class="sr-only">Loading...</span>
      </div>
      <ul v-if="hasMatches">
        <li v-for="match in matches" :key="match.id">
          <a :href="match.url" target="_blank">
            {{ match.name }}
          </a>
          (
            <span>{{ match.jurisdiction.name }}</span>,
            <span v-if="match.categories.length > 0">{{ match.categories[0].name }}</span>
          )
          <button @click="connect(match)">Connect</button>
        </li>
      </ul>
      <a v-if="hasMatches" :href="createPublicBodyUrl" target="_blank">
        Create new
      </a>
      -
      <a v-if="!hasLinks" :href="searchPublicBodyUrl" target="_blank">
        Search
      </a>
    </td>
  </tr>
</template>

<script>

export default {
  name: 'geo-matcher-row',
  props: {
    georegion: {
      type: Object
    }
  },
  data () {
    return {
    }
  },
  mounted () {
  },
  computed: {
    links () {
      if (!this.georegion.links){
        return []
      }
      return this.georegion.links.map(this.addPublicBodyAdminUrl)
    },
    matches () {
      if (!this.georegion.matches){
        return []
      }
      return this.georegion.matches.map(this.addPublicBodyAdminUrl)
    },
    hasLinks () {
      if (!this.georegion.links) {
        return false
      }
      return this.georegion.links.length > 0
    },
    hasMatches () {
      if (this.hasLinks) {
        return false
      }
      if (!this.georegion.matches) {
        return true
      }
      return this.georegion.matches.length > 0
    },
    georegionAdminUrl () {
      return this.$root.config.url.georegionAdminUrl.replace(/\/0\//, `/${this.georegion.id}/`)
    },
    createPublicBodyUrl () {
      let name = window.encodeURIComponent(`${this.georegion.kind_detail} ${this.georegion.name}`)
      return `${this.$root.config.url.publicbodyAddAdminUrl}?regions=${this.georegion.id}&name=${name}`
    },
    searchPublicBodyUrl () {
      let name = window.encodeURIComponent(this.georegion.name)
      return `${this.$root.config.url.publicbodyAdminUrl}?q=${name}`
    }
  },
  methods: {
    addPublicBodyAdminUrl (pb) {
      pb.url = this.$root.config.url.publicbodyAdminChangeUrl.replace(/\/0\//, `/${pb.id}/`)
      return pb
    },
    connect (match) {
      this.$emit('connectpublicbody', {
        georegionId: this.georegion.id,
        georegionUrl: this.georegion.resource_uri,
        publicbodyId: match.id,
        publicbody: match,
      })
    }
  }
}
</script>

<style lang="scss" scoped>
  .loading {
    background-color: lightgray;
  }
</style>
