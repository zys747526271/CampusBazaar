import { reactive } from 'vue'

/** 轻提示队列（全局单例，由 ToastHost 渲染） */
export const toastState = reactive({ items: [] })

let seed = 0

export function toast(message, type = 'info', duration = 2600) {
  if (!message) return
  const id = ++seed
  toastState.items.push({ id, message, type })
  window.setTimeout(() => dismiss(id), duration)
  return id
}

export function dismiss(id) {
  const index = toastState.items.findIndex((item) => item.id === id)
  if (index >= 0) toastState.items.splice(index, 1)
}

export const toastSuccess = (msg) => toast(msg, 'success')
export const toastError = (msg) => toast(msg, 'error', 3400)
export const toastWarn = (msg) => toast(msg, 'warn', 3000)

export function useToast() {
  return { toast, toastSuccess, toastError, toastWarn, toastState, dismiss }
}
