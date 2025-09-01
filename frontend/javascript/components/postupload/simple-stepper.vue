<script setup>
import { computed } from 'vue'

const props = defineProps({
  step: Number,
  steps: Array
})

// [0.0,1.0]
const progressDesktop = computed(() => props.step / (props.steps.length - 1))

// [1/n,1.0]
const progressMobile = computed(() => (props.step + 1) / props.steps.length)
</script>

<template>
  <div class="simple-stepper">
    <!-- desktop/md -->
    <div class="d-none d-md-block py-2">
      <div class="container">
        <div class="row position-relative">
          <div
            v-for="(stepLabel, stepIndex) in steps"
            :key="stepIndex"
            class="step col d-flex flex-column align-items-center text-primary z-1"
            :class="{
              'fw-bold': stepIndex <= step
            }">
            <div
              :class="`step-marker d-block rounded-circle text-center border border-primary
                  ${
                    stepIndex <= step
                      ? 'text-white bg-primary'
                      : 'text-primary bg-body'
                  }`">
              {{ stepIndex + 1 }}
            </div>
            <div>{{ stepLabel }}</div>
          </div>
          <div
            class="progress progress--desktop position-absolute translate-middle-y"
            :style="{
              width: 100 * (1 - 1 / props.steps.length) + '%',
              left: 50 / props.steps.length + '%'
            }">
            <div
              class="progress-bar"
              :style="{ width: progressDesktop * 100 + '%' }"></div>
          </div>
        </div>
      </div>
    </div>
    <!-- mobile -->
    <!-- the breadcrumbs fit well in post-upload but make this component less reusable -->
    <div class="d-md-none bg-body-tertiary">
      <div class="container">
        <div class="breadcrumb">
          <div class="breadcrumb-item"></div>
          <div class="breadcrumb-item">
            <slot></slot>
          </div>
        </div>
      </div>
      <div class="d-lg-none progress progress--mobile">
        <div
          class="progress-bar"
          :style="{ width: progressMobile * 100 + '%' }"></div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.step {
  // TODO refine, bootstrapize
  flex: 1 1 0;
  hyphens: auto;
  word-break: break-word;
}

.step-marker {
  font-size: 1rem;
  width: 2rem;
  height: 2rem;
  line-height: 1.9rem;
}

.progress {
  height: 4px;
}

.progress--desktop {
  top: 1rem;
}
</style>
