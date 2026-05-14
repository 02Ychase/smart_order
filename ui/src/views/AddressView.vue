<template>
  <section class="address-view">
    <div class="modal-header">
      <div>
        <h2>地址管理</h2>
        <p class="subtitle">管理你的收货地址</p>
      </div>
      <button v-if="!formVisible" class="btn-ghost btn-sm" data-test="open-create-address" @click="openCreateForm">+ 新增</button>
      <button class="close-x" @click="$emit('close')">×</button>
    </div>

    <div class="modal-body mt-scroll">
      <!-- Form -->
      <form v-if="formVisible" class="form-block" data-test="address-form" @submit.prevent="submitAddress">
        <input v-model="addressForm.label" data-test="address-label-input" type="hidden" />
        <div class="label-chips">
          <span
            v-for="l in ['家', '公司', '其他']"
            :key="l"
            class="label-chip"
            :class="{ active: addressForm.label === l }"
            @click="addressForm.label = l"
          >{{ l }}</span>
        </div>
        <div class="field">
          <label>联系人</label>
          <input v-model="addressForm.contact_name" data-test="address-contact-name-input" placeholder="王小明" />
        </div>
        <div class="field">
          <label>手机号</label>
          <input v-model="addressForm.contact_phone" data-test="address-contact-phone-input" placeholder="138 0000 0000" />
        </div>
        <div class="field-row">
          <div class="field">
            <label>城市</label>
            <input v-model="addressForm.city" data-test="address-city-input" placeholder="上海市" />
          </div>
          <div class="field">
            <label>区县</label>
            <input v-model="addressForm.district" data-test="address-district-input" placeholder="徐汇区" />
          </div>
        </div>
        <div class="field">
          <label>详细地址</label>
          <input v-model="addressForm.detail_address" data-test="address-detail-input" placeholder="街道、楼栋、门牌" />
        </div>
        <div class="field-row">
          <div class="field">
            <label>经度</label>
            <input v-model.number="addressForm.longitude" data-test="address-longitude-input" placeholder="121.45" />
          </div>
          <div class="field">
            <label>纬度</label>
            <input v-model.number="addressForm.latitude" data-test="address-latitude-input" placeholder="31.22" />
          </div>
        </div>
        <label class="default-toggle">
          <input v-model="addressForm.is_default" data-test="address-default-input" type="checkbox" />
          设为默认地址
        </label>
        <div class="form-actions">
          <button class="btn-cta" data-test="address-submit" type="submit">保存地址</button>
          <button class="btn-ghost" data-test="address-cancel" type="button" @click="closeForm">取消</button>
        </div>
      </form>

      <!-- List -->
      <p v-if="loading" class="state-text">加载中...</p>
      <p v-else-if="errorMessage" class="state-text state-text--error">{{ errorMessage }}</p>
      <div v-else-if="!addresses.length && !formVisible" class="state-text">暂无地址</div>

      <article v-for="address in addresses" v-else :key="address.id" class="address-card">
        <div class="card-main">
          <div class="card-top">
            <strong>{{ address.contact_name }}</strong>
            <span class="card-phone">{{ address.contact_phone }}</span>
            <span class="tag tag--orange">{{ address.label || '其他' }}</span>
            <span v-if="address.is_default" class="tag tag--default">默认</span>
          </div>
          <p class="card-addr">{{ address.city }}{{ address.district }} {{ address.detail_address }}</p>
        </div>
        <div class="card-actions">
          <button v-if="!address.is_default" class="mini-btn" :data-test="`set-default-${address.id}`" @click="markDefault(address.id)">设为默认</button>
          <button class="mini-btn" :data-test="`edit-address-${address.id}`" @click="startEdit(address)">编辑</button>
          <button class="mini-btn" @click="removeAddress(address.id)">删除</button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { createAddress, deleteAddress, listAddresses, setDefaultAddress, updateAddress } from '../api/address'

defineEmits(['close'])

const addresses = ref([])
const loading = ref(true)
const errorMessage = ref('')
const formVisible = ref(false)
const addressForm = reactive({
  id: null,
  label: '家',
  contact_name: '',
  contact_phone: '',
  city: '',
  district: '',
  detail_address: '',
  longitude: 121.45,
  latitude: 31.22,
  is_default: false,
})

const resetForm = () => {
  Object.assign(addressForm, {
    id: null,
    label: '家',
    contact_name: '',
    contact_phone: '',
    city: '',
    district: '',
    detail_address: '',
    longitude: 121.45,
    latitude: 31.22,
    is_default: false,
  })
}

const closeForm = () => {
  formVisible.value = false
  resetForm()
}

const openCreateForm = () => {
  resetForm()
  formVisible.value = true
}

const loadAddresses = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    addresses.value = await listAddresses()
  } catch (error) {
    errorMessage.value = error?.message || '加载失败，请稍后再试'
  } finally {
    loading.value = false
  }
}

