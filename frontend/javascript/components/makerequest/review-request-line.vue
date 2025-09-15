<template>
  <div class="row border-top">
    <div class="col-md-2">
      <h5 class="fs-6">{{ title }}</h5>
    </div>
    <div class="col-md-8">
      <slot name="contents">
        <div
          :class="{ 'text-danger': invalid }"
          >{{ contents }}</div>
      </slot>
    </div>
    <div class="col-md-2">
      <button
        v-if="step"
        type="button"
        class="btn btn-sm"
        :class="{
          'btn-link': !invalid,
          'btn-primary': invalid
        }"
        @click="setStep(step)"
        >{{ invalid ? '§korrigieren' : i18n.change }}</button>
    </div>
  </div>
</template>

<script>
import { mapMutations } from 'vuex'
import {
  SET_STEP,
} from '../../store/mutation_types'

export default {
  name: 'ReviewRequest',
  props: {
    i18n: {
      type: Object,
      required: true
    },
    title: {
      type: String,
      default: ''
    },
    contents: {
      type: String,
      default: ''
    },
    invalid: {
      type: Boolean,
      default: false
    },
    step: {
      type: String,
      default: ''
    },
  },
  methods: {
    ...mapMutations({
      setStep: SET_STEP,
    })
  }
}

</script>
