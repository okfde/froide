<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  step: Number,
  steps: Array,
  clickable: Boolean,
  keepVisitedClickable: Boolean
})

const emit = defineEmits('stepClick')

const stepClick = (stepIndex) => {
  if (!props.clickable) return
  if (stepIndex <= maxClickableStep.value) {
    emit('stepClick', stepIndex)
  }
}

const maxVisitedStep = ref(0)
watch(
  () => props.step, () => {
    maxVisitedStep.value = Math.max(maxVisitedStep.value, props.step)
  },
  { immediate: true }
)

const maxClickableStep = computed(() => props.keepVisitedClickable ? maxVisitedStep.value : props.step)

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
      <div class="container">
        <div class="row position-relative">
          <component
            :is="(clickable && (stepIndex <= maxClickableStep)) ? 'a' : 'div'"
            v-for="(stepLabel, stepIndex) in steps"
            @click.prevent="stepClick(stepIndex)"
            :href="clickable ? '#step-' + stepIndex : false"
            :key="stepIndex"
            :class="{
              'fw-bold': stepIndex <= step
            }"
            class="step col d-flex flex-column align-items-center text-body z-1 flex-grow-1 flex-shrink-1 text-break"
            >
            <div
              :class="`step-marker ${markerClasses(stepIndex)} d-block rounded-circle text-center border border-primary`">
              {{ stepIndex + 1 }}
            </div>
            <div class="text-center">{{ stepLabel }}</div>
          </component>
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
  hyphens: auto;
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