const markDefault = async (addressId) => {
  await setDefaultAddress(addressId)
  await loadAddresses()
}

const startEdit = async (address) => {
  Object.assign(addressForm, address)
  formVisible.value = true
}

const submitAddress = async () => {
  const payload = {
    label: addressForm.label,
    contact_name: addressForm.contact_name,
    contact_phone: addressForm.contact_phone,
    city: addressForm.city,
    district: addressForm.district,
    detail_address: addressForm.detail_address,
    longitude: Number(addressForm.longitude),
    latitude: Number(addressForm.latitude),
    is_default: addressForm.is_default,
  }

  if (addressForm.id) {
    await updateAddress(addressForm.id, payload)
  } else {
    await createAddress(payload)
  }

  await loadAddresses()
  closeForm()
}

const removeAddress = async (addressId) => {
  await deleteAddress(addressId)
  await loadAddresses()
}

onMounted(loadAddresses)
</script>

<style scoped>
.address-view {
  display: flex;
  flex-direction: column;
  max-height: 78vh;
  color: var(--so-ink-1);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--so-border-1);
  gap: 12px;
}

.modal-header h2 { margin: 0; font-size: 18px; font-weight: 700; }
.subtitle { margin: 4px 0 0; color: var(--so-ink-4); font-size: 13px; }

.close-x {
  width: 28px; height: 28px; border: none; background: transparent;
  cursor: pointer; color: var(--so-ink-4); font-size: 22px; line-height: 1; padding: 0;
}

.modal-body { flex: 1; overflow-y: auto; padding: 12px 24px 24px; }

/* Form */
.form-block {
  padding: 16px;
  background: var(--so-yellow-faint);
  border-radius: var(--so-r-md);
  margin-bottom: 16px;
}

.label-chips { display: flex; gap: 8px; margin-bottom: 12px; }

.label-chip {
  display: inline-flex; align-items: center;
  height: 28px; padding: 0 14px;
  border-radius: var(--so-r-pill);
  font-size: 13px; font-weight: 500;
  cursor: pointer;
  background: var(--so-surface);
  color: var(--so-ink-2);
  border: 1px solid var(--so-border-2);
  transition: all 0.15s;
}

.label-chip.active {
  background: var(--so-orange-soft);
  color: var(--so-orange);
  border-color: var(--so-orange);
}

.field { margin-bottom: 12px; }
.field label { display: block; font-size: 13px; color: var(--so-ink-3); margin-bottom: 6px; }
.field input {
  width: 100%; height: 40px; padding: 0 14px;
  border: 1px solid var(--so-border-2); border-radius: var(--so-r-sm);
  font-size: 14px; color: var(--so-ink-1); outline: none; box-sizing: border-box;
}

.field-row { display: flex; gap: 10px; }
.field-row .field { flex: 1; }

.default-toggle {
  display: flex; gap: 8px; align-items: center;
  font-size: 13px; color: var(--so-ink-2);
  accent-color: var(--so-orange);
}

.form-actions { display: flex; gap: 10px; margin-top: 14px; }

/* Address card */
.address-card {
  padding: 14px;
  background: var(--so-surface);
  border: 1px solid var(--so-border-1);
  border-radius: var(--so-r-md);
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
}

.card-main { flex: 1; min-width: 0; }

.card-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.card-top strong { color: var(--so-ink-1); font-size: 15px; }
.card-phone { color: var(--so-ink-4); font-size: 13px; }

.tag {
  display: inline-flex; align-items: center;
  height: 18px; padding: 0 8px;
  border-radius: var(--so-r-pill);
  font-size: 10px; font-weight: 600;
}

.tag--orange { background: var(--so-orange-soft); color: var(--so-orange); }
.tag--default { background: var(--so-surface-line); color: var(--so-ink-4); }

.card-addr { margin: 6px 0 0; font-size: 13px; color: var(--so-ink-2); }

.card-actions {
  display: flex; flex-direction: column; align-items: flex-end; gap: 4px;
}

.mini-btn {
  background: transparent; border: none; cursor: pointer;
  font-size: 12px; color: var(--so-ink-3); padding: 2px 6px;
}

.mini-btn:hover { color: var(--so-orange); }

/* Buttons */
.btn-cta {
  height: 36px; padding: 0 22px;
  background: var(--so-orange); color: #fff;
  border: none; border-radius: var(--so-r-pill);
  font-size: 13px; font-weight: 600; cursor: pointer;
}

.btn-ghost {
  height: 36px; padding: 0 18px;
  background: var(--so-surface); color: var(--so-ink-2);
  border: 1px solid var(--so-border-2); border-radius: var(--so-r-pill);
  font-size: 13px; cursor: pointer;
}

.btn-sm { height: 30px; padding: 0 14px; font-size: 12px; }

.state-text { padding: 60px 0; text-align: center; color: var(--so-ink-4); font-size: 14px; }
.state-text--error { color: var(--so-red); }
</style>
