<template>
  <div>
    <small>{{ document.name }}</small>
    <template v-if="hasAttachment">
      <span v-if="!approved" class="badge badge-warning">
        {{ i18n.notPublic }}
      </span>
      <span v-if="isRedacted" class="badge badge-dark">
        {{ i18n.redacted }}
      </span>

      <span v-if="isProtected" class="badge badge-info" data-toggle="tooltip" data-placement="top" :title="i18n.protectedOriginalExplanation">
        {{ i18n.protectedOriginal }}
      </span>
    </template>
  </div>
</template>


<script>
import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'pdf-header',
  mixins: [I18nMixin],
  props: ['config', 'document'],
  computed: {
    attachment () {
      return this.document.attachment
    },
    hasAttachment () {
      return !!this.document.attachment
    },
    isProtected () {
      return (this.attachment.converted && !this.attachment.approved) || this.attachment.redacted
    },
    isRedacted () {
      return this.attachment.is_redacted
    },
    approved () {
      return this.attachment.approved
    }
  }
}
</script>
