<template>
  <div id="step-confirm" class="modal fade" tabindex="-1">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            {{ gettext('Are you sure that no redaction is needed?') }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            :aria-label="gettext('Close')"
          />
        </div>
        <div class="modal-body">
          <p>
            {{
              gettext(
                'You redacted parts of the document, but clicked that no redaction is needed. Are you sure that no redaction is needed?'
              )
            }}
          </p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn" data-bs-dismiss="modal">
            {{ gettext('Cancel') }}
          </button>
          <button
            id="send-request-button"
            type="submit"
            class="btn btn-primary"
            @click="submit"
          >
            {{ gettext('No redaction needed') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { translateMixin } from 'vuepo/vue'

export default {
  name: 'ConfirmNoRedaction',
  mixins: [translateMixin],
  methods: {
    submit() {
      this.$emit('submit')
    }
  }
}
</script>
