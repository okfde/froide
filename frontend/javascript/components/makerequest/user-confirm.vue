<template>
  <div class="form-check form-check-emphasized">
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
      >
      <slot />
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

<style scoped>

/* hide required indicator (a red asterisk) for labels that contain block markup */

label:has(p)::after,
label:has(div)::after,
label:has(ul)::after {
  display: none;
}

</style>