<template><span>{{ separator }}<span @click="redact" class="word" :class="{'-redacted': redacted}">{{ realWord }}</span></span></template>

<script>

import {getData} from '../../lib/api.js'

const SPACE = /\s/g

export default {
  name: 'messageredaction-word',
  props: ['word', 'redacted', 'index'],
  data () {
    return {
      message: null
    }
  },
  mounted () {
    
  },
  computed: {
    startsSpace () {
      return SPACE.test(this.word[0])
    },
    separator () {
      if (this.startsSpace) {
        return this.word[0]
      }
      return ''
    },
    realWord () {
      if (this.startsSpace) {
        return this.word.substring(1)
      }
      return this.word
    }
  },
  methods: {
    redact () {
      this.$emit('redact', this.index)
    }
  }
}
</script>


<style lang="scss" scoped>
  .word {
    cursor: pointer;
  }
  .word:hover {
    background-color: #000;
    color: #fff;
  }
  .word.-redacted {
    background-color: #bbb;
    color: #000;
  }
  .word.-redacted:hover {
    background-color: #fff;
    color: #000;
  }
</style>
