<template>
  <div class="redaction-area">
    <div class="content-text"><message-redaction-word v-for="word in words" :key="word.index"
      :word="word.word"
      :redacted="word.redacted"
      :index="word.index"
      @redact="redact"
    ></message-redaction-word></div>
    <input type="hidden" :name="fieldName" :value="serializedValue">
  </div>
</template>

<script>
import Vue from 'vue'

import {getData} from '../../lib/api.js'

import MessageRedactionWord from './messageredaction-word.vue'

const SPLITTER = /(?=[^\w\u00C0-\u00FF\-@/\.\:])/g

export default {
  name: 'messageredaction-field',
  props: ['redactedParts', 'fieldName'],
  components: {
    MessageRedactionWord
  },
  data () {
    return {
      message: null,
      redactionMap: {},
      words: []
    }
  },
  mounted () {
    let counter = -1
    this.words = this.redactedParts.map((part) => {
      return part[1].split(SPLITTER).map((p) => {
        counter += 1
        if (part[0]) {
          this.redactionMap[counter] = true
        }
        return {
          word: p,
          redacted: part[0],
          index: counter,
        }
      })
    }).flat()

  },
  computed: {
    serializedValue () {
      let redacted = []
      for (let index in this.redactionMap) {
        if (this.redactionMap[index]) {
          redacted.push('' + index)
        }
      }
      return redacted.join(',')
    }
  },
  methods: {
    redact (index) {
      Vue.set(this.redactionMap, index, !this.redactionMap[index])
      Vue.set(this.words[index], 'redacted', this.redactionMap[index])
    }
  }
}
</script>


<style lang="scss">
.redaction-area {
  border: 1px solid gray;
  padding: 3px;
}
</style>
