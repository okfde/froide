<script setup>
import { ref, computed } from 'vue'
import OnlineHelp from './online-help.vue'

const props = defineProps({
  step: Number,
  steps: Array
})

const progressDesktop = computed(() => props.step / (props.steps.length - 1))

const progressMobile = computed(() => (props.step + 1) / props.steps.length)

const onlineHelpShow = ref(false)
const onlineHelpPath = ref('')

const showhelp = (e) => {
  onlineHelpShow.value = true
  onlineHelpPath.value = e
}
</script>

<template>
  <div class="appshell">
    <header class="appshell-header">
      <div
        class="appshell-header-container appshell-header-container--mobile container">
        <div class="appshell-header-logo">
          <div class="appshell-header-logo-image">
            <span class="visually-hidden">FragDenStaat</span>
          </div>
        </div>
        <div class="appshell-header-title1">
          <slot name="mobile-header-title1" />
        </div>
        <div class="appshell-header-title2">
          <slot name="mobile-header-title2" />
        </div>
      </div>
      <div class="appshell-header-container appshell-header-container--desktop">
        <div class="appshell-header-steps my-3">
          <ol>
            <li
              v-for="(stepLabel, stepIndex) in steps"
              :key="stepIndex"
              class="appshell-header-step"
              :class="{ 'appshell-header-step--active': stepIndex <= step }">
              <div class="appshell-header-step-marker">{{ stepIndex + 1 }}</div>
              <div>{{ stepLabel }}</div>
            </li>
          </ol>
          <div
            class="appshell-header-progress appshell-header-progress--desktop">
            <div
              class="appshell-header-progress-bar"
              :style="{ width: progressDesktop * 100 + '%' }"></div>
          </div>
        </div>
      </div>
      <div class="appshell-header-progress appshell-header-progress--mobile">
        <div
          class="appshell-header-progress-bar"
          :style="{ width: progressMobile * 100 + '%' }"></div>
      </div>
    </header>
    <div class="appshell-nav container">
      <slot name="nav" />
    </div>
    <div class="appshell-main">
      <slot name="main" @showhelp="showhelp" />
    </div>
    <div class="appshell-help" v-if="onlineHelpShow">
      <!-- .close should be provided by bootstrap, hmm -->
      <button
        type="button"
        class="close appshell-help-close"
        @click="onlineHelpShow = false"></button>
      <online-help :path="onlineHelpPath" />
    </div>
    <div class="appshell-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<!-- unscoped!
  well, scoped to the current django route .../post-hochladen/ since the global css is not ejected+collected
  else would have to guard via body.appshell
-->
<style lang="scss">
// TODO: arbitrarily switch to "appshell" under this breakpoint
//   not really usable, but also not broken. WIP
$breakpoint: 1600px;

@media (max-width: $breakpoint) {
  #header,
  #footer {
    display: none;
  }

  .postupload-breadcrumbs,
  .postupload-main-heading,
  .postupload-main-intro {
    display: none;
  }

  /*
  .postupload-main-container {
    width: 100% !important;
    max-width: 600px !important;
  }
  */
}
</style>

<style lang="scss" scoped>
// TODO: again, arbitrary breakpoint
$breakpoint: 1600px;
$ci-accent-text: rgb(
  41,
  109,
  255
); // blue from FDS logo, not var(--bs-link-color)

$header-height: 4em;
$actions-min-height: 4em;
$header-progress-height: 4px;
$step-width: 10em;

.appshell,
.appshell * {
  box-sizing: border-box;
}

.appshell-header {
  top: 0;
  left: 0;
  width: 100%;
  height: $header-height;
  background: white;
  position: relative;
  z-index: 1000;

  @media (max-width: $breakpoint) {
    // regular fixed header gets in the way
    position: fixed;
  }
}

.appshell-header-container--mobile {
  height: calc($header-height - $header-progress-height);
  display: none;
  grid-template-rows: 0.45fr 0.55fr;
  grid-template-columns: 3em auto;
  grid-template-areas:
    'logo     title1'
    'logo     title2';
  gap: 0.2em;

  @media (max-width: $breakpoint) {
    display: grid;
  }
}

.appshell-header-container--desktop {
  @media (max-width: $breakpoint) {
    display: none;
  }
}

.appshell-header-logo {
  grid-area: logo;
  justify-self: center;
  align-self: center;
}

.appshell-header-logo-image {
  width: 2.3em;
  height: 2em;
  background-image: url(/static/img/header_logo.svg);
  background-repeat: no-repeat;
  background-position: center left;
  background-size: cover;
}

.appshell-header-title1 {
  grid-area: title1;
  align-self: end;
  text-transform: uppercase;
  color: $ci-accent-text;
  font-size: 66%;
  font-weight: bolder;
}

.appshell-header-title2 {
  grid-area: title2;
  align-self: start;
  font-weight: bold;
}

.appshell-header-steps {
  width: $step-width * 3;
  margin: 0 auto;
  position: relative;
}

.appshell-header-steps ol {
  display: flex;
  list-style-type: none;
  padding: 0;
  margin: 0 auto;
  z-index: 1;
  position: relative;
}

.appshell-header-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: $step-width;
  color: $ci-accent-text;
}

.appshell-header-step--active {
  font-weight: bold;
}

.appshell-header-step-marker {
  display: block;
  width: 2em;
  height: 2em;
  box-sizing: border-box;
  border: 2px solid $ci-accent-text;
  border-radius: 50%;
  text-align: center;
  line-height: 1.8em;
  background: white;

  .appshell-header-step--active & {
    background: $ci-accent-text;
    color: white;
  }
}

.appshell-header-progress {
  height: $header-progress-height;
  background: lightgrey;
}

.appshell-header-progress--mobile {
  display: none;

  @media (max-width: $breakpoint) {
    display: block;
    position: static;
    width: 100%;
  }
}

.appshell-header-progress--desktop {
  position: absolute;
  top: calc(1em - ($header-progress-height / 2));
  left: $step-width / 2;
  width: $step-width * 2;
  z-index: 0;

  @media (max-width: $breakpoint) {
    display: none;
  }
}

.appshell-header-progress-bar {
  height: 100%;
  background-color: $ci-accent-text;
  transition: width 500ms;
}

.appshell-nav {
  padding-top: $header-height;
}

.appshell-main {
  padding-bottom: calc($actions-min-height + 4em);
}

.appshell-help {
  position: fixed;
  right: 0;
  // TODO this value was eyeballed from the bootstrap container width
  width: calc((100vw - 1000px) / 2);
  top: $header-height;
  bottom: 0;
  overflow-y: scroll;

  @media (max-width: $breakpoint) {
    top: $header-height;
    left: 0;
    width: 100%;
    bottom: 0;
    z-index: 100;
  }
}

.appshell-help-close {
  position: fixed;
  right: 1em;
  top: calc(1em + $header-height);
  width: 3em;
  height: 3em;
  background: 0;
  border: 0;

  &::after {
    content: '×';
    font-weight: bold;
    font-size: 200%;
    line-height: 1;
  }
}

.appshell-actions {
  @media (max-width: $breakpoint) {
    position: fixed;
  }

  bottom: 0;
  left: 0;
  width: 100%;
  min-height: $actions-min-height;
  padding: 0.5rem;
  background-color: white;
  transition: background-color 500ms;

  &:has(.action-info) {
    background-color: #eee;
  }
}
</style>
