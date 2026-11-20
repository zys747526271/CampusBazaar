import { reactive } from 'vue'

/** 二次确认（Promise 化），用于删除/下架/封禁等破坏性操作（PRD 8.3） */
export const confirmState = reactive({
  open: false,
  title: '',
  message: '',
  confirmText: '确认',
  cancelText: '取消',
  danger: true,
  _resolve: null
})

export function confirmAction(options = {}) {
  const {
    title = '确认操作',
    message = '',
    confirmText = '确认',
    cancelText = '取消',
    danger = true
  } = options

  Object.assign(confirmState, {
    open: true,
    title,
    message,
    confirmText,
    cancelText,
    danger
  })

  return new Promise((resolve) => {
    confirmState._resolve = resolve
  })
}

export function settleConfirm(result) {
  const resolve = confirmState._resolve
  confirmState.open = false
  confirmState._resolve = null
  if (resolve) resolve(result)
}

export function useConfirm() {
  return { confirmAction, confirmState, settleConfirm }
}
