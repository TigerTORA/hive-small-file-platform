import { onMounted, onBeforeUnmount } from 'vue'

const REFRESH_EVENT = 'datanova:refresh'

export const emitGlobalRefresh = () => {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(REFRESH_EVENT))
}

export const useGlobalRefresh = (handler: () => void) => {
  if (typeof window === 'undefined') return

  const listener = () => {
    try {
      handler()
    } catch (error) {
      console.error('[GlobalRefresh] handler failed', error)
    }
  }

  onMounted(() => {
    window.addEventListener(REFRESH_EVENT, listener)
  })

  onBeforeUnmount(() => {
    window.removeEventListener(REFRESH_EVENT, listener)
  })
}
