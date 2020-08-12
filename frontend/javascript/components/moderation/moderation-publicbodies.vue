<template>
  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>{{ i18n.name }}</th>
          <th>{{ i18n.date }}</th>
          <th class="action-column">
            {{ i18n.action }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="pb in pbs"
          :key="pb.id"
        >
          <td>
            <a
              :href="pb.url"
              target="_blank"
            >
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
                class="btn btn-primary"
                target="_blank"
              >
                {{ i18n.reviewChangedPublicBody }}
              </a>
            </template>
            <template v-else>
              <a
                :href="pb.acceptUrl"
                class="btn btn-secondary"
                target="_blank"
              >
                {{ i18n.reviewNewPublicBody }}
              </a>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>

const getUrl = (templ, objId) => templ.replace(/0/, objId)

export default {
  name: 'ModerationPublicbodies',
  props: {
    config: {
      type: Object,
      required: true
    },
    publicbodies: {
      type: Array,
      required: true
    }
  },
  computed: {
    i18n () {
      return this.config.i18n
    },
    pbs () {
      return this.publicbodies.map(pb => {
        pb.url = getUrl(this.config.url.publicBody, pb.id)
        pb.acceptUrl = getUrl(this.config.url.publicBodyAcceptChanges, pb.id)
        return pb
      })
    }
  },
  methods: {

  }
}
</script>

<style lang="scss" scoped>
  .action-column {
    min-width: 120px;
  }
</style>