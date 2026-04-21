const CATEGORY_COVER_STYLES = {
  '湘菜': 'linear-gradient(135deg, #ffe1d6, #ffb59c)',
  '轻食': 'linear-gradient(135deg, #e2f5ef, #b9e6db)',
  '咖啡甜品': 'linear-gradient(135deg, #efe7ff, #dccbff)',
  '炸鸡汉堡': 'linear-gradient(135deg, #fff0d8, #ffd18c)',
  '粥面': 'linear-gradient(135deg, #fff4dc, #f3d8aa)',
  '日韩料理': 'linear-gradient(135deg, #ffe7ef, #ffc6d8)',
  '麻辣烫': 'linear-gradient(135deg, #ffe0e0, #ffb0b0)',
  '披萨意面': 'linear-gradient(135deg, #ffe9cf, #ffca90)',
  '全部': 'linear-gradient(135deg, #eef5ff, #dce9ff)',
}

const CATEGORY_COVER_IMAGES = {
  '湘菜': new URL('../assets/home-covers/xiangcai.svg', import.meta.url).href,
  '轻食': new URL('../assets/home-covers/light-meal.svg', import.meta.url).href,
  '咖啡甜品': new URL('../assets/home-covers/coffee-dessert.svg', import.meta.url).href,
  '炸鸡汉堡': new URL('../assets/home-covers/fried-burger.svg', import.meta.url).href,
  '粥面': new URL('../assets/home-covers/noodles.svg', import.meta.url).href,
  '日韩料理': new URL('../assets/home-covers/jk-food.svg', import.meta.url).href,
  '麻辣烫': new URL('../assets/home-covers/malatang.svg', import.meta.url).href,
  '披萨意面': new URL('../assets/home-covers/pizza-pasta.svg', import.meta.url).href,
}

export const buildHomepageCategories = (merchants) => {
  const uniqueCategories = []

  merchants.forEach((merchant) => {
    if (merchant.homepage_category && !uniqueCategories.includes(merchant.homepage_category)) {
      uniqueCategories.push(merchant.homepage_category)
    }
  })

  return ['全部', ...uniqueCategories]
}

export const getMerchantCoverStyle = (category) => ({
  background: CATEGORY_COVER_STYLES[category] || CATEGORY_COVER_STYLES['全部'],
})

export const getMerchantCover = (category) => ({
  imageSrc: CATEGORY_COVER_IMAGES[category] || '',
  gradientStyle: getMerchantCoverStyle(category),
})
