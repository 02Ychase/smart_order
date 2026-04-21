<template>
  <section class="address-dialog-view">
    <header class="dialog-header">
      <h2>地址管理</h2>
      <p>新增、编辑，并维护默认收货地址。</p>
    </header>

    <p v-if="loading">加载中...</p>
    <p v-else-if="errorMessage">{{ errorMessage }}</p>
    <el-empty v-else-if="!addresses.length" description="暂无地址" />
    <template v-else>
      <article v-for="address in addresses" :key="address.id" class="address-card">
        <div>
          <strong>{{ address.label }}</strong>
          <span v-if="address.is_default">默认地址</span>
          <p>{{ address.contact_name }} · {{ address.contact_phone }}</p>
          <p>{{ address.city }}{{ address.district }} · {{ address.detail_address }}</p>
        </div>
        <div class="address-actions">
          <el-button :data-test="`set-default-${address.id}`" text @click="markDefault(address.id)">设为默认</el-button>
          <el-button text @click="startEdit(address)">编辑</el-button>
          <el-button text @click="removeAddress(address.id)">删除</el-button>
        </div>
      </article>
    </template>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { deleteAddress, listAddresses, setDefaultAddress, updateAddress } from '../api/address'

const addresses = ref([])
const loading = ref(true)
const errorMessage = ref('')
const editingAddress = reactive({
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
  Object.assign(editingAddress, address, { detail_address: `${address.detail_address} 9 楼` })
  await updateAddress(address.id, editingAddress)
  await loadAddresses()
}

const removeAddress = async (addressId) => {
  await deleteAddress(addressId)
  await loadAddresses()
}

onMounted(loadAddresses)
</script>
