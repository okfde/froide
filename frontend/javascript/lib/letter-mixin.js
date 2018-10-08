var LetterMixin = {
  computed: {
    letterStart () {
      if (this.defaultLaw) {
        return this.defaultLaw.letter_start + '\n'
      } else {
        return this.i18n.greeting + '\n\n' + this.i18n.defaultLetterStart + '\n'
      }
    },
    letterSignatureName () {
      let name = ''
      if (this.first_name || this.last_name) {
        name = `${this.first_name || ''} ${this.last_name || ''}`
      }
      return name.trim()
    },
    letterEndShort () {
      let name = this.letterSignatureName
      return `\n${this.i18n.kindRegards}\n${name}`
    },
    letterEnd () {
      let name = this.letterSignatureName
      if (!this.defaultLaw) {
        return `${this.i18n.kindRegards}\n${name}`
      }
      return `${this.defaultLaw.letter_end}\n${name}`
    },
    letterEndNoName () {
      if (!this.defaultLaw) {
        return `${this.i18n.kindRegards}`
      }
      return `${this.defaultLaw.letter_end}`
    },
    letterSignature () {
      if (!this.user && (!this.first_name && !this.last_name)) {
        return this.i18n.giveName
      }
      return false
    }
  }
}

export default LetterMixin
