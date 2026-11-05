<template>
  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>{{ gettext('Name') }}</th>
          <th>{{ gettext('Date') }}</th>
          <th class="action-column">
            {{ pgettext('action to take in moderation table', 'Action') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="pb in pbs" :key="pb.id">
          <td>
            <a :href="pb.url" target="_blank">
              {{ pb.name }}
            </a>
          </td>
          <td>
            <template v-if="!pb.confirmed">
              {{ new Date(pb.created_at).toLocaleString() }}
            </template>
          </td>
          <td>
            <template v-if="pb.confirmed">
              <a
                :href="pb.acceptUrl"
                class="btn btn-primary btn-sm"
                target="_blank"
              >
                {{ gettext('review changes') }}
              </a>
            </template>
            <template v-else>
              <a
                :href="pb.acceptUrl"
                class="btn btn-secondary btn-sm"
                target="_blank"
              >
                {{ gettext('review new') }}
              </a>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { translateMixin } from 'vuepo/vue'

const getUrl = (templ, objId) => templ.replace(/0/, objId)

export default {
  name: 'ModerationPublicbodies',
  mixins: [translateMixin],
  props: {
    publicbodies: {
      type: Array,
      required: true
    }
  },
  inject: ['config'],
  computed: {
    pbs() {
      return this.publicbodies.map((pb) => {
        pb.url = getUrl(this.config.url.publicBody, pb.id)
        pb.acceptUrl = getUrl(this.config.url.publicBodyAcceptChanges, pb.id)
        return pb
      })
    }
  },
  methods: {}
}
</script>

<style lang="scss" scoped>
.action-column {
  min-width: 120px;
}
</style>
