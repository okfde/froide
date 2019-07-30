<template>
  <div>
    <template v-if="message">
      <div v-if="message.subject" class="row mb-3">
        <div class="col-md-3">
          <h5>{{ i18n.subject }}</h5>
        </div>
        <div class="col-md-9">
          <message-redaction-field
            field-name="subject"
            :redacted-parts="message.redacted_subject"
          ></message-redaction-field>
        </div>
      </div>
      <div v-if="message.content" class="mb-3">
        <h5>
          {{ i18n.message }}
        </h5>
        <div>
          <message-redaction-field
            field-name="content"
            :redacted-parts="message.redacted_content"
          ></message-redaction-field>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="text-center">
        <h3>
          {{ i18n.messageLoading }}
        </h3>
        <div class="spinner-border" role="status">
        </div>
      </div>
    </template>
  </div>
</template>

<script>

import {getData} from '../../lib/api.js'

import MessageRedactionField from './messageredaction-field.vue'

export default {
  name: 'messageredaction',
  props: ['config', 'messageUrl'],
  components: {
    MessageRedactionField
  },
  data () {
    return {
      message: null
    }
  },
  created () {
    getData(this.messageUrl).then((message) => {
      this.message = message
    })
  },
  computed: {
    i18n () {
      return this.config.i18n
    },
  }
}
</script>


<style lang="scss">

</style>
