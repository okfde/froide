import { VueElement, createApp } from 'vue'

type PropValue = string | boolean | Record<string, unknown> | Array<unknown>
type Props = Record<string, PropValue>
export type DjangoSlots = Record<string, DocumentFragment> | undefined
interface OtherAttrs {
  class: Record<string, boolean>
}

function snakeToCamel(s: string) {
  return s.replace(/(-\w)/g, function (m) {
    return m[1].toUpperCase()
  })
}

const isNumber = /^-?[0-9.]+$/

function getPropsFromElement(el: HTMLElement): Props {
  const attrs = el.attributes
  const props: Props = {}

  for (let i = 0; i < attrs.length; i += 1) {
    const attr = attrs[i]
    if (attr.name[0] === 'v' && attr.name[1] === '-') {
      continue
    }
    if (attr.name === 'id' || attr.name === 'class') {
      continue
    }
    let val: PropValue = attr.value
    let name = attr.name
    if (attr.name[0] === ':') {
      name = attr.name.substring(1)
      if (
        attr.value[0] === '{' ||
        attr.value[0] === '[' ||
        isNumber.test(attr.value)
      ) {
        val = JSON.parse(attr.value)
      } else if (attr.value === 'true') {
        val = true
      } else if (attr.value === 'false') {
        val = false
      }
    }
    props[snakeToCamel(name)] = val
  }
  return props
}

function getSlotData(el: HTMLElement): DjangoSlots {
  const slotEls = el.querySelectorAll('template')
  const slots: DjangoSlots = {}

  for (const slotEl of slotEls) {
    const slotName = slotEl.dataset.slot

    if (slotName) {
      slots[slotName] = Object.freeze(
        (slotEl.cloneNode(true) as HTMLTemplateElement).content
      )
    }
  }
  return slots
}

function getOtherAttrs(el: HTMLElement): OtherAttrs {
  const other: OtherAttrs = {
    class: {}
  }
  if (el.className) {
    const classes = el.className.split(' ')
    classes.forEach((c) => {
      other.class[c.trim()] = true
    })
  }
  return other
}

function createAppWithProps(el: string | HTMLElement, component: VueElement) {
  /*
    Fake VueJS compiler which does only the following:
    - takes class and id attributes and sets them on new element
    - takes other attributes of element and makes them to props object
    - takes containing slot content elements, which are accessible using <django-slot>
  */
  let checkedEl: HTMLElement | null = null
  if (typeof el === 'string') {
    checkedEl = document.querySelector(el)
  } else {
    checkedEl = el
  }
  if (checkedEl === null) {
    return
  }
  const props = getPropsFromElement(checkedEl)
  const slotData = getSlotData(checkedEl)

  const otherAttrs = getOtherAttrs(checkedEl)

  const app = createApp(component, {
    ...props,
    ...otherAttrs
  })

  app.provide('django-slots', slotData)

  return app
}

export { createAppWithProps }
