<script setup>
import { toastState, dismiss } from '@/composables/useToast'
import AppIcon from './AppIcon.vue'

const iconOf = (type) => ({ success: 'check-circle', error: 'x-circle', warn: 'alert', info: 'info' }[type] || 'info')
</script>

<template>
  <Teleport to="body">
    <div class="toast-host">
      <TransitionGroup name="toast">
        <div v-for="item in toastState.items" :key="item.id" class="toast" :class="`toast-${item.type}`">
          <AppIcon :name="iconOf(item.type)" :size="17" />
          <span class="msg">{{ item.message }}</span>
          <button class="close" type="button" aria-label="关闭" @click="dismiss(item.id)">
            <AppIcon name="close" :size="13" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-host {
  position: fixed; top: 78px; left: 50%; transform: translateX(-50%);
  z-index: 90; display: flex; flex-direction: column; gap: 8px; align-items: center;
  pointer-events: none;
}
.toast {
  pointer-events: auto;
  display: flex; align-items: center; gap: 9px;
  min-width: 200px; max-width: min(520px, 88vw);
  padding: 10px 12px 10px 14px;
  background: #fff; border-radius: 10px;
  box-shadow: var(--shadow);
  border: 1px solid var(--line);
  font-size: 13.5px; color: var(--ink);
}
.toast .msg { flex: 1; }
.toast .close { border: none; background: none; color: var(--muted-2); padding: 2px; line-height: 0; }
.toast .close:hover { color: var(--ink-2); }
.toast-success { border-color: #c9ecd9; }
.toast-success .app-icon { color: var(--ok); }
.toast-error { border-color: #f6cdc9; }
.toast-error .app-icon { color: var(--danger); }
.toast-warn { border-color: #f8dfb8; }
.toast-warn .app-icon { color: var(--warn); }
.toast-info .app-icon { color: var(--info); }

.toast-enter-active, .toast-leave-active { transition: all .22s cubic-bezier(.22,.61,.36,1); }
.toast-enter-from { opacity: 0; transform: translateY(-8px) scale(.97); }
.toast-leave-to { opacity: 0; transform: translateY(-4px) scale(.98); }
</style>
