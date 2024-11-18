import { defineStore } from 'pinia'

export const useAttachmentsStore = defineStore('attachments', {
  state: () => ({
    all: [],
  }),
  getters: {
    images: (state) => state.all.filter((d) => d.type === 'imagedoc')
  },
  actions: {
  }
})