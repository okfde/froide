<script setup>

defineProps({
  label: {
    required: true,
    type: String
  },
  value: {
    required: true,
    type: String
  }
})

const emit = defineEmits(['removeClick'])

</script>

<template>
  <div class="filter-badge">
    <dl>
      <dt><small>{{ label }} =</small></dt>
      <dd>{{ value }}</dd>
    </dl>
    <button
      @click="emit('removeClick')"
      type="button"
      class="btn btn-close btn-close-white"
      aria-label="Close"></button>
  </div>
</template>

<style lang="scss" scoped>
@import '../../../styles/variables';

.filter-badge {
  background-color: $secondary;
  color: #fff; // TODO $secondary-text ?
  display: block;
  border-radius: 4px; // TODO set a BS var
  padding: 0.25rem 0.5rem;
  margin: 0.5rem 0;
  display: flex;
  justify-content: space-between;

  dl,
  dt,
  dd {
    margin: 0;
    font-weight: inherit;
  }
}
</style>