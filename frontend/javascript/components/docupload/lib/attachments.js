import { postData } from '../../../lib/api'

//import { createPinia } from 'pinia'
import { pinia } from '../../../lib/pinia'
import { useAttachmentsStore, getNewImageDoc } from './attachments-store'

import ExifReader from 'exifreader'

console.log('### attachments.js "root" 1')

const attachments = useAttachmentsStore(pinia)

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

const convertImage = (image) => {
  attachments.isConverting = true
  return postData(
    config.urls.convertAttachments,
    {
      action: 'convert_to_pdf',
      title: 'TODO',
      images: image.pages.map((p) => ({
        id: p.id,
        rotate: (p.rotate || 0) + (p.implicitRotate || 0)
      }))
    },
    config.csrfToken
  )
    .then((newAttachment) => {
      // remove converted
      attachments.all = attachments.all.filter((a) => a.id != image.id)
      // append new
      attachments.all.push(...processAttachmentsFromFetch([newAttachment], { new: true }))
    })
    .finally(() => {
      attachments.isConverting = false
    })
}

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

const fetchImagePage = (page) => {
  fetch(page.file_url)
    .then((response) => {
      return response.blob()
    })
    .then((blob) => {
      return Promise.all([blob.arrayBuffer(), createImageBitmap(blob)])
    })
    .then(([ab, v]) => {
      const reader = ExifReader.load(ab, { expanded: true })
      const metadata = {
        exif: true,
        width: v.width,
        heigh: v.height,
        implicitRotate: 0
      }
      const orientation = reader.exif?.Orientation?.value
      if (orientation === 6) {
        metadata.implicitRotate = 90
      } else if (orientation === 8) {
        metadata.implicitRotate = 270
      } else if (orientation === 3) {
        metadata.implicitRotate = 180
      }
      page.metadata = metadata
      page.imgBitmap = v
      page.loaded = true
    })
}

// const addFromUppy = ({ csrfToken, convertAttachmentsUrl, onImagesAdded, onDocumentsAdded }) => ({ uppy, response, file }) => {
const addFromUppy = ({ uppy, response, file }) => {
  const uploadUrl = response.uploadURL
  return postData(
    config.urls.convertAttachmentsUrl,
    {
      action: 'add_tus_attachment',
      upload: uploadUrl
    },
    config.csrfToken
  )
    .then((result) => {
      if (result.error) {
        throw new Error(result.message)
      }
      const att = result.added[0]
      if (att.is_image) {
        addImages([att])
        // onImagesAdded()
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
        // onDocumentsAdded()
      }
    })
    .then(() => {
      uppy.removeFile(file.id)
    })
}

const config = {}

const refresh = () => fetchAttachments(config.urls.getAttachment, config.csrfToken)

attachments.$subscribe(() => {
  attachments.images.forEach(image => {
    image.pages.forEach(page => {
      if (!page.loaded && !page.loading) {
        fetchImagePage(page)
      }
    })
  })
})

const rotatePage = (page) => {
  page.rotate = ((page.rotate || 0) + 90) % 360
}

export function useAttachments({ urls = null, csrfToken = null} = {}) {
  if (urls) config.urls = urls
  if (csrfToken) config.csrfToken = csrfToken
  console.log('### attachments.js useAttachments')
  /*
  onMounted(() => {
    console.log('### attachments.js onMounted')
    refresh()
  })
  */
  return {
    pinia,
    refresh,
    attachments,
    convertImage,
    splitPages: attachments.splitPages,
    rotatePage,
    addFromUppy,
  }
}
