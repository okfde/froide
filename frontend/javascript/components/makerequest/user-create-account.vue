<template>
  <div>
    <h2>{{ i18n.createAccount }}</h2>

    <p>{{ i18n.createAccountPreamble }}</p>

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
      <h3 class="fs-6">{{ i18n.privacy }}</h3>
      <UserPublic
        :user-form="userForm"
        :config="config"
        v-model:initial-private="userPrivate"
        >
        <slot name="userPublicPreamble"></slot>
      </UserPublic>
    </template>

    <template v-if="config.settings.user_can_claim_vip">
      <h3 class="fs-6">{{ userForm.fields.claims_vip.label }}</h3>
      <UserClaimsVip
        :user-form="userForm"
        v-model:initial-value="userClaimsVip"
        />
    </template>

    <h3 class="fs-6">{{ i18n.terms }}</h3>
    <UserTerms
      ref="userTerms"
      :form="userForm"
      v-model:initial-terms="terms"
      />

    <div class="my-4">
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
import UserClaimsVip from './user-claims-vip.vue'

import { mapGetters, mapMutations } from 'vuex'

import {
  UPDATE_FIRST_NAME,
  UPDATE_LAST_NAME,
  UPDATE_EMAIL,
  UPDATE_PRIVATE,
  UPDATE_CLAIMS_VIP,
} from '../../store/mutation_types'

import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'UserCreateAccount',
  components: {
    UserRegistration,
    UserTerms,
    UserPublic,
    UserAddress,
    UserClaimsVip,
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
    userClaimsVip: {
      get() {
        return this.$store.state.user.claims_vip
      },
      set(value) {
        this.updateClaimsVip(value)
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
      // child components don't `expose` explicitly, but this still works
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
      updateClaimsVip: UPDATE_CLAIMS_VIP,
    })
  }
}

</script>