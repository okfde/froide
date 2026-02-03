<template>
  <div class="my-4">
    <!-- TODO empty publicbody causes a nondescript form error (in messages), but does not show up as form error,
      and does not show up as invalid here, either -->
    <ReviewRequestLine
      v-if="!hidePublicbodyChooser"
      :step="STEPS.SELECT_PUBLICBODY"
      :i18n="i18n"
      :title="i18n.publicbody"
      :invalid="needCorrectionPublicbody"
    >
      <template #contents>
        <span v-if="!hasPublicbodies" class="text-danger">{{ i18n.none }}</span>
        <ReviewPublicbody
          v-else
          :config="config"
          :pb-scope="pbScope"
          :multi-request="multiRequest"
        />
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      :i18n="i18n"
      :title="i18n.subject"
      :invalid="needCorrectionSubject"
      :step="STEPS.WRITE_REQUEST"
      :contents="subject || i18n.subject"
    />

    <ReviewRequestLine
      :i18n="i18n"
      :title="i18n.requestBody"
      :invalid="needCorrectionBody"
      :step="STEPS.WRITE_REQUEST"
    >
      <template #contents>
        <div>
          <div v-if="fullText">
            <div
              class="body-text review-body-text"
              :class="{ 'text-danger': needCorrectionBody }"
            >
              <span v-text="body" /><br />
              <span v-text="letterSignatureName" />
            </div>
          </div>
          <div v-else>
            <div
              class="body-text review-body-text"
              :class="{ 'text-danger': needCorrectionBody }"
            >
              <span>{{ letterStart }}</span>
              <span class="highlight"><br />{{ body }}</span>
              <span><br /><br />{{ letterEnd }}</span>
            </div>
          </div>
        </div>
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="needCorrectionConfirm"
      :i18n="i18n"
      :title="i18n.request"
      :invalid="needCorrectionConfirm"
      :contents="i18n.notConfirmed"
      :step="STEPS.WRITE_REQUEST"
    />

    <ReviewRequestLine
      v-if="!hidePublic"
      :i18n="i18n"
      :title="i18n.visibility"
      :step="STEPS.REQUEST_PUBLIC"
    >
      <template #contents>
        {{ requestPublic === 'True' ? i18n.publishNow : i18n.publishLater }}
        <a
          v-if="config.url.helpRequestPublic"
          :href="config.url.helpRequestPublic"
          @click.prevent="
            $emit('onlinehelpClick', config.url.helpRequestPublic)
          "
          >{{ i18n.help }}</a
        >
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="!user.id"
      :i18n="i18n"
      :title="i18n.privacy"
      :step="STEPS.CREATE_ACCOUNT"
    >
      <template #contents>
        <span
          v-html="
            user.private === 'True' ? i18n.nameRedact : i18n.namePlainText
          "
        />
        <!-- TODO
        <a
          href="#"
          @click.prevent="$emit('onlinehelpClick', { content: i18n.TODO })"
          >{{ i18n.help }}</a>
        -->
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="!user.id"
      :i18n="i18n"
      :title="i18n.name"
      :invalid="needCorrectionUser"
      :step="STEPS.CREATE_ACCOUNT"
    >
      <template #contents>
        <span :class="{ 'text-danger': !user.first_name }">
          {{ user.first_name || i18n.yourFirstName }}
        </span>
        <span
          :class="{ 'text-danger': !user.last_name }"
          style="margin-left: 1ch"
        >
          {{ user.last_name || i18n.yourLastName }}
        </span>
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="!user.id"
      :i18n="i18n"
      :title="i18n.email"
      :invalid="needCorrectionEmail"
      :step="STEPS.CREATE_ACCOUNT"
    >
      <template #contents>
        <span :class="{ 'text-danger': needCorrectionEmail }">
          {{ user.email || i18n.email }}
        </span>
        {{ i18n.notSentToPb }}
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      :i18n="i18n"
      :title="i18n.address"
      :invalid="needCorrectionAddress"
      :step="user.id ? STEPS.WRITE_REQUEST : STEPS.CREATE_ACCOUNT"
    >
      <template #contents>
        <div
          style="white-space: pre-line"
          :class="{ 'text-danger': needCorrectionAddress }"
        >
          {{ user.address || '—' }}
        </div>
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="needCorrectionTerms"
      :i18n="i18n"
      :title="i18n.terms"
      :invalid="needCorrectionTerms"
      :contents="i18n.notAgreed"
      :step="STEPS.CREATE_ACCOUNT"
    />

    <UserConfirmation :i18n="i18n" :form="userForm" />

    <div class="mt-4">
      <button
        id="send-request-button"
        type="submit"
        class="btn btn-primary me-2 mb-3"
        :disabled="needCorrection"
        @click.prevent="$emit('submit')"
      >
        <i class="fa fa-send" aria-hidden="true" />
        {{ i18n.submitRequest }}
      </button>
      <button
        v-if="user.id && showDraft"
        type="submit"
        class="btn btn-secondary mb-3"
        name="save_draft"
        value="true"
        :disabled="needCorrection"
        @click="$emit('savedraft')"
      >
        <i class="fa fa-save" aria-hidden="true" />
        {{ i18n.saveAsDraft }}
      </button>
    </div>
  </div>
