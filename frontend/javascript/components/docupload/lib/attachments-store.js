import { defineStore } from 'pinia'

let imageDocId = 0

/* has to be called with the global pinia instance imported from lib/pinia.js
  due to our late ("onDom") app.use(pinia) call, cf. attachments.js */
const useAttachmentsStore = defineStore('attachments', {
  state: () => { console.trace('att-store state()'); return {
    isConverting: false,
    isFetching: false,
    all: [],
    images: [],
    selectedIds: new Set
  }},
  getters: {
    approved: (state) => state.all.filter((d) => (!d.is_irrelevant && d.approved && !d.has_redacted && !(d.converted && !d.is_image))),
    notApproved: (state) => state.all.filter((d) => (!d.is_irrelevant && !d.approved && !d.has_redacted && !(d.converted && !d.is_image))),
    relevant: (state) => state.all.filter((d) => !d.is_irrelevant && !(d.converted && !d.is_image)),
    irrelevant: (state) => state.all.filter((d) => d.is_irrelevant),
    getById: (state) => {
      return (id) => state.all.find((d) => d.id === id)
    },
    selected (state) {
      return [...state.selectedIds].map(id => this.getById(id))
    },
    getUnredactedAttachmentByResourceUri: (state) => {
      return (resourceUri) => state.all.find((d) => d.redacted === resourceUri)
    },
    getUnconvertedAttachmentByResourceUri: (state) => {
      return (resourceUri) => state.all.find((d) => d.converted === resourceUri)
    }
  },
  actions: {
    splitPages(imageIndex, pageNum) {
      console.log('# att store splitPages')
      const newPages = this.images[imageIndex].pages.slice(pageNum)
      this.images[imageIndex].pages = this.images[imageIndex].pages.slice(0, pageNum)
      this.images[imageIndex].new = true
      this.images.push({ pages: newPages, new: true })
    },
    removeAttachment(attachment) {
      this.all = this.all.filter((a) => a.id !== attachment.id)
    },
    addImages(newImages, { isNew = false, imageDefaultFilename = '' } = {}) {
      // if there are no image documents yet, create a new one
      // otherwise, append a page to the existing image
      if (this.images.length === 0) {
        imageDocId += 1
        this.images.push({
          id: 'imagedoc' + imageDocId,
          filetype: null,
          type: 'imagedoc',
          'new': isNew,
          name: imageDefaultFilename, // TODO: provide default name here?
          isConverting: false,
          progress: false,
          pages: newImages // .map((i, c) => ({ ...i, pageNum: c + 1 }))
        })
      } else {
        this.images[0].pages.push(...newImages)
      }
    },
    selectSubset(subset) {
      subset.forEach(_ => this.selectedIds.add(_.id))
    },
    unselectSubset(subset) {
      subset.forEach(_ => this.selectedIds.delete(_.id))
    }
  }
})

export { useAttachmentsStore }
