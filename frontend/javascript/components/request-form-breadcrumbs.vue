<template>
  <div class="process-breadcrumbs-container">
    <div class="container">
      <div class="row">
          <ol class="process-breadcrumbs col-md-8">
          <li :class="{ 'active': stepSelectPublicBody, 'done': stepSelectPublicBodyDone}">
            <a v-if="!hidePublicbodyChooser" href="#step-publicbody" @click.prevent="setStepSelectPublicBody">
              <i class="fa fa-check-circle" aria-hidden="true"></i>
              Behörde wählen
            </a>
            <span v-else>
              <i class="fa fa-check-circle" aria-hidden="true"></i>
              Behörde wählen
            </span>
          </li>
          <li v-if="multiRequest" :class="{'active': stepReviewPublicBodies, 'done': stepReviewPublicBodiesDone}">
            <a v-if="hasPublicBodies" href="#step-publicbody-review" @click.prevent="setStepReviewPublicBody">
              <i class="fa" :class="{ 'fa-check-circle': stepReviewPublicBodiesDone, 'fa-check-circle-o': !stepReviewPublicBodiesDone }" aria-hidden="true"></i>
              Auswahl prüfen
            </a>
            <span v-else>
              <i class="fa fa-check-circle-o" aria-hidden="true"></i>
              Auswahl prüfen
            </span>
          </li>
          <li :class="{ 'active': stepWriteRequest}">
            <a v-if="hasPublicBodies" href="#step-request"  @click.prevent="setStepRequest">
              <i class="fa" :class="{ 'fa-check-circle': stepWriteRequestDone, 'fa-check-circle-o': !stepWriteRequestDone }" aria-hidden="true"></i>
              Anfrage stellen
            </a>
            <span v-else>
              <i class="fa" :class="{ 'fa-check-circle': stepWriteRequestDone, 'fa-check-circle-o': !stepWriteRequestDone }" aria-hidden="true"></i>
              Anfrage stellen
            </span>
          </li>
          <li>
            <a href="#step-review" data-toggle="modal" v-if="stepWriteRequest">
              <i class="fa fa-check-circle-o" aria-hidden="true"></i>
              Anfrage prüfen
            </a>
            <span v-else>
              <i class="fa fa-check-circle-o" aria-hidden="true"></i>
              Anfrage prüfen
            </span>
          </li>
          </ol>
          <div class="pt-2 col-auto ml-auto" v-if="showNext">
            <button class="btn btn-secondary" @click.prevent="clickNext">
                zum nächsten Schritt
            </button>
          </div>
      </div>
    </div>
  </div>
</template>

<script>

import {mapGetters, mapMutations, mapActions} from 'vuex'


import {
  SET_STEP_SELECT_PUBLICBODY, SET_STEP_REVIEW_PUBLICBODY, SET_STEP_REQUEST
} from '../store/mutation_types'


export default {
  name: 'request-form-breadcrumbs',
  props: {
    i18n: {
      type: Object
    },
    hidePublicbodyChooser: {
      type: Boolean,
      default: false
    },
    multiRequest: {
      type: Boolean,
      default: false
    },
    hasPublicBodies: {
      type: Boolean,
      default: false
    }
  },
  data () {
    return {
      sortHeader: null,
      sortOrder: 1,
      allRowsSelected: false
    }
  },
  computed: {
    showNext() {
      if ((this.stepSelectPublicBody || this.stepReviewPublicBodies)
          && this.hasPublicBodies) {
        return true
      }
      return false
    },
    ...mapGetters([
      'stepReviewPublicBodies',
      'stepSelectPublicBody',
      'stepReviewPublicBodiesDone',
      'stepSelectPublicBodyDone',
      'stepWriteRequest',
      'stepWriteRequestDone'
    ])
  },
  methods: {
    clickNext () {
      if (this.hasPublicBodies) {
        if (this.stepSelectPublicBody && this.multiRequest) {
          this.setStepReviewPublicBody()
        } else {
          this.setStepRequest()
        }
      }
    },
    ...mapMutations({
      setStepSelectPublicBody: SET_STEP_SELECT_PUBLICBODY,
      setStepReviewPublicBody: SET_STEP_REVIEW_PUBLICBODY,
      setStepRequest: SET_STEP_REQUEST,
    })
  }
}
</script>

<style lang="scss" scoped>

@import "../../styles/variables";

.process-breadcrumbs-container {
  background-color: #f5f5f5;
  // position: sticky;
  // top: 0;
  // z-index: 500;
}

.process-breadcrumbs {
  margin-bottom: 0;
  list-style-type: none;
  display: flex;
  flex-wrap: wrap;

  li {
    flex: 1;
    min-width: 150px;
    padding: 15px 0;

    & > *, *:hover {
      color: $gray-500;
      text-decoration: none;
    }
    &.active > * {
      color: $black;
      font-weight: bold;
    }
    &.done > * {
      color: $success;
    }
  }
}
</style>