<template>
  <div class="modal-mask" id="step-review" @click.self="close">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            {{ i18n.reviewTitle }}
          </h5>
          <button type="button" class="close" aria-label="Close" @click="close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <dl class="message-meta">
            <dt :class="{'text-danger': !userValid}">{{ i18n.reviewFrom }}</dt>
            <dd :class="{'text-danger': !userValid}">
              {{ user.first_name }} {{ user.last_name }} &lt;{{ user.email }}&gt;
            </dd>
            <dt>{{ i18n.reviewTo }}</dt>
            <dd v-if="publicBodies.length > 1">
              {{ publicBodies.length }} {{ i18n.reviewPublicbodies }}
            </dd>
            <dd v-else-if="publicBody">
              {{ publicBody.name }}
            </dd>
            <dd v-else>
              -
            </dd>
            <dt :class="{'text-danger': !subjectValid}">{{ i18n.subject }}</dt>
            <dd :class="{'text-danger': !subjectValid}">
              {{ subject }}
            </dd>
          </dl>
          <div v-if="fullText">
            <div class="body-text review-body-text">{{ body }}
{{ letterSignatureName }}</div>
          </div>
          <div v-else>
            <div class="body-text review-body-text"><span>{{ letterStart }}</span>
  <span class="highlight">
{{ body }}
</span>
  <span>
{{ letterEnd }}</span></div>
          </div>
          <ul class="review-hints">
            <li>{{ i18n.reviewSpelling }}</li>
            <li>{{ i18n.reviewPoliteness }}</li>
            <li v-for="error in errors" :key="error" class="error">
              {{ error }}
            </li>
          </ul>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn" :class="{ 'btn-secondary': canSend, 'btn-primary': !canSend }" @click="close">
            <i class="fa fa-edit" aria-hidden="true"></i>
            {{ i18n.reviewEdit }}
          </button>
          <button v-if="canSend" type="submit" id="send-request-button" class="btn btn-primary">
            <i class="fa fa-send" aria-hidden="true"></i>
            {{ i18n.submitRequest }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import LetterMixin from './lib/letter-mixin'

function erx (text) {
  return text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&')
}

export default {
  name: 'review-request',
  props: ['i18n',
    'publicbodies',
    'user',
    'defaultLaw',
    'subject',
    'body',
    'fullText'
  ],
  mixins: [LetterMixin],
  computed: {
    canSend () {
      return this.user.id || !this.hasErrors
    },
    hasErrors () {
      return this.errors.length > 0
    },
    userValid () {
      return this.user.first_name && this.user.last_name && this.user.email
    },
    subjectValid () {
      return this.subject && this.subject.length > 0
    },
    errors () {
      let errors = []
      if (!this.subjectValid) {
        errors.push(this.i18n.noSubject)
      }
      if (!this.body || this.body.length === 0) {
        errors.push(this.i18n.noBody)
      }
      let needles = []
      if (!this.fullText) {
        needles = [
          ...needles,
          [
            new RegExp(erx(this.i18n.greeting), 'gi'),
            this.i18n.dontAddGreeting
          ],
          [
            new RegExp(erx(this.i18n.kindRegards), 'gi'),
            this.i18n.dontAddClosing
          ]
        ]
      }

      if (this.userRegex) {
        needles.push([this.userRegex, this.i18n.dontInsertName])
      }

      needles.forEach((params) => {
        if (params[0].test(this.body)) {
          errors.push(params[1])
        }
      })

      return errors
    },
    userRegex () {
      let regex = []
      if (this.user.first_name && this.user.last_name) {
        regex.push(
          erx(`${this.user.first_name} ${this.user.last_name}`)
        )
      }
      if (this.user.first_name) {
        regex.push(
          erx(this.user.first_name)
        )
      }
      if (this.user.first_name) {
        regex.push(
          erx(this.user.first_name)
        )
      }
      if (regex.length === 0) {
        return null
      }
      return new RegExp(regex.join('|'), 'gi')
    },
    publicBody () {
      return this.publicbodies[0]
    },
    publicBodies () {
      return this.publicbodies
    }
  },
  methods: {
    close () {
      this.$emit('close')
    }
  }
}
</script>

<style lang="scss" scoped>
  @import "../../../styles/variables";

  .modal-mask {
    position: fixed;
    z-index: 9998;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, .5);
    display: flex;
    transition: opacity .3s ease;
  }

  .review-body-text {
    color: #333;
    border: 1px solid #333;
    padding: 0.25em;
    height: 14em;
    max-height: 14em;
    overflow: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
  }
  .review-hints {
    margin-top: 1rem;
    .error {
      color: $red;
    }
  }
</style>
