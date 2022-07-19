<template>
  <div id="step-confirm" class="modal-mask" @click.self="close">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            {{ i18n.confirmNoRedactionTitle }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            :aria-label="i18n.close"
            @click="close"></button>
        </div>
        <div class="modal-body">
          <p>
            {{ i18n.confirmNoRedactionsText }}
          </p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn" @click="close">
            {{ i18n.cancel }}
          </button>
          <button
            id="send-request-button"
            type="submit"
            class="btn btn-primary"
            @click="submit">
            {{ i18n.publishWithoutRedaction }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConfirmNoRedaction',
  props: {
    i18n: {
      type: Object,
      required: true
    }
  },
  methods: {
    close() {
      this.$emit('close')
    },
    submit() {
      this.$emit('submit')
    }
  }
}
</script>
