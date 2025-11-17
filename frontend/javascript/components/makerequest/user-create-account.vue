<template>
  <div>
    <h2>Account anlegen</h2><!-- TODO i18n -->

    <p>
      {{ i18n.doYouAlreadyHaveAccount }}<br/>
      <slot name="loginlink"></slot>
    </p>

    <p><small>{{ i18n.thisFormRemembers }}</small></p>

    <UserRegistration
      ref="userRegistration"
      :form="userForm"
      :user-form="userForm"
      :config="config"
      :default-law="defaultLaw"
      v-model:initial-first-name="firstName"
      v-model:initial-last-name="lastName"
      v-model:initial-email="email"
      />
    <!-- TODO: password, see UserRegistration stub -->

    <UserAddress
      ref="userAddress"
      :i18n="i18n"
      :form="userForm"
      :config="config"
      :address-help-text="userForm.fields.address.help_text"
      />

    <template v-if="config.settings.user_can_hide_web">
      <h3 class="fs-6">Privatsphäre</h3><!-- TODO i18n -->
      <!-- TODO test online help -->
      <UserPublic
        x-v-if="!user.id"
        :user-form="userForm"
        :config="config"
        v-model:initial-private="userPrivate"
        @onlinehelp-click="$emit('onlinehelpClick', $event)"
        />
      <h3 class="fs-6">Nutzungsbedingungen</h3><!-- TODO i18n -->
      <UserTerms
        ref="userTerms"
        :form="userForm"
        v-model:initial-terms="terms"
        />
    </template>

    <div class="my-4">
      <!-- TODO: validation of vorname/name -->
      <button
        type="button"
        class="btn btn-primary"
        @click="validateAllNextStep"
        >
        {{ i18n.stepNext }}
      </button>
    </div>
  </div>
</template>

<script>
import UserRegistration from './user-registration'
import UserTerms from './user-terms'
import UserPublic from './user-public.vue'
import UserAddress from './user-address.vue'

import { mapGetters, mapMutations } from 'vuex'

import {
  UPDATE_FIRST_NAME,
  UPDATE_LAST_NAME,
  UPDATE_EMAIL,
  UPDATE_PRIVATE,
} from '../../store/mutation_types'

import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'UserCreateAccount',
  components: {
    UserRegistration,
    UserTerms,
    UserPublic,
    UserAddress,
  },
  mixins: [I18nMixin],
  props: {
    config: {
      type: Object
    },
    userForm: {
      type: Object
    },
  },
  computed: {
    email: {
      get() {
        return this.$store.state.user.email
      },
      set(value) {
        this.updateEmail(value)
      }
    },
    firstName: {
      get() {
        return this.$store.state.user.first_name
      },
      set(value) {
        this.updateFirstName(value)
      }
    },
    lastName: {
      get() {
        return this.$store.state.user.last_name
      },
      set(value) {
        this.updateLastName(value)
      }
    },
    userPrivate: {
      get() {
        return this.$store.state.user.private
      },
      set(value) {
        this.updatePrivate(value)
      }
    },
    ...mapGetters([
      'firstNameValid',
      'lastNameValid',
      'emailValid',
      'addressValid',
      'termsValid',
      'stepCanContinue',
    ])
  },
  methods: {
    validateAllNextStep() {
      // calling the child's method à la Vue3 expose
      this.$refs.userTerms.validate()
      this.$refs.userAddress.validate()
      this.$refs.userRegistration.validateAll()
      if (this.firstNameValid && this.lastNameValid && this.emailValid && this.addressValid && this.termsValid) {
        this.$emit('stepNext')
      }
    },
    ...mapMutations({
      updateFirstName: UPDATE_FIRST_NAME,
      updateLastName: UPDATE_LAST_NAME,
      updateEmail: UPDATE_EMAIL,
      updatePrivate: UPDATE_PRIVATE,
    })
  }
}

</script>