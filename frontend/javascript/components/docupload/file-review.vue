<template>
  <div class="row">
    <div v-if="hasAttachment" class="col-auto mt-1">
      <a v-if="canOpen" :href="attachment.site_url" target="_blank" class="btn btn-sm btn-light mt-1">
        {{ i18n.openAttachmentPage }}
      </a>
      <button v-if="attachment.is_pdf && canPreview" class="btn btn-sm btn-light mt-1" @click="$emit('loadpdf')">
        {{ i18n.loadPreview }}
      </button>
    </div>
    <div class="ml-auto mt-1 col-auto text-right">
      <template v-if="canReview">
        <a v-if="!approved" class="btn btn-sm btn-primary mr-1 mt-1" :href="reviewUrl">
          <i class="fa fa-eye"></i>
          {{ i18n.review }}
        </a>
        <a v-else class="btn btn-sm btn-dark mr-1 mt-1" :href="reviewUrl">
          <i class="fa fa-paint-brush"></i>
          {{ i18n.redact }}
        </a>
      </template>
      <button v-if="canApprove" class="btn btn-sm btn-success mr-1 mt-1"
          :disabled="working" @click="approve">
        <i class="fa fa-check"></i>
        {{ i18n.approve }}
      </button>
      <button v-if="canDelete" class="btn btn-sm btn-outline-danger mt-1"
          :disabled="working" @click="deleteAttachment">
        <i class="fa fa-ban"></i>
        {{ i18n.delete }}
      </button>
    </div>
  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'
import {postData, getData} from '../../lib/api.js'

export default {
  name: 'file-review',
  mixins: [I18nMixin],
  props: ['config', 'document', 'canPreview'],
  computed: {
    attachment () {
      return this.document.attachment
    },
    hasAttachment () {
      return !!this.document.attachment
    },
    working () {
      return this.document.approving || this.document.deleting
    },
    canApprove () {
      return this.attachment && !this.attachment.approved && this.attachment.can_approve
    },
    canDelete () {
      return this.attachment && this.attachment.can_delete && !this.document.approving
    },
    canReview () {
      return this.attachment && this.attachment.can_redact
    },
    canOpen () {
      return !this.canApprove
    },
    reviewUrl () {
      return this.config.url.redactAttachment.replace('/0/', `/${this.document.id}/`)
    },
    approved () {
      return this.attachment && this.attachment.approved
    }
  },
  methods: {
    approve () {
      this.$emit('docupdated', {
        approving: true
      })
    },
    deleteAttachment () {
      const confirm = window.confirm(this.i18n.confirmDelete)
      if (!confirm) {
        return
      }
      this.$emit('docupdated', {
        deleting: true
      })
    }
  },
}
</script>
