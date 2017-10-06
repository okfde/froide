<template>
  <div v-if="publicbody" class="card">
    <h5 class="card-header">
      {{ i18n.similarExist }}
    </h5>
    <div class="card-body">
      <div class="row">
        <div class="col-md-6">
          <h6>
            {{ i18n.similarRequests }}
          </h6>

        </div>
        <div class="col-md-6">
          <h6>
            {{ i18n.relevantResources }}
          </h6>
          <ul>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>

import {mapGetters} from 'vuex'

export default {
  name: 'similar-requests',
  props: ['config'],
  computed: {
    i18n () {
      return this.config.i18n
    },
    ...mapGetters(['publicbody'])
  }
}
</script>
