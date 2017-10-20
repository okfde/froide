<template>
  <div class="modal fade" id="step-review" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            {{ i18n.reviewTitle }}
          </h5>
          <button type="button" class="close" data-dismiss="modal" aria-label="Close">
             <span aria-hidden="true">&times;</span>
           </button>
        </div>
        <div class="modal-body">
          <dl class="message-meta">
            <dt>{{ i18n.reviewFrom }}</dt>
            <dd>
              {{ user.first_name }} {{ user.last_name }} &lt;{{ user.email }}&gt;
            </dd>
            <dt>{{ i18n.reviewTo }}</dt>
            <dd v-if="publicbodies.length > 1">
              {{ publicbodies.length }} {{ i18n.reviewPublicbodies }}
            </dd>
            <dd v-else>
              {{ publicbody.name }}
            </dd>
            <dt>{{ i18n.subject }}</dt>
            <dd>
              {{ subject }}
            </dd>
          </dl>
          <div class="body-text review-body-text"><span>{{ letterStart }}</span><span class="highlight">{{ body }}</span><span>{{ letterEnd }}</span></div>
          <ul>
            <li>{{ i18n.reviewSpelling }}</li>
            <li>{{ i18n.reviewPoliteness }}</li>
            <li v-for="error in errors"></li>
          </ul>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-dismiss="modal">
            <i class="fa fa-edit" aria-hidden="true"></i>
            {{ i18n.reviewEdit }}
          </button>
          <button type="submit" id="send-request-button" class="btn btn-primary">
            <i class="fa fa-send" aria-hidden="true"></i>
            {{ i18n.submitRequest }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {mapGetters} from 'vuex'

export default {
  name: 'review-request',
  props: ['i18n', 'pbScope'],
  data () {
    return {
      errors: []
    }
  },
  computed: {
    letterStart () {
      if (this.defaultLaw === null) {
        return ''
      }
      return this.defaultLaw.letter_start + '\n\n'
    },
    letterEnd () {
      if (this.defaultLaw === null) {
        return ''
      }
      return `\n\n${this.defaultLaw.letter_end}\n${this.user.first_name} ${this.user.last_name}`
    },
    publicbody () {
      return this.getPublicBodyByScope(this.pbScope)
    },
    publicbodies () {
      return this.getPublicBodiesByScope(this.pbScope)
    },
    ...mapGetters([
      'getPublicBodiesByScope', 'getPublicBodyByScope', 'subject', 'body', 'user', 'defaultLaw'
    ])
  }
}
</script>

<style>
  .review-body-text {
    color: #333;
    border: 1px solid #333;
    padding: 0.25em;
    height: 14em;
    max-height: 14em;
    overflow: auto;
  }
</style>
