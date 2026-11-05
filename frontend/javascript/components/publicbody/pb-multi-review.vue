<template>
  <div class="review">
    <div class="row mt-3 mb-3">
      <div class="col-auto">
        <h2>
          {{ publicBodiesCount(publicBodies.length) }}
        </h2>
      </div>
    </div>

    <PbSummary :scope="scope" :dimensions="summaryDimensions"></PbSummary>

    <div class="row mb-2">
      <div class="col-auto ms-auto">
        <button
          v-if="publicBodies.length > 0"
          @click.prevent="clearSelection"
          class="btn btn-sm hover-btn-danger"
        >
          <i class="fa fa-ban" aria-hidden="true"></i>
          {{ gettext('clear selection') }}
        </button>
      </div>
    </div>

    <PbTable
      :name="name"
      :scope="scope"
      :headers="headers"
      :options="chosenOptions"
      :rows="publicBodies"
      @select-all-rows="selectAllRows"
      class="transition"
    ></PbTable>

    <div class="row">
      <div class="col-auto ms-auto">
        <button
          type="button"
          class="btn btn-primary"
          :disabled="!stepCanContinue(scope)"
          @click="$emit('stepNext')"
        >
          {{ gettext('Next') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapMutations } from 'vuex'
import { t } from 'vuepo'
import { translateMixin } from 'vuepo/vue'
import { SET_STEP_SELECT_PUBLICBODY } from '../../store/mutation_types'

import PBChooserMixin from './lib/pb-chooser-mixin'
import PBListMixin from './lib/pb-list-mixin'
import { summaryDimensions } from '../../store/multi_settings'

import PbTable from './pb-table'
import PbSummary from './pb-summary'

export default {
  name: 'PbMultiReview',
  mixins: [translateMixin, PBChooserMixin, PBListMixin],
  emits: ['stepNext'],
  props: ['name', 'scope'],
  components: {
    PbTable,
    PbSummary
  },
  data() {
    return {
      chosenOptions: {
        sortableHeader: true
      }
    }
  },
  computed: {
    summaryDimensions() {
      return summaryDimensions
    },
    ...mapGetters(['stepCanContinue'])
  },
  methods: {
    publicBodiesCount(count) {
      return this.ngettext('one public body', t`${count} public bodies`, count)
    },
    ...mapMutations({
      setStepSelectPublicBody: SET_STEP_SELECT_PUBLICBODY
    })
  }
}
</script>
