<template>
  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>{{ gettext('Name') }}</th>
          <th>{{ gettext('Message') }}</th>
          <th class="action-column">
            {{ pgettext('action to take in moderation table', 'Action') }}
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
              {{ gettext('to message') }}
            </a>
          </td>
          <td>
            <div class="btn-group-vertical btn-group-sm">
              <a :href="att.redactUrl" class="btn btn-primary" target="_blank">
                {{ gettext('redact') }}
              </a>
              <button
                @click="() => markModerated(att)"
                class="btn btn-dark"
                target="_blank"
              >
                {{ gettext('Mark moderated') }}
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
import { translateMixin } from 'vuepo/vue'

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
  mixins: [translateMixin],
  props: {
    attachments: {
      type: Array,
      required: true
    }
  },
  emits: ['resolved'],
  inject: ['config', 'csrfToken'],
  computed: {
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
        this.csrfToken
      ).then(() => {
        this.$emit('resolved', att)
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
