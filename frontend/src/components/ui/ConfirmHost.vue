<script setup>
import { confirmState, settleConfirm } from '@/composables/useConfirm'
import AppIcon from './AppIcon.vue'
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="confirmState.open" class="modal-mask" @click.self="settleConfirm(false)">
        <div class="modal confirm" role="alertdialog" aria-modal="true">
          <div class="body">
            <div class="icon" :class="{ danger: confirmState.danger }">
              <AppIcon :name="confirmState.danger ? 'alert' : 'info'" :size="22" />
            </div>
            <div class="content">
              <h3>{{ confirmState.title }}</h3>
              <p v-if="confirmState.message" class="text-sm text-sub">{{ confirmState.message }}</p>
            </div>
          </div>
          <div class="foot">
            <button class="btn" type="button" @click="settleConfirm(false)">{{ confirmState.cancelText }}</button>
            <button
              class="btn"
              :class="confirmState.danger ? 'btn-primary' : 'btn-dark'"
              type="button"
              @click="settleConfirm(true)"
            >
              {{ confirmState.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.confirm { width: min(420px, 100%); }
.body { display: flex; gap: 14px; padding: 24px 24px 8px; }
.icon {
  width: 42px; height: 42px; border-radius: 12px; flex: none;
  display: grid; place-items: center;
  background: var(--info-soft); color: var(--info);
}
.icon.danger { background: var(--danger-soft); color: var(--danger); }
.content h3 { font-size: 16px; margin-bottom: 4px; }
.foot { display: flex; justify-content: flex-end; gap: 10px; padding: 18px 24px 22px; }
</style>
