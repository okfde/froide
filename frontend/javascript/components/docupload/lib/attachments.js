import { onMounted } from 'vue'
import { postData } from '../../../lib/api'

import { useAttachmentsStore } from './attachments-store'

console.log('### attachments.js "root" 1')

let attachments

console.log('### attachments.js "root" 2')

const prepareImages = (images) => images
  .sort((a, b) => {
    if (a.name < b.name) return -1
    if (a.name > b.name) return 1
    return 0
  })
  .map((x, i) => {
    x.pageNum = i + 1
    return x
  })

let imageDocId = 0

const getNewImageDoc = (data) => {
  imageDocId += 1
  return {
    id: 'imagedoc' + imageDocId,
    filetype: null,
    type: 'imagedoc',
    new: true,
    name: '',
    ...data
  }
}

const processAttachmentsFromFetch = (attachments, extra = {}) => {
  const ret = []
  let images = []
  attachments.forEach((att) => {
    const a = {
      id: att.id,
      name: att.name,
      filetype: att.filetype,
      pending: att.pending,
      file_url: att.file_url,
      is_redacted: att.is_redacted,
      has_redacted: !!att.redacted,
      pages: null,
      attachment: att,
      auto_approve: true,
      ...extra
    }
    let imagePage = false

    if (att.is_irrelevant) {
      a.irrelevant = true
    } else if (att.is_pdf) {
      a.type = 'pdf'
    } else if (att.is_image) {
      if (att.converted) {
        a.irrelevant = true
      } else {
        imagePage = true
        images.push({
          id: att.id,
          name: att.name,
          attachment: att,
          file_url: att.file_url
        })
      }
    }
    if (!imagePage) {
      ret.push(a)
    }
    // unused?
    // this.names[att.name] = true
  })
  if (images.length > 0) {
    images = prepareImages(images)
    ret.unshift(
      getNewImageDoc({
        pages: images,
        new: false
      })
    )
  }
  return ret
}

const addImages = (images) => {
  // if there are no image documents yet, create a new one
  // otherwise, append a page to the existing image
  if (attachments.images.length === 0) {
    // TODO this used to be a complicated prepend, maybe unnecessary?
    attachments.all.push(
      getNewImageDoc({
        pages: images.map((i, c) => {
          i.pageNum = c + 1
          return i
        })
      })
    )
  } else {
    const imageAtt = attachments.images[0]
    imageAtt.pages = [
      ...imageAtt.pages,
      ...images.map((i, c) => {
        i.pageNum = imageAtt.pages.length + c + 1
        return i
      })
    ]
  }
  // this.$emit('imagesadded')
}

const convertImages = () => {
}
convertImages()

const fetchAttachments = (url, csrfToken) => {
  return fetch(url, {
    headers: { 'X-CSRFToken': csrfToken }
  })
    .then((response) => {
      if (!response.ok) {
        console.error('fetch attachment error', url, response)
        // TODO
        throw new Error(response.message)
      }
      return response.json()
    })
    .then((response) => {
      console.log(response)
      if (response.meta.next) {
        // TODO
        // the API has a hardcoded limit/pagesize of 50
        // would have to fetch multiple times to get all
        console.warn('not all attachments fetched')
      }
      const savedAttrs = attachments.all.reduce((a, d) => {
        a[d.id] = {
          selected: d.selected,
          auto_approve: d.auto_approve
        }
        return a
      }, {})
      attachments.$patch({
        all: processAttachmentsFromFetch(response.objects)
          .map((d) => ({ ...d, ...savedAttrs[d.id] }))
      })
    })
}

const addFromUppy = ({ csrfToken, convertAttachmentsUrl, onImagesAdded, onDocumentsAdded }) => ({ uppy, response, file }) => {
  const uploadUrl = response.uploadURL
  return postData(
    convertAttachmentsUrl,
    {
      action: 'add_tus_attachment',
      upload: uploadUrl
    },
    csrfToken
  )
    .then((result) => {
      if (result.error) {
        throw new Error(result.message)
      }
      const att = result.added[0]
      if (att.is_image) {
        addImages([att])
        onImagesAdded()
      } else {
        /*
        documents.value = [
          ...buildDocuments([att], { new: true }),
          ...documents.value
        ]
        */
        // TODO again, weird prepend?
        attachments.all.push(processAttachmentsFromFetch([att], { 'new': true }))
        // this.$emit('documentsadded')
        onDocumentsAdded()
      }
    })
    .then(() => {
      uppy.removeFile(file.id)
    })
}

export function useAttachments({ url, csrfToken, convertAttachmentsUrl, onDocumentsAdded = () => {}, onImagesAdded = () => {} }) {
  console.log('### attachments.js useAttachments')
  attachments = useAttachmentsStore()
  const refresh = () => fetchAttachments(url, csrfToken)
  onMounted(() => {
    console.log('### attachments.js onMounted')
    refresh()
  })
  return {
    refresh,
    addFromUppy: addFromUppy({ csrfToken, convertAttachmentsUrl, onDocumentsAdded, onImagesAdded }),
  }
}
