import { defineStore } from 'pinia'

let imageDocId = 0

const getNewImageDoc = ({ pages, isNew = false } = {}) => {
  imageDocId += 1
  return {
    id: 'imagedoc' + imageDocId,
    filetype: null,
    type: 'imagedoc',
    'new': isNew,
    name: '',
    pages
  }
}

/* has to be called with the global pinia instance imported from lib/pinia.js
  due to our late ("onDom") app.use(pinia) call, cf. attachments.js */
const useAttachmentsStore = defineStore('attachments', {
  state: () => { console.trace('att-store state()'); return {
    isConverting: false,
    all: [],
  }},
  getters: {
    images: (state) => state.all.filter((d) => d.type === 'imagedoc')
  },
  actions: {
    splitPages(image, pageNum) {
      console.log('# att store splitPages')
      const newPages = image.pages.slice(pageNum)
      newPages.forEach((p, i) => {
        p.pageNum = i + 1
      })
      image.pages = image.pages.slice(0, pageNum)
      image.new = true
      this.all.push(getNewImageDoc({ pages: newPages }))
      /*
      this.documents = [
        ...this.documents.filter((d) => d.type === 'imagedoc'),
        this.getNewImageDoc({
          pages: newPages
        }),
        ...this.documents.filter((d) => d.type !== 'imagedoc')
      ]
      */
    }
  }
})

export { useAttachmentsStore, getNewImageDoc }
