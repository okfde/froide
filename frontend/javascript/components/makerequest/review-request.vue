<template>
  <div class="my-4">
    <!-- TODO empty publicbody causes a nondescript form error (in messages), but does not show up as form error,
      and does not show up as invalid here, either -->
    <ReviewRequestLine
      v-if="!hidePublicbodyChooser"
      :step="STEPS.SELECT_PUBLICBODY"
      :title="gettext('Public body')"
      :invalid="needCorrectionPublicbody"
    >
      <template #contents>
        <span v-if="!hasPublicbodies" class="text-danger">{{
          gettext('None chosen')
        }}</span>
        <ReviewPublicbody
          v-else
          :config="config"
          :pb-scope="pbScope"
          :multi-request="multiRequest"
        />
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      :title="gettext('Subject')"
      :invalid="needCorrectionSubject"
      :step="STEPS.WRITE_REQUEST"
      :contents="subject || gettext('Subject')"
    />

    <ReviewRequestLine
      :title="gettext('Request body')"
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
      :title="gettext('request')"
      :invalid="needCorrectionConfirm"
      :contents="gettext('Not confirmed')"
      :step="STEPS.WRITE_REQUEST"
    />

    <ReviewRequestLine
      v-if="!hidePublic"
      :title="gettext('Visibility')"
      :step="STEPS.REQUEST_PUBLIC"
    >
      <template #contents>
        {{
          requestPublic === 'True'
            ? gettext('Publish request now')
            : gettext('Publish request later')
        }}
        <a
          v-if="config.url.helpRequestPublic"
          :href="config.url.helpRequestPublic"
          @click.prevent="
            $emit('onlinehelpClick', config.url.helpRequestPublic)
          "
          >{{ gettext('Help') }}</a
        >
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="!user.id"
      :title="gettext('Privacy')"
      :step="STEPS.CREATE_ACCOUNT"
    >
      <template #contents>
        <span
          v-html="
            user.private === 'True'
              ? gettext('My name must be <strong>redacted</strong>')
              : gettext(
                  'My name may appear on the website in <strong>plain text</strong>'
                )
          "
        />
        <!-- TODO online help link -->
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="!user.id"
      :title="gettext('Name')"
      :invalid="needCorrectionUser"
      :step="STEPS.CREATE_ACCOUNT"
    >
      <template #contents>
        <span :class="{ 'text-danger': !user.first_name }">
          {{ user.first_name || gettext('Your first name') }}
        </span>
        <span
          :class="{ 'text-danger': !user.last_name }"
          style="margin-left: 1ch"
        >
          {{ user.last_name || gettext('Your last name') }}
        </span>
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="!user.id"
      :title="gettext('Email')"
      :invalid="needCorrectionEmail"
      :step="STEPS.CREATE_ACCOUNT"
    >
      <template #contents>
        <span :class="{ 'text-danger': needCorrectionEmail }">
          {{ user.email || gettext('Email') }}
        </span>
        {{ gettext('(not sent to public body)') }}
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      :title="gettext('Address')"
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
      :title="gettext('Proof of identity')"
      :step="STEPS.WRITE_REQUEST"
      v-if="user && proofForm"
    >
      <template #contents>
        {{
          hasProofs
            ? gettext('You have provided a proof of your identity')
            : gettext(
                "You're not providing a proof of your identity (only required in rare cases)"
              )
        }}
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="needCorrectionTerms"
      :title="gettext('Terms of Use')"
      :invalid="needCorrectionTerms"
      :contents="gettext('Not agreed')"
      :step="STEPS.CREATE_ACCOUNT"
    />

    <UserConfirmation :form="userForm" />

    <div class="mt-4">
      <button
        id="send-request-button"
        type="submit"
        class="btn btn-primary me-2 mb-3"
        :disabled="needCorrection"
        @click.prevent="$emit('submit')"
      >
        <i class="fa fa-send" aria-hidden="true" />
        {{ gettext('Submit request') }}
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
        {{ gettext('Save as draft') }}
      </button>
    </div>
  </div>
</template>

<script>
import { translateMixin } from 'vuepo/vue'

import LetterMixin from './lib/letter-mixin'

import ReviewPublicbody from './review-publicbody.vue'
import ReviewRequestLine from './review-request-line.vue'
import UserConfirmation from './user-confirmation'

import { mapGetters, mapMutations } from 'vuex'

import { SET_STEP, STEPS } from '../../store/mutation_types'

export default {
  name: 'ReviewRequest',
  mixins: [translateMixin, LetterMixin],
  components: {
    ReviewRequestLine,
    ReviewPublicbody,
    UserConfirmation
  },
  emits: ['submit', 'onlinehelpClick', 'savedraft'],
  props: {
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
    proofForm: {
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
    },
    hasProof: {
      type: Boolean,
      required: true
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
      return 'user_email' in this.userForm.errors
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
      'requestPublic',
      'hasProofs'
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
