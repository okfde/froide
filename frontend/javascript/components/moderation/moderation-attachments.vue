<template>
  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>{{ i18n.name }}</th>
          <th class="action-column">
            {{ i18n.action }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="att in attachmentsList" :key="att.id">
          <td>
            <a :href="att.url" target="_blank">
              {{ att.name }}
            </a>
          </td>
          <td>
            <a :href="att.redactUrl" class="btn btn-dark" target="_blank">
              {{ i18n.redact }}
            </a>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
const getUrl = (templ, att) => {
  return templ
    .replace(/\/0\//, `/${att.belongs_to__request__slug}/`)
    .replace(/\/1\//, `/${att.belongs_to_id}/`)
    .replace(/\/2/, `/${att.name}`)
}

const getRedactionUrl = (templ, att) => {
  return templ
    .replace(/\/0\//, `/${att.belongs_to__request__slug}/`)
    .replace(/\/1\//, `/${att.id}/`)
}

export default {
  name: 'ModerationAttachments',
  props: {
    config: {
      type: Object,
      required: true
    },
    attachments: {
      type: Array,
      required: true
    }
  },
  computed: {
    i18n() {
      return this.config.i18n
    },
    attachmentsList() {
      return this.attachments.map((att) => {
        att.url = getUrl(this.config.url.show_attachment, att)
        att.redactUrl = getRedactionUrl(this.config.url.redact_attachment, att)
        return att
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
