<template>
  <span
    class="word"
    :class="{ '-redacted': redacted, '-changed': changed, '-blocked': blocked }"
    @mouseout="mouseout"
    @click="redact"
    :title="title"
    >{{ word }}</span
  >
</template>

<script>
export default {
  name: 'MessageRedactionWord',
  props: {
    word: {
      type: String,
      required: true
    },
    redacted: {
      type: Boolean,
      required: true
    },
    index: {
      type: Number,
      required: true
    },
    blocked: {
      type: Boolean,
      default: false
    }
  },
  emits: ['redact'],
  inject: ['config'],
  data() {
    return {
      changed: false
    }
  },
  computed: {
    title() {
      if (this.blocked) {
        return this.config.i18n.blockedRedaction
      }
      return null
    }
  },
  methods: {
    redact() {
      if (this.blocked) {
        return
      }
      this.changed = true
      this.$emit('redact', this.index)
    },
    mouseout() {
      this.changed = false
    }
  }
}
</script>

<style lang="scss" scoped>
@import '../../../styles/variables';
.word {
  cursor: pointer;
  transition: all 300ms;
}
.word:not(.-changed):hover,
.word.-redacted {
  background-color: var(--redacted);
  color: var(--#{$prefix}body);
}

.word.-redacted:not(.-changed):hover {
  background-color: var(--#{$prefix}body-bg);
  color: var(--#{$prefix}body);
}

.word.-redacted.-blocked {
  &,
  &:hover {
    background-color: var(--redacted);
    color: var(--#{$prefix}secondary);
    cursor: not-allowed;
    user-select: none;
  }
}
</style>
