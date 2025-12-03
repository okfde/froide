<template>
  <div class="row border-top py-1">
    <div class="col-sm-12 col-md-2 py-1">
      <h3 class="fs-6 lh-base m-0" style="hyphens: auto">{{ title }}</h3>
    </div>
    <div class="col-sm-8 col-md-8 py-1">
      <slot name="contents">
        <div
          :class="{ 'text-danger': invalid }"
          >{{ contents }}</div>
      </slot>
    </div>
    <div class="col-sm-4 col-md-2 text-sm-end">
      <button
        v-if="step"
        type="button"
        class="btn btn-sm"
        :class="{
          'btn-link': !invalid,
          'btn-primary': invalid
        }"
        @click="setStep(step)"
        >{{ invalid ? i18n.correct : i18n.change }}</button>
    </div>
  </div>
</template>

<script>
import { mapMutations } from 'vuex'
import {
  SET_STEP,
} from '../../store/mutation_types'

export default {
  name: 'ReviewRequestLine',
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
