<template>
  <section class="address-dialog-view">
    <header class="dialog-header">
      <div>
        <h2>地址管理</h2>
        <p>新增、编辑，并维护默认收货地址。</p>
      </div>
      <el-button data-test="open-create-address" @click="openCreateForm">新增地址</el-button>
    </header>

    <form v-if="formVisible" class="address-form" data-test="address-form" @submit.prevent="submitAddress">
      <input v-model="addressForm.label" data-test="address-label-input" placeholder="标签" />
      <input v-model="addressForm.contact_name" data-test="address-contact-name-input" placeholder="联系人" />
      <input v-model="addressForm.contact_phone" data-test="address-contact-phone-input" placeholder="手机号" />
      <input v-model="addressForm.city" data-test="address-city-input" placeholder="城市" />
      <input v-model="addressForm.district" data-test="address-district-input" placeholder="区县" />
      <input v-model="addressForm.detail_address" data-test="address-detail-input" placeholder="详细地址" />
      <input v-model.number="addressForm.longitude" data-test="address-longitude-input" placeholder="经度" />
      <input v-model.number="addressForm.latitude" data-test="address-latitude-input" placeholder="纬度" />
      <label class="address-default-toggle">
        <input v-model="addressForm.is_default" data-test="address-default-input" type="checkbox" />
        设为默认地址
      </label>
      <div class="address-form-actions">
        <button data-test="address-submit" type="submit">保存地址</button>
        <button data-test="address-cancel" type="button" @click="closeForm">取消</button>
      </div>
    </form>

    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <template v-else>
      <el-empty v-if="!addresses.length" description="暂无地址" />
      <article v-for="address in addresses" :key="address.id" class="address-card">
        <div>
          <strong>{{ address.label }}</strong>
          <span v-if="address.is_default">默认地址</span>
          <p>{{ address.contact_name }} · {{ address.contact_phone }}</p>
          <p>{{ address.city }}{{ address.district }} · {{ address.detail_address }}</p>
        </div>
        <div class="address-actions">
          <el-button :data-test="`set-default-${address.id}`" text @click="markDefault(address.id)">设为默认</el-button>
          <el-button :data-test="`edit-address-${address.id}`" text @click="startEdit(address)">编辑</el-button>
          <el-button text @click="removeAddress(address.id)">删除</el-button>
        </div>
      </article>
    </template>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { createAddress, deleteAddress, listAddresses, setDefaultAddress, updateAddress } from '../api/address'

const addresses = ref([])
const loading = ref(true)
const errorMessage = ref('')
const formVisible = ref(false)
const addressForm = reactive({
  id: null,
  label: '',
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
    label: '',
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
.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.address-form {
  display: grid;
  gap: 12px;
  margin: 16px 0 20px;
}

.address-form-actions {
  display: flex;
  gap: 12px;
}

.address-default-toggle {
  display: flex;
  gap: 8px;
  align-items: center;
}

.address-card + .address-card {
  margin-top: 12px;
}

.address-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
</style>
