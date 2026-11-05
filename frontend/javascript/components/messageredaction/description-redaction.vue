<template>
  <div>
    <template v-if="request">
      <div v-if="request.description" class="mb-3">
        <h5>
          {{ gettext('Description') }}
        </h5>
        <div>
          <MessageRedactionField
            field-name="description"
            :redacted-parts="request.redacted_description"
          ></MessageRedactionField>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="text-center">
        <h3>
          {{ gettext('Message is loading...') }}
        </h3>
        <div class="spinner-border" role="status"></div>
      </div>
    </template>
  </div>
</template>

<script>
import { getData } from '../../lib/api.js'
import { translateMixin } from 'vuepo/vue'

import MessageRedactionField from './message-redaction-field.vue'

export default {
  name: 'MessageRedaction',
  mixins: [translateMixin],
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
  }
}
</script>
