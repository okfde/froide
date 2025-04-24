<template>
  <div class="redaction-area">
    <div class="content-text">
      <template v-for="word in words">
        <message-redaction-word
          v-if="!word.separator"
          :key="word.index"
          :word="word.word"
          :redacted="word.redacted"
          :index="word.index"
          :blocked="word.blocked"
          @redact="redact"
        />
        <template v-else>{{ word.word }}</template>
      </template>
    </div>
    <input type="hidden" :name="fieldName" :value="serializedValue" />
    <input type="hidden" :name="fieldName + '_length'" :value="words.length" />
  </div>
</template>

<script>
import MessageRedactionWord from './message-redaction-word.vue'

// const SPLITTER = /[^\w\u00C0-\u00FF\-@/\.\:]/g
// eslint-disable-next-line no-control-regex
const SPLITTER = /[\u0000-\u002C\u003B-\u003F\u005B-\u005e\u0060\u007B-\u007E]/g

function getChunks(redactedParts, blockPattern) {
  let counter = 0
  const chunks = []
  for (const redactedPart of redactedParts) {
    let result
    let partIndex = 0
    const part = redactedPart[1]
    while ((result = SPLITTER.exec(part))) {
      if (result.index > partIndex) {
        const word = part.substring(partIndex, result.index)
        chunks.push({
          separator: false,
          redacted: redactedPart[0],
          index: counter,
          word: word,
          blocked: blockPattern.test(word)
        })
        counter += 1
      }
      chunks.push({
        separator: true,
        redacted: false,
        index: counter,
        word: result[0],
        blocked: false
      })
      counter += 1
      partIndex = result.index + 1
    }
    if (partIndex < part.length) {
      const word = part.substring(partIndex, part.length + 1)
      chunks.push({
        separator: false,
        redacted: redactedPart[0],
        index: counter,
        word: word,
        blocked: blockPattern.test(word)
      })
      counter += 1
    }
  }
  return chunks
}

export default {
  name: 'MessageRedactionField',
  props: {
    redactedParts: {
      type: Array,
      required: true
    },
    fieldName: {
      type: String,
      required: true
    },
    blockedPatterns: {
      type: Array,
      default: () => []
    }
  },
  components: {
    MessageRedactionWord
  },
  data() {
    return {
      words: []
    }
  },
  mounted() {
    let blockPattern
    if (this.blockedPatterns.length === 0) {
      blockPattern = /a^/
    } else {
      blockPattern = new RegExp(this.blockedPatterns.join('|'), 'g')
    }
    this.words = getChunks(this.redactedParts, blockPattern)
  },
  computed: {
    serializedValue() {
      const redacted = []
      for (const [i, word] of this.words.entries()) {
        if (word.redacted) {
          redacted.push('' + i)
        }
      }
      return redacted.join(',')
    }
  },
  methods: {
    redact(index) {
      this.words[index].redacted = !this.words[index].redacted
    }
  }
}
</script>

<style lang="scss" scoped>
.redaction-area {
  border: 1px solid gray;
  padding: 3px;
  max-height: 60vh;
  overflow-y: auto;
}
.content-text {
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
