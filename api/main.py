"""
智能点餐助手主程序 FastAPI 接口

1. 定义 FastAPI 应用实例
2. 提供三个主要接口：
2.1 POST /chat - 智能对话接口
2.2 POST /delivery - 配送查询接口
2.3 GET /menu/list - 菜品列表接口
"""

from fastapi import FastAPI, HTTPException
from pydantic import Field, BaseModel
from typing import List,Dict,Any,Literal,Optional
from service.diancan_service import get_menu,check_delivery_range,chat_with_assistant
from tools.amap_tool import PathInputMode
import logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

app = FastAPI(
    title="智能点餐助手的API接口",
    description="智能点餐助手程序主要暴露三个接口：智能对话接口、配送查询接口、菜品列表接口",
)


# 定义数据模型
class MenuListResponse(BaseModel):
    """菜品列表响应"""

    success: bool # 有数据 True
    menu_items: List[Dict]  # 菜品列表
    count: int  # 菜品数量
    messages: str  # 响应消息提示

class DeliveryRequest(BaseModel):
    """配送查询请求"""
    address: str
    travel_mode: PathInputMode = "2"  # 1=步行, 2=骑电动车, 3=驾车

class ChatRequest(BaseModel):
    """智能对话请求"""
    query: str




# 配送查询响应数据模型
class DeliveryResponse(BaseModel):
    """配送查询响应"""
    success: bool  # 成功(True) or 失败的标识（False）
    in_range: bool #  配送是否在配送范围内(True False)
    distance: float # 配送距离(公里 km)
    formatted_address: str # 格式化地址
    duration:float # 配送时间（秒）
    message: str  # (前端要展示的配送完整消息内容)
    travel_mode: PathInputMode # 配送模式 (1:步行 2:骑电动车 3:驾车)
    input_address: str # 输入原始内容

# 定义对话响应模型
class ChatResponse(BaseModel):
    """智能对话响应"""
    success: bool  # 成功失败表示
    query: str  # 原始查询内容
    response: Optional[str] = None  # 响应内容
    recommendation: Optional[str] = None  # 推荐内容
    menu_ids: Optional[List[str]] = None  # 推荐的菜品id


@app.get("/menu/list", response_model=MenuListResponse)
async def menu_list_endpoint():
    """菜品列表区域展示"""
    # 调用service中的方法
    menu_items = get_menu()

    if not menu_items:
        return MenuListResponse(
            success=False,
            menu_items=[],
            count=0,
            messages="获取不到菜品列表，菜品列表为空"
        )
    else:
        return MenuListResponse(
            success=True,
            menu_items=menu_items,
            count=len(menu_items),
            messages=f"成功获取到{len(menu_items)}个菜品"
        )
@app.post("/delivery", response_model=DeliveryResponse)

@app.post("/delivery", response_model=DeliveryResponse)
async def delivery_endpoint(request: DeliveryRequest):
    """
    配送查询接口
    
    检查指定地址是否在配送范围内
    """
    try:
        # 调用配送查询服务
        check_delivery_range_result = check_delivery_range(request.address, request.travel_mode)
        
        if check_delivery_range_result["status"] == "success":
            return DeliveryResponse(
                success=True,
                in_range=check_delivery_range_result["in_range"],
                distance=check_delivery_range_result["distance"],
                formatted_address=check_delivery_range_result["formatted_address"],
                duration=check_delivery_range_result["duration"],
                message=check_delivery_range_result["message"],
                travel_mode=request.travel_mode,
                input_address=request.address
            )
        else:
            return DeliveryResponse(
                success=False,
                in_range=False,
                distance=0.0,
                formatted_address=request.address,
                message=check_delivery_range_result["message"],
                duration=0.0,
                travel_mode=request.travel_mode,
                input_address=request.address
            )
            
    except Exception as e:
        logger.error(f"配送范围查询失败:{e}")
        return DeliveryResponse(
            success=False,
            message=f"配送范围查询失败:{e}"
        )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    智能对话接口
    
    接收用户问题，返回智能助手回复
    """
    try:
        # 调用智能对话服务
        result = chat_with_assistant(request.query)
        
        # 处理不同类型的返回值
        if isinstance(result, dict) and "recommendation" in result and "menu_ids" in result:
            # 菜品推荐返回
            return ChatResponse(
                success=True,
                query=request.query,
                recommendation=result["recommendation"],
                menu_ids=result["menu_ids"]
            )
        else:
            # 普通文本回复
            return ChatResponse(
                success=True,
                query=request.query,
                response=str(result)
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"智能对话服务失败: {str(e)}"
        )
    
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "AiMenu API"}