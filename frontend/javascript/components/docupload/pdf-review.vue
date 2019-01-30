<template>
  <div>
    <a v-if="!approved" class="btn btn-sm btn-primary mr-1 d-print-none" :href="reviewUrl">
      <i class="fa fa-paint-brush"></i>
      {{ i18n.review }}
    </a>
    <a v-else class="btn btn-sm btn-dark mr-1 d-print-none" :href="reviewUrl">
      <i class="fa fa-paint-brush"></i>
      {{ i18n.redact }}
    </a>
    <button v-if="canApprove" class="btn btn-sm btn-success" @click="approve">
      <i class="fa fa-check"></i>
      {{ i18n.approve }}
    </button>
  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'
import {postData, getData} from '../../lib/api.js'

export default {
  name: 'pdf-review',
  mixins: [I18nMixin],
  props: ['config', 'document'],
  computed: {
    attachment () {
      return this.document.attachment
    },
    canApprove () {
      return !this.attachment.approved && this.attachment.can_approve
    },
    reviewUrl () {
      return this.config.url.redactAttachment.replace('/0/', `/${this.document.id}/`)
    },
    approveUrl () {
      return this.config.url.approveAttachment.replace('/0/', `/${this.document.id}/`)
    },
    attachmentUrl () {
      return this.config.url.getAttachment.replace('/0/', `/${this.document.id}/`)
    },
    approved () {
      return this.attachment.approved
    }
  },
  methods: {
    approve () {
      postData(this.approveUrl, {}, this.$root.csrfToken).then(() => {
        getData(this.attachmentUrl).then((data) => {
          this.$emit('documentupdated', {
            attachment: data
          })
        })
      })
    }
  },
}
</script>
