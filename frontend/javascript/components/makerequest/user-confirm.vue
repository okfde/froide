<template>
  <div class="form-check">
    <input
      type="checkbox"
      v-model="confirm"
      ref="confirm"
      name="confirm"
      class="form-check-input"
      required=""
      id="id_confirm"
      />
    <label
      for="id_confirm"
      class="form-check-label field-required"
      >Ich versichere, dass ich <strong>keine persönlichen Informationen über mich selbst anfrage.</strong><!-- TODO i18n -->
    </label>
  </div>
</template>

<script>
import { mapMutations } from 'vuex'

import {
  UPDATE_CONFIRM,
  UPDATE_CONFIRM_VALIDITY,
} from '../../store/mutation_types'

export default {
  name: 'UserConfirm',
  computed: {
    confirm: {
      get() {
        return this.$store.state.user.confirm
      },
      set(value) {
        this.updateConfirm(value)
      }
    }
  },
  methods: {
    validate() {
      this.updateConfirmValidity(
        this.$refs.confirm.reportValidity()
      )
    },
    ...mapMutations({
      updateConfirm: UPDATE_CONFIRM,
      updateConfirmValidity: UPDATE_CONFIRM_VALIDITY,
    })
  }
}
</script>
