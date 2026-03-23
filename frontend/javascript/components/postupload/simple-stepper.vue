<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  step: Number,
  steps: Array,
  clickable: Boolean,
  keepVisitedClickable: Boolean
})

const emit = defineEmits(['stepClick'])

const stepClick = (stepIndex) => {
  if (!props.clickable) return
  if (stepIndex <= maxClickableStep.value) {
    emit('stepClick', stepIndex)
  }
}

const maxVisitedStep = ref(0)
watch(
  () => props.step,
  () => {
    maxVisitedStep.value = Math.max(maxVisitedStep.value, props.step)
  },
  { immediate: true }
)

const maxClickableStep = computed(() =>
  props.keepVisitedClickable ? maxVisitedStep.value : props.step
)

const markerClasses = (stepIndex) => {
  if (stepIndex <= props.step) return 'text-white bg-primary'
  if (stepIndex <= maxClickableStep.value) return 'text-body bg-primary-subtle'
  return 'text-body bg-body'
}

// [0.0,1.0]
const progressDesktop = computed(() => props.step / (props.steps.length - 1))

// [1/n,1.0]
const progressMobile = computed(() => (props.step + 1) / props.steps.length)
</script>

<template>
  <div class="simple-stepper">
    <!-- desktop/md -->
    <div class="d-none d-md-block py-2">
      <nav class="container">
        <div class="position-relative">
          <ol class="d-flex justify-content-between list-unstyled m-0">
            <li
              v-for="(stepLabel, stepIndex) in steps"
              :key="stepIndex"
              class="d-contents"
            >
              <component
                :is="clickable && stepIndex <= maxClickableStep ? 'a' : 'div'"
                :href="clickable ? '#step-' + stepIndex : false"
                class="step d-flex flex-column align-items-center text-body z-1 small"
                :class="{
                  'fw-semibold': stepIndex <= step
                }"
                :aria-current="stepIndex == step ? 'step' : null"
                :aria-disabled="stepIndex > step"
                @click.prevent="stepClick(stepIndex)"
              >
                <div
                  class="step-marker d-block rounded-circle text-center border border-primary"
                  :class="markerClasses(stepIndex)"
                  aria-hidden="true"
                >
                  {{ stepIndex + 1 }}
                </div>
                <div class="text-center step-label">{{ stepLabel }}</div>
              </component>
            </li>
          </ol>
          <div class="progress progress--desktop position-absolute">
            <div
              class="progress-bar"
              :style="{ width: progressDesktop * 100 + '%' }"
            ></div>
          </div>
        </div>
      </nav>
    </div>
    <!-- mobile -->
    <!-- the breadcrumbs fit well in post-upload but make this component less reusable -->
    <div class="d-md-none bg-body-tertiary">
      <div class="container">
        <div class="breadcrumb">
          <div class="breadcrumb-item">
            <slot></slot>
          </div>
        </div>
      </div>
      <div class="d-lg-none progress progress--mobile">
        <div
          class="progress-bar"
          :style="{ width: progressMobile * 100 + '%' }"
        ></div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import '../../../styles/variables.scss';

.step {
  width: 9rem;
}

a.step {
  &:hover {
    text-decoration: none;

    .step-label {
      text-decoration: underline;
    }
  }
}

.step-marker {
  width: 2rem;
  height: 2rem;
  line-height: 1.9rem;
}

.progress {
  height: 4px;
}

.progress--desktop {
  top: 1rem;
  left: 4.5rem;
  right: 4.5rem;
  width: calc(100% - 9rem);
}
</style>
