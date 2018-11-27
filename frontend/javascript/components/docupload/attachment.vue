<template>
  <div class="document-uploader mb-3">
    <input type="search"/>
    <div class="attachments">
    
    </div>
  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'attachment',
  mixins: [I18nMixin],
  props: ['config', 'attachment'],
  data () {
    return {
    }
  },
  created () {
    this.setConfig(this.config)
  },
  mounted () {
    if (this.defaultsearch && this.searchMeta === null) {
      this.triggerAutocomplete()
    }
  },
  components: {
    // resultList: PBResultList,
  },
  computed: {
    attachments () {
      return this.message.attachments
    },
    settings () {
      return this.config.settings
    }
  },
  methods: {
  }
}
</script>
