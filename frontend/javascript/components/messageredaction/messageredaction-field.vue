<template>
  <div class="redaction-area">
    <div class="content-text"><template v-for="word in words"><message-redaction-word 
      v-if="!word.separator"
      :key="word.index"
      :word="word.word"
      :redacted="word.redacted"
      :index="word.index"
      @redact="redact"
    ></message-redaction-word><template v-else>{{ word.word }}</template></template></div>
    <input type="hidden" :name="fieldName" :value="serializedValue">
    <input type="hidden" :name="fieldName + '_length'" :value="words.length">
  </div>
</template>

<script>
import Vue from 'vue'

import {getData} from '../../lib/api.js'

import MessageRedactionWord from './messageredaction-word.vue'

const SPLITTER = /[^\w\u00C0-\u00FF\-@/\.\:]/g

function getChunks(redactedParts) {
  let counter = 0
  let chunks = []
  for (let redactedPart of redactedParts) {
    let result
    let partIndex = 0
    let part = redactedPart[1]
    while (result = SPLITTER.exec(part)) {
      if (result.index > partIndex) {
        chunks.push({
          separator: false,
          redacted: redactedPart[0],
          index: counter,
          word: part.substring(partIndex, result.index)
        })
        counter += 1
      }
      chunks.push({
        separator: true,
        redacted: false,
        index: counter,
        word: result[0]
      })
      counter += 1
      partIndex = result.index + 1
    }
    if (partIndex < part.length) {
      chunks.push({
        separator: false,
        redacted: redactedPart[0],
        index: counter,
        word: part.substring(partIndex, part.length + 1)
      })
      counter += 1
    }

  }
  return chunks
}

export default {
  name: 'messageredaction-field',
  props: ['redactedParts', 'fieldName'],
  components: {
    MessageRedactionWord
  },
  data () {
    return {
      words: []
    }
  },
  mounted () {
    let counter = -1
    this.words = getChunks(this.redactedParts)
  },
  computed: {
    serializedValue () {
      let redacted = []
      for (var i = 0; i < this.words.length; i += 1) {
        if (this.words[i].redacted) {
          redacted.push('' + i)
        }
      }
      return redacted.join(',')
    }
  },
  methods: {
    redact (index) {
      Vue.set(this.words[index], 'redacted', !this.words[index].redacted)
    }
  }
}
</script>


<style lang="scss">
.redaction-area {
  border: 1px solid gray;
  padding: 3px;
  max-height: 60vh;
  overflow-y: auto;
}
</style>
