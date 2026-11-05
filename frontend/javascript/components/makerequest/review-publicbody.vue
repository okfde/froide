<template>
  <div
    v-if="multiRequest && canBatchRequest"
    class="publicbody-summary-container"
  >
    <div class="publicbody-summary">
      <ul class="list">
        <PbTruncatedList
          :public-bodies="publicBodies"
          :threshold="20"
          :show-count="20"
        >
          <template #default="{ pb }">
            <li>
              <a v-if="pb" :href="pb.site_url" target="_blank">
                {{ pb.name }}
              </a>

              <div
                v-if="pb.request_note_html"
                class="col-lg-8 alert alert-warning pb-0"
                v-html="pb.request_note_html"
              />
            </li>
          </template>
          <template #truncation="{ count }">
            <li>… ({{ publicBodiesCount(count) }})</li>
          </template>
        </PbTruncatedList>
      </ul>
    </div>
  </div>
  <div v-if="multiRequest && !canBatchRequest" class="mb-5 mt-5">
    <p>{{ toMultiPublicBodies(publicBodies.length) }}</p>
    <div class="publicbody-summary-list">
      <ul>
        <li v-for="pb in publicBodies" :key="pb.id">
          {{ pb.name }}
        </li>
      </ul>
    </div>
    <small>{{
      gettext(
        'You have been allowed to make one project request to these public bodies, but you do not have permission to select your own.'
      )
    }}</small>
  </div>

  <div v-if="!multiRequest" class="publicbody-summary-container">
    <div class="row">
      <div class="col-lg-12 publicbody-summary">
        <p v-if="publicBody">
          <a :href="publicBody.site_url" target="_blank">
            {{ publicBody.name }}
          </a>
        </p>
      </div>
    </div>
    <div v-if="hasLawNotes" class="row">
      <div class="col-lg-8">
        <div class="alert alert-warning" v-html="lawNotes" />
      </div>
    </div>
    <div v-if="hasPublicBodyNotes" class="row">
      <div class="col-lg-8">
        <div class="alert alert-warning" v-html="publicBodyNotes" />
      </div>
    </div>
  </div>
</template>

<script>
import { t } from 'vuepo'
import { translateMixin } from 'vuepo/vue'

import { mapGetters } from 'vuex'

import PbTruncatedList from '../publicbody/pb-truncated-list.vue'

export default {
  name: 'ReviewPublicbody',
  mixins: [translateMixin],
  components: {
    PbTruncatedList
  },
  props: {
    config: {
      type: Object,
      required: true
    },
    multiRequest: {
      type: Boolean,
      default: false
    },
    pbScope: {
      type: String,
      required: true
    }
  },
  computed: {
    canBatchRequest() {
      return this.config.settings.user_can_create_batch
    },
    publicBody() {
      return this.getPublicBodyByScope(this.pbScope)
    },
    publicBodies() {
      return this.getPublicBodiesByScope(this.pbScope)
    },
    hasLawNotes() {
      if (this.defaultLaw) {
        return !!this.defaultLaw.request_note_html
      }
      // FIXME: find all notes of all public body default laws?
      return false
    },
    hasPublicBodyNotes() {
      if (this.publicBody) {
        return !!this.publicBody.request_note_html
      }
      // FIXME: find all notes of all public body default laws?
      return false
    },
    lawNotes() {
      if (this.hasLawNotes) {
        return this.defaultLaw.request_note_html
      }
      return ''
    },
    publicBodyNotes() {
      if (this.hasPublicBodyNotes) {
        return this.publicBody.request_note_html
      }
      return ''
    },
    ...mapGetters([
      'getPublicBodyByScope',
      'getPublicBodiesByScope',
      'defaultLaw'
    ])
  },
  methods: {
    publicBodiesCount(count) {
      return this.ngettext('one public body', t`${count} public bodies`, count)
    },
    toMultiPublicBodies(count) {
      return this.ngettext(
        t`To: one public body`,
        t`To: ${count} public bodies`,
        count
      )
    }
  }
}
</script>

<style lang="scss" scoped>
.list {
  list-style-type: none;
  margin: 0;
  padding: 0;
}
</style>
