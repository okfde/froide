<template><span class="word"
    :class="{'-redacted': redacted, '-changed': changed}"
    @mouseout="mouseout" @click="redact"
  >{{ word }}</span></template>

<script>
export default {
  name: 'messageredaction-word',
  props: ['word', 'redacted',  'index'],
  data () {
    return {
      changed: false,
    }
  },
  methods: {
    redact () {
      this.changed = true
      this.$emit('redact', this.index)
    },
    mouseout () {
      this.changed = false
    }
  }
}
</script>


<style lang="scss" scoped>
  .word {
    cursor: pointer;
    transition: all 300ms;
  }
  .word:not(.-changed):hover {
    background-color: #000;
    color: #fff;
  }
  .word.-redacted {
    background-color: #ccc;
    color: #000;
  }
  .word.-redacted:not(.-changed):hover {
    background-color: #fafafa;
    color: #000;
  }
</style>
