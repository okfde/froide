const VAR = new RegExp(/\$\{(\w+)\}/g)

var I18nMixin = {
  computed: {
    i18n () {
      return {
        _replacer (params) {
          return (match, p1, offset, string) => {
            return params[p1]
          }
        },
        _ (key, params) {
          return this[key].replace(VAR, this._replacer(params))
        },
        ...this.config.i18n
      }
    }
  }
}

export default I18nMixin
