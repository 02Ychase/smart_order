const labels = {
  pending_payment: '待支付',
  paid: '已支付',
  preparing: '备餐中',
  delivering: '配送中',
  completed: '已完成',
  cancelled: '已取消',
}

export function formatOrderStatus(status) {
  return labels[status] || status
}
