<template>
  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>{{ i18n.name }}</th>
          <th>{{ i18n.lastMessage }}</th>
          <th class="action-column">
            {{ i18n.action }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="req in unclassifiedList" :key="req.id">
          <td>
            <a :href="req.url" target="_blank">
              {{ req.title }}
            </a>
          </td>
          <td>
            {{ new Date(req.last_message).toLocaleString() }}
          </td>
          <td>
            <a
              :href="req.url + '#set-status'"
              class="btn btn-primary btn-sm"
              target="_blank"
            >
              {{ i18n.setStatus }}
            </a>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
const getUrl = (templ, objId) => templ.replace(/0/, objId)

export default {
  name: 'ModerationUnclassified',
  props: {
    unclassified: {
      type: Array,
      required: true
    }
  },
  inject: ['config'],
  computed: {
    i18n() {
      return this.config.i18n
    },
    unclassifiedList() {
      return this.unclassified.map((req) => {
        req.url = getUrl(this.config.url.foirequest, req.id)
        return req
      })
    }
  },
  methods: {}
}
</script>

<style lang="scss" scoped>
.action-column {
  min-width: 120px;
}
</style>
