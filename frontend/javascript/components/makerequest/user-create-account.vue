<template>
  <div>
    <UserRegistration
      ref="userRegistration"
      :form="userForm"
      :user-form="userForm"
      :config="config"
      :use-pseudonym="usePseudonym"
      v-model:initial-first-name="firstName"
      v-model:initial-last-name="lastName"
      v-model:initial-email="email"
    />

    <!-- TODO: password, see UserRegistration stub -->

    <UserAddress
      ref="userAddress"
      :form="userForm"
      :config="config"
      :default-law="defaultLaw"
      :address-help-text="addressHelpText"
      :address-required="addressRequired"
    />

    <template v-if="config.settings.user_can_hide_web">
      <h3 id="id_private_label" class="fs-6">
        {{ gettext('Privacy') }}
      </h3>
      <UserPublic
        :user-form="userForm"
        :config="config"
        v-model:initial-private="userPrivate"
      >
        <slot name="userPublicPreamble"></slot>
      </UserPublic>
    </template>

    <template v-if="config.settings.user_can_claim_vip && showUserClaimsVip">
      <h3 id="id_claims_vip_label" class="fs-6">
        {{ userForm.fields.claims_vip.label }}
      </h3>
      <UserClaimsVip
        :user-form="userForm"
        v-model:initial-value="userClaimsVip"
      />
    </template>

    <h3 class="fs-6">{{ gettext('Terms of Use') }}</h3>
    <UserTerms
      ref="userTerms"
      :form="userForm"
      v-model:initial-terms="userTerms"
    />

    <div class="my-4" v-if="showNextButton">
      <button
        type="button"
        class="btn btn-primary"
        @click="validateAllNextStep"
      >
        {{ gettext('Next') }}
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
import { translateMixin } from 'vuepo/vue'

import {
  UPDATE_FIRST_NAME,
  UPDATE_LAST_NAME,
  UPDATE_EMAIL,
  UPDATE_PRIVATE,
  UPDATE_CLAIMS_VIP,
  UPDATE_TERMS
} from '../../store/mutation_types'

export default {
  name: 'UserCreateAccount',
  mixins: [translateMixin],
  components: {
    UserRegistration,
    UserTerms,
    UserPublic,
    UserAddress,
    UserClaimsVip
  },
  emits: ['stepNext'],
  props: {
    config: {
      type: Object
    },
    userForm: {
      type: Object
    },
    showNextButton: {
      type: Boolean
    },
    showUserClaimsVip: {
      type: Boolean
    },
    addressHelpText: {
      type: String,
      default: null
    },
    addressRequired: {
      type: Boolean,
      default: false
    },
    defaultLaw: {
      type: Object
    },
    // TODO: this used to be true, hint should be added to privacy help page?
    usePseudonym: {
      type: Boolean,
      default: false
    }
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
    userTerms: {
      get() {
        return this.$store.state.user.terms
      },
      set(value) {
        this.updateTerms(value)
      }
    },
    ...mapGetters([
      'firstNameValid',
      'lastNameValid',
      'emailValid',
      'addressValid',
      'termsValid',
      'stepCanContinue'
    ])
  },
  methods: {
    validateAllNextStep() {
      // child components don't `expose` explicitly, but this still works
      this.$refs.userTerms.validate()
      this.$refs.userAddress.validate()
      this.$refs.userRegistration.validateAll()
      if (
        this.firstNameValid &&
        this.lastNameValid &&
        this.emailValid &&
        this.addressValid &&
        this.termsValid
      ) {
        this.$emit('stepNext')
      }
    },
    ...mapMutations({
      updateFirstName: UPDATE_FIRST_NAME,
      updateLastName: UPDATE_LAST_NAME,
      updateEmail: UPDATE_EMAIL,
      updatePrivate: UPDATE_PRIVATE,
      updateClaimsVip: UPDATE_CLAIMS_VIP,
      updateTerms: UPDATE_TERMS
    })
  }
}
</script>
