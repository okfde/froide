<template>
  <div class="row">
    <div class="col-md-12">
      <input type="hidden" name="hide_public" v-model="hidePublic" id="id_hide_public"/>
      <div class="card mb-3" v-if="!hidePublic">
        <div class="card-body">
          <div class="checkbox">
            <label>
              <input type="checkbox" name="public" id="id_public" v-model="publicValue"/>
              {{ form.fields.public.label }}
            </label>
            <small class="form-text text-muted">
              {{ form.fields.public.help_text }}
            </small>
          </div>
        </div>
      </div>
      <div v-else style="display: none">
        <input type="checkbox" name="public" id="id_public" v-model="publicValue"/>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'request-public',
  props: {
    form: {
      type: Object
    },
    hidePublic: {
      type: Boolean,
      default: false
    }
  },
  data () {
    return {
      public: this.form.fields.public.value || this.form.fields.public.initial
    }
  },
  computed: {
    publicValue: {
      get() {
        return this.public
      },
      set (value) {
        this.public = value
        this.$emit('update:initialPublic', value)
      }
    }
  }
}
</script>