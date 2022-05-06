const VAR = /\$\{(\w+)\}/g

const LANG = document.querySelector('html').lang

const I18nMixin = {
  computed: {
    i18n() {
      return {
        _replacer(params) {
          return (match, p1) => {
            if (p1 === 'count' && params.count >= 1000) {
              return params.count.toLocaleString(LANG)
            }
            return params[p1]
          }
        },
        _(key, params) {
          const trans = this[key]
          if (Array.isArray(trans)) {
            if (
              params.count !== undefined &&
              (params.count > 1 || params.count === 0)
            ) {
              return trans[1].replace(VAR, this._replacer(params))
            }
            return trans[0].replace(VAR, this._replacer(params))
          }
          return trans.replace(VAR, this._replacer(params))
        },
        ...this.config.i18n
      }
    }
  }
}

export default I18nMixin
