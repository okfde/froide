var FilterMixin = {
  computed: {
    valueList () {
      if (this.value === null) {
        return []
      }
      if (!this.config.multi) {
        return [this.value]
      }
      return this.value
    },
    hasValue () {
      if (this.value === null) {
        return false
      }
      return !(this.config.multi && this.value.length === 0)
    },
    hasMore () {
      if (!this.searchMeta) { return false }
      return this.searchMeta.next !== null
    }
  },
  methods: {
    removeFilter (itemId) {
      if (this.config.multi) {
        let val = this.value.filter((x) => itemId !== x)
        this.$emit('update', this.config, val)
      } else {
        this.$emit('update', this.config, null)
      }
    }
  }
}

export default FilterMixin
