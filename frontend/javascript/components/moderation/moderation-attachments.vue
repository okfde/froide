<template>
  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>{{ i18n.name }}</th>
          <th>{{ i18n.message }}</th>
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
            <a :href="att.messageUrl" target="_blank">
              {{ i18n.toMessage }}
            </a>
          </td>
          <td>
            <div class="btn-group-vertical btn-group-sm">
              <a :href="att.redactUrl" class="btn btn-primary" target="_blank">
                {{ i18n.redact }}
              </a>
              <button
                @click="() => markModerated(att)"
                class="btn btn-dark"
                target="_blank">
                {{ i18n.markModerated }}
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { postData } from '../../lib/api.js'

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

const getMessageUrl = (templ, att) => {
  return templ.replace(/\/0\//, `/${att.belongs_to_id}/`)
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
        att.messageUrl = getMessageUrl(this.config.url.foimessage, att)
        return att
      })
    }
  },
  methods: {
    markModerated(att) {
      postData(
        getRedactionUrl(this.config.url.mark_attachment_as_moderated, att),
        {},
        this.$root.csrfToken
      ).then(() => {
        const index = this.attachments.findIndex((x) => x.id === att.id)
        if (index !== -1) {
          this.$delete(this.attachments, index)
        }
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.action-column {
  min-width: 120px;
}
</style>
