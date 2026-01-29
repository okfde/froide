import { ref } from 'vue'

export function useIsDesktop() {
  const desktopBreakpoint = getComputedStyle(document.body).getPropertyValue(
    '--bs-breakpoint-md'
  )
  const isDesktopMediaQueryList = window.matchMedia(
    `(min-width: ${desktopBreakpoint})`
  )
  const isDesktop = ref(isDesktopMediaQueryList.matches)
  isDesktopMediaQueryList.addEventListener(
    'change',
    (mqle: MediaQueryListEvent): void => {
      isDesktop.value = mqle.matches
    }
  )
  return { isDesktop }
}
