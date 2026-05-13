export function isWithinBusinessHours(businessHours) {
  if (!businessHours) return true

  const now = new Date()
  const currentHour = now.getHours()
  const currentMinute = now.getMinutes()
  const currentTime = currentHour * 60 + currentMinute

  const match = businessHours.match(/(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})/)
  if (!match) return true

  const startHour = parseInt(match[1], 10)
  const startMinute = parseInt(match[2], 10)
  const endHour = parseInt(match[3], 10)
  const endMinute = parseInt(match[4], 10)

  const startTime = startHour * 60 + startMinute
  const endTime = endHour * 60 + endMinute

  if (startTime <= endTime) {
    return currentTime >= startTime && currentTime <= endTime
  }
  return currentTime >= startTime || currentTime <= endTime
}

export function formatBusinessStatus(businessHours, isOpen) {
  if (!isOpen) return '已休息'
  if (!businessHours) return '营业中'
  return isWithinBusinessHours(businessHours) ? '营业中' : '休息中'
}