</template>

<script>
import LetterMixin from './lib/letter-mixin'

import ReviewPublicbody from './review-publicbody.vue'
import ReviewRequestLine from './review-request-line.vue'
import UserConfirmation from './user-confirmation'

import { mapGetters, mapMutations } from 'vuex'

import { SET_STEP, STEPS } from '../../store/mutation_types'

export default {
  name: 'ReviewRequest',
  mixins: [LetterMixin],
  components: {
    ReviewRequestLine,
    ReviewPublicbody,
    UserConfirmation
  },
  emits: ['submit', 'onlinehelpClick', 'savedraft'],
  props: {
    i18n: {
      type: Object,
      required: true
    },
    config: {
      type: Object,
      required: true
    },
    pbScope: {
      type: String,
      required: true
    },
    userForm: {
      type: Object,
      required: true
    },
    requestForm: {
      type: Object,
      required: true
    },
    defaultLaw: {
      type: Object,
      default: null
    },
    multiRequest: {
      type: Boolean,
      required: true
    },
    fullText: {
      type: Boolean,
      required: true
    },
    hidePublic: {
      type: Boolean,
      required: true
    },
    hidePublicbodyChooser: {
      type: Boolean,
      required: true
    },
    showDraft: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      STEPS
    }
  },
  computed: {
    needCorrection() {
      return (
        this.needCorrectionUser ||
        this.needCorrectionEmail ||
        this.needCorrectionPublicbody ||
        this.needCorrectionSubject ||
        this.needCorrectionBody ||
        this.needCorrectionAddress
      )
    },
    needCorrectionUser() {
      return this.hasFormErrorsUser || this.userValid === false
    },
    needCorrectionTerms() {
      return this.hasFormErrorsUserTerms || this.termsValid === false
    },
    hasFormErrorsUser() {
      // note UserTerms here
      return (
        this.hasFormErrorsFirstName ||
        this.hasFormErrorsLastName ||
        this.hasFormErrorsUserTerms
      )
    },
    hasFormErrorsFirstName() {
      if (this.userForm?.fields.first_name?.value !== this.user.first_name)
        return
      return 'first_name' in this.userForm.errors
    },
    hasFormErrorsLastName() {
      if (this.userForm?.fields.last_name?.value !== this.user.last_name) return
      return 'last_name' in this.userForm.errors
    },
    hasFormErrorsUserTerms() {
      if (this.userForm?.fields.terms?.value !== this.user.terms) return
      return 'terms' in this.userForm.errors
    },
    needCorrectionPublicbody() {
      // TODO are pb-less requests allowed? drafts?
      // return !this.hasPublicbodies?
      return false
    },
    needCorrectionEmail() {
      return this.hasFormErrorsEmail || this.emailValid === false
    },
    hasFormErrorsEmail() {
      if (this.userForm?.fields.user_email?.value !== this.user.email) return
      return 'email' in this.userForm.errors
    },
    needCorrectionSubject() {
      return this.hasFormErrorsSubject || this.subjectValid === false
    },
    hasFormErrorsSubject() {
      // ignore form errors if value changed
      if (this.requestForm?.fields.subject.value !== this.subject) return
      return 'subject' in this.requestForm.errors
    },
    needCorrectionBody() {
      return this.hasFormErrorsBody || this.bodyValid === false
    },
    hasFormErrorsBody() {
      // TODO
      // TODO? the calculation is different than the validation in RequestForm,
      //   where *any* change explicitly allows re-submitting -- even an effectively unchanged value
      //   (which is made impossible here, contradictingly)
      //   maybe need to move was...changed into store...
      if (this.requestForm?.fields.body.value !== this.body) return
      return 'body' in this.requestForm.errors
    },
    needCorrectionConfirm() {
      return this.confirmValid === false
    },
    needCorrectionAddress() {
      return this.hasFormErrorsAddress || this.addressValid === false
    },
    hasFormErrorsAddress() {
      if (this.userForm?.fields.address.value !== this.user.address) return
      return 'address' in this.userForm.errors
    },
    publicBody() {
      return this.getPublicBodyByScope(this.pbScope)
    },
    publicBodies() {
      return this.getPublicBodiesByScope(this.pbScope)
    },
    hasPublicbodies() {
      return this.publicBodies.length > 0
    },
    ...mapGetters([
      'user',
      'userValid',
      'subject',
      'subjectValid',
      'body',
      'bodyValid',
      'emailValid',
      'addressValid',
      'termsValid',
      'confirmValid',
      'getPublicBodyByScope',
      'getPublicBodiesByScope',
      'requestPublic'
    ])
  },
  methods: {
    ...mapMutations({
      setStep: SET_STEP
    })
  }
}
</script>

<style lang="scss" scoped>
@import '../../../styles/variables';

.review-body-text {
  color: var(--#{$prefix}body-color);
  background-color: var(--#{$prefix}body-bg);
  border: 1px dashed #777;
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
