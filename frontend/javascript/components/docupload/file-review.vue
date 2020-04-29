<template>
  <div class="text-right">
    <div class="btn-group btn-group-sm" role="group" aria-label="Button group with nested dropdown">
      <button v-if="canApprove" class="btn btn-sm btn-outline-success"
          :disabled="working" @click="approve">
        <i class="fa fa-check"></i>
        {{ i18n.approve }}
      </button>

      <a v-if="canReview && !approved" class="btn btn-sm btn-outline-primary" :href="reviewUrl">
        <i class="fa fa-eye"></i>
        {{ i18n.review }}
      </a>
      <template v-if="hasSubMenu">
        <div class="btn-group-sm" role="group">
          <button :id="'docupload-dropdown-' + attachment.id" type="button" class="btn btn-light dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
          </button>
          <div class="dropdown-menu dropdown-menu-right" :aria-labelledby="'docupload-dropdown-' + attachment.id">

            <a v-if="canReview && approved" class="dropdown-item btn btn-sm btn-dark" :href="reviewUrl">
              <i class="fa fa-paint-brush"></i>
              {{ i18n.redact }}
            </a>

            <button v-if="canDelete" class="dropdown-item"
                :disabled="working" @click="deleteAttachment">
              <i class="fa fa-ban"></i>
              {{ i18n.delete }}
            </button>
            <button v-if="attachment.is_irrelevant && attachment.is_image" class="dropdown-item btn-danger" @click="makeRelevant">
              {{ i18n.makeRelevant }}
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import {Dropdown} from 'bootstrap.native/dist/bootstrap-native-v4.js'

import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'file-review',
  mixins: [I18nMixin],
  props: ['config', 'document'],
  mounted () {
    if (this.hasSubMenu) {
      new Dropdown(document.getElementById('docupload-dropdown-' + this.attachment.id))
    }
  },
  computed: {
    attachment () {
      return this.document.attachment
    },
    hasAttachment () {
      return !!this.document.attachment
    },
    working () {
      return !!this.document.approving || !!this.document.deleting
    },
    canApprove () {
      return !!this.attachment && !this.attachment.approved && this.attachment.can_approve
    },
    canDelete () {
      return !!this.attachment && this.attachment.can_delete && !this.document.approving
    },
    canReview () {
      return !!this.attachment && this.attachment.can_redact
    },
    canOpen () {
      return !this.canApprove
    },
    reviewUrl () {
      return this.config.url.redactAttachment.replace('/0/', `/${this.document.id}/`)
    },
    approved () {
      return this.attachment && this.attachment.approved
    },
    hasSubMenu () {
      return (
        this.canDelete ||
        (this.attachment && this.attachment.is_irrelevant && this.attachment.is_image) ||
        (this.canReview && this.approved)
      )
    }
  },
  methods: {
    approve () {
      this.$emit('docupdated', {
        approving: true
      })
    },
    makeRelevant() {
      this.$emit('makerelevant')
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
