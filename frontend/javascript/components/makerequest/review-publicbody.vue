<template>
  <div
    v-if="multiRequest && canBatchRequest"
    class="publicbody-summary-container">
    <div class="publicbody-summary">
      <p>
        <template v-if="publicBodies.length < 20">
          <ul>
            <li v-for="pb in publicBodies" :key="pb.id">
              {{ pb.name }}
              <!--<div v-if="pb.request_note_html" class="col-lg-8 alert alert-warning pb-0" v-html="pb.request_note_html" />-->
            </li>
          </ul>
        </template>
        <template v-else>
          {{ i18n._('toMultiPublicBodies', { count: publicBodies.length }) }}
        </template>
        <!--
        <span v-if="!hidePublicbodyChooser">
          <a
            class="pb-change-link badge rounded-pill text-bg-primary ms-3"
            :href="config.url.makeRequest"
            @click.prevent="$emit('setStepSelectPublicBody')">
            {{ i18n.change }}
          </a>
        </span>
        -->
      </p>
    </div>
  </div>
  <div v-if="multiRequest && !canBatchRequest" class="mb-5 mt-5">
    <p>{{ i18n._('toMultiPublicBodies', { count: publicBodies.length }) }}</p>
    <div class="publicbody-summary-list">
      <ul>
        <li v-for="pb in publicBodies" :key="pb.id">
          {{ pb.name }}
        </li>
      </ul>
    </div>
    <small>{{ i18n.batchRequestDraftOnly }}</small>
  </div>

  <div v-if="!multiRequest" class="publicbody-summary-container">
    <div class="row">
      <div class="col-lg-12 publicbody-summary">
        <p>
        <!--{{ i18n._('toPublicBody', { name: publicBody?.name || '?' }) }}-->
         {{ publicBody?.name || '?' }}
          <!--<a v-if="publicBody" :href="publicBody.site_url" target="_blank">
            <span class="fa fa-info-circle" />
          </a>-->
          <!--<span v-if="!hidePublicbodyChooser">
            <a
              class="pb-change-link badge rounded-pill text-bg-primary ms-3"
              :href="config.url.makeRequest"
              @click.prevent="$emit('setStepSelectPublicBody')">
              {{ i18n.change }}
            </a>
          </span>-->
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
import I18nMixin from '../../lib/i18n-mixin'

import { mapGetters } from 'vuex'

export default {
  name: 'ReviewPublicbody',
  mixins: [I18nMixin],
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
      'defaultLaw',
    ])
  }
}
</script>