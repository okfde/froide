<script setup>
defineProps({
  progress: Number
})
</script>

<template>
  <div class="appshell">
    <header class="appshell-header">
      <div class="appshell-header-container container">
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
      <div class="appshell-header-progress">
        <div
          class="appshell-header-progress-bar"
          :style="{ width: progress * 100 + '%' }"></div>
      </div>
    </header>
    <div class="appshell-nav">
      <slot name="nav" />
    </div>
    <div class="appshell-main">
      <slot name="main" />
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

  @media (max-width: $breakpoint) {
    // regular fixed header gets in the way
    position: fixed;
  }
}

.appshell-header-container {
  height: calc($header-height - $header-progress-height);
  display: grid;
  grid-template-rows: 0.45fr 0.55fr;
  grid-template-columns: 3em auto;
  grid-template-areas:
    'logo     title1'
    'logo     title2';
  gap: 0.2em;
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

.appshell-header-progress {
  height: $header-progress-height;
  background: lightgrey;
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
