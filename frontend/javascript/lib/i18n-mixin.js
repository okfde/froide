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
          let trans = this[key]
          if (Array.isArray(trans)) {
            if (params.count !== undefined && (params.count > 1 ||
                                               params.count === 0)) {
              return trans[1].replace(VAR, this._replacer(params))
            }
            return trans[0].replace(VAR, this._replacer(params))
          }
          return trans.replace(VAR, this._replacer(params))
        },
        ...(this.config.i18n)
      }
    }
  }
}

export default I18nMixin
