<template>
  <div>
    <template v-if="request">
      <div v-if="request.description" class="mb-3">
        <h5>
          {{ i18n.description }}
        </h5>
        <div>
          <message-redaction-field
            field-name="description"
            :redacted-parts="
              request.redacted_description
            "></message-redaction-field>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="text-center">
        <h3>
          {{ i18n.messageLoading }}
        </h3>
        <div class="spinner-border" role="status"></div>
      </div>
    </template>
  </div>
</template>

<script>
import { getData } from '../../lib/api.js'

import MessageRedactionField from './message-redaction-field.vue'

export default {
  name: 'MessageRedaction',
  props: {
    config: {
      type: Object,
      required: true
    },
    requestUrl: {
      type: String,
      required: true
    }
  },
  components: {
    MessageRedactionField
  },
  provide() {
    return {
      config: this.config
    }
  },
  data() {
    return {
      request: null
    }
  },
  created() {
    getData(this.requestUrl).then((request) => {
      this.request = request
    })
  },
  computed: {
    i18n() {
      return this.config.i18n
    }
  }
}
</script>
