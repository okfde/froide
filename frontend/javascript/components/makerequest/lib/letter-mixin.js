const LetterMixin = {
  computed: {
    letterStart() {
      if (this.defaultLaw) {
        return this.defaultLaw.letter_start + '\n'
      } else {
        return (
          this.gettext('Dear Sir or Madam,') +
          '\n\n' +
          this.gettext('Please send me the following information:') +
          '\n'
        )
      }
    },
    letterSignatureName() {
      let name = ''
      if (this.user && (this.user.first_name || this.user.last_name)) {
        name = `${this.user.first_name || ''} ${this.user.last_name || ''}`
      }
      return name.trim()
    },
    letterEndShort() {
      const name = this.letterSignatureName
      return `\n${this.gettext('Kind regards')}\n${name}`
    },
    letterEnd() {
      const name = this.letterSignatureName
      if (!this.defaultLaw) {
        return `${this.gettext('Kind regards')}\n${name}`
      }
      return `${this.defaultLaw.letter_end}\n${name}`
    },
    letterEndNoName() {
      if (!this.defaultLaw) {
        return `${this.gettext('Kind regards')}`
      }
      return `${this.defaultLaw.letter_end}`
    },
    letterSignature() {
      if (!this.user || (!this.user.first_name && !this.user.last_name)) {
        return this.gettext(
          'Please fill out your name below, or in the next step'
        )
      }
      return false
    }
  }
}

export default LetterMixin
