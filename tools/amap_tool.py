"""
高德地图工具模块

该模块提供高德地图的API调用功能，
用于获取地图上的地点信息、路线规划等
"""

from typing import Dict, List, Any, Literal, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
import json
import logging
from dotenv import load_dotenv
import os
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    encoding="utf-8",
)
logger = logging.getLogger(__name__)
load_dotenv(override=True)

PathInputMode = Literal["1", "2", "3"]  # 外部用
PathMode = Literal["walking", "electrobike", "driving"]  # 内部用


@dataclass  # 自动生成init方法，快速对对象进行一些赋值，减少重复工作
class AmapConfig:
    AMAP_API_KEY = os.getenv("AMAP_API_KEY")
    MERCHANT_LONGITUDE = os.getenv("MERCHANT_LONGITUDE")
    MERCHANT_LATITUDE = os.getenv("MERCHANT_LATITUDE")
    DELIVERY_RADIUS = int(os.getenv("DELIVERY_RADIUS"))
    MERCHANT_LATITUDE = os.getenv("MERCHANT_LATITUDE")
    DEFAULT_PATH_MODE = os.getenv("DEFAULT_PATH_MODE")

    def __post_init__(self):
        """自动调用"""
        if self.AMAP_API_KEY is None:
            raise ValueError("AMAP_API_KE不存在")
        pass


class PathModelConverter:
    """路径模式转换"""

    MODE_MAPPING = {"1": "walking", "2": "electrobike", "3": "driving"}

    @classmethod
    def to_mode(cls, mode_input: Union[PathInputMode]) -> PathMode:
        """将输入的模式转换为内部用的模式"""
        if mode_input in cls.MODE_MAPPING:
            return cls.MODE_MAPPING[mode_input]
        else:
            raise ValueError(
                f"不支持的路径格式:{mode_input},支持的模式:{list(cls.MODE_MAPPING.keys())}"
            )


# 创建配置实例
config = AmapConfig()


def create_session_with_retries():
    """创建带重试机制的requests会话"""
    # 1.创建session对象
    session = requests.Session()
    # 2.定义重试策略
    retry_rule = Retry(
        total=3,  # 总共重试次数，不包括第一次
        backoff_factor=1,  # 退避因子(backoff_factor)*2^(重试次数-1)
        status_forcelist=[
            429,  # 429:请求过快
            500,  #  5xx系列状态码都是服务内部出现各种问题
            502,
            503,
            504,
            505,
        ],
    )

    # 3. 创建HttpAdapter(自定义http请求行为)
    adapter = HTTPAdapter(max_retries=retry_rule)

    # 4.将adapter挂载到session中
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def safe_request(base_url: str, params: dict):
    """安全发送http请求，处理重试和ssl降级

    Args:
        base_url (str): url
        params (dict): 参数
    """
    # https(加密)协议请求：1.ssl协议过期了->降级为http请求 2.https协议的网络连接没建立，建立网络连接超时了，读取超时
    # 1.获取到带重试机制的session对象
    session = create_session_with_retries()
    try:
        # 发送请求
        response = session.get(url=base_url, params=params, timeout=10)

        response.raise_for_status()

        return response.json()  # 将网络传输的对象反序列化为字典对象 [字节->对象]反序列化：方便应用程序处理  [对象->字节]序列化：网络传输，内存读写

    except requests.exceptions.SSLError as e:
        try:
            http_request_url = base_url.replace("https", "http")

            response = session.get(url=http_request_url, params=params, timeout=10)

            response.raise_for_status()

            return response.json()
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException("Http协议请求发送失败")

    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException("Https协议请求发送失败")

    # 反序列化失败
    except json.decoder.JSONDecodeError as e:
        logger.error(f"解析响应失败:{e}")
        raise json.decoder.JSONDecodeError("json解析失败")


def geocode_address(address: str):
    """将地址转换为经纬度坐标

    Args:
        address (str): 地址
    """
    try:
        # 1. 构建请求的url
        base_url = "https://restapi.amap.com/v3/geocode/geo"
        # 2. 构建请求的参数
        params = {"address": address, "key": os.getenv("AMAP_API_KEY")}
        # 3. 发送请求,得到响应
        response = safe_request(base_url=base_url, params=params)
        # 4. 解析结果
        # 失败
        if response["status"] != "1":
            return {"success": False, "messages": response["info"]}
        # 成功
        geocodes = response["geocodes"][0]
        return {
            "success": True,
            "formatted_address": geocodes["formatted_address"],
            "location": geocodes["location"],
        }

    except Exception as e:
        logger.error(f"调用高德地图进行地理位置编码失败:{e}")


def calculate_distance(
    origin_location: str,
    destination_location: str,
    path_mode_input: PathInputMode = "2",
) -> Dict[str, Any]:
    """给定路径模式计算起点和终点之间的距离和预计时间

    Args:
        origin_location (str): 起点
        destination_location (str): 终点
        path_mode (PathInputMode, optional): 路径模式. Defaults to "2".
    """
    try:
        # 将外部模式转换为内部用的
        inner_mode = PathModelConverter.to_mode(path_mode_input)

        # 1.校验高德的API_KEY
        if config.AMAP_API_KEY is None:
            raise ValueError("AMAP_API_KEY不存在")

        # 2.构建请求的URL
        path_endpoints = {
            "walking": "https://restapi.amap.com/v5/direction/walking",
            "electrobike": "https://restapi.amap.com/v5/direction/electrobike",
            "driving": "https://restapi.amap.com/v5/direction/driving",
        }
        # 3.构建params

        params = {
            "key": config.AMAP_API_KEY,
            "origin": origin_location,
            "destination": destination_location,
        }
        if inner_mode == "driving":
            params["show_fields"] = "cost"

        # 4.发送请求获取响应
        response = safe_request(base_url=path_endpoints[inner_mode], params=params)

        # 5.解析结果
        if response.get("status") == "1":
            path = response["route"]["paths"][0]
            duration = (
                int(path["duration"])
                if inner_mode == "electrobike"
                else int(path["cost"]["duration"])
            )
            return {
                "distance": int(path["distance"]),  # 两点之间距离
                "duration": duration,  # 所耗时间
                "status": "success",
            }

        return {"status": "fail", "message": "高德地图距离解析失败"}
    except Exception as e:
        logging.error(f"调用高德地图进行路径规划编码失败:{e}")
        raise e


def check_delivery_range(
    address: str, path_mode_input: PathInputMode = None
) -> Dict[str, Any]:
    """检查地址是否在配送范围内

    Args:
        address: 用户输入的地址

        path_mode_input: 路径模式，支持 "1"(walking), "2"(bicycling), "3"(driving)。如果为None则使用配置的默认模式

    Returns:
          包含检查结果的 Dict 对象
    """
    try:
        # 获取起点坐标，餐厅地址
        origin_location=f"{config.MERCHANT_LONGITUDE},{config.MERCHANT_LATITUDE}"
        geocode_result = geocode_address(address=address)
        if geocode_result["success"] is False:
            return {"status": "fall", "message": geocode_result["message"]}
        calculate_distance_result = calculate_distance(
            origin_location=origin_location,
            destination_location=geocode_result["location"],
            path_mode_input=path_mode_input or config.DEFAULT_PATH_MODE,
        )  # or运算符，返回第一个真值或者最后一个假值

        if calculate_distance_result["status"] == "fail":
            return {"status": "fail", "message": calculate_distance_result["message"]}

        # 返回两点之间距离、时间、是否在配送范围之内
        distance = calculate_distance_result["distance"] #多少米 2000
        distance_km=round(distance/1000,2)

        in_range=distance<=config.DELIVERY_RADIUS

        return {
            "status": "success",
            "in_range": in_range,  # 是否在配送范围
            "distance": distance_km, # 距离
            "duration": calculate_distance_result["duration"],
            "formatted_address": geocode_result["formatted_address"],
            "message": (
                f"配送地址：{geocode_result['formatted_address']}\n"
                f"配送距离：{distance_km:.2f}公里\n"
                f"配送状态：{'在配送范围内' if in_range else '超出配送范围'}"
            ),
        }
    except Exception as e:
        logger.error(f"配送范围查询失败:{e}")
        raise e


if __name__ == "__main__":
    # print(geocode_address("安徽大学磬苑校区")) #'location': '117.190995,31.759296'

    # print(geocode_address("安徽大学金寨路校区"))  #'location': '117.211965,31.770207'

    # print(
    #     calculate_distance(
    #         origin_location="117.211965,31.770207",
    #         destination_location="117.190995,31.759296",
    #         path_mode_input="3",
    #     )
    # )
    test_address = "武汉市洪山区光谷天地" #  测试地址
    print("\n=== 测试不同路径模式 ===")
    # 测试步行模式 (1)
    print("\n1. 步行模式测试:")
    result1 = check_delivery_range(test_address, "1")
    minutes = result1['duration'] // 60
    seconds = result1['duration'] % 60
    print(f"步行模式距离: {result1['distance']}公里 时间: {result1['duration']}秒 ({minutes}分{round(seconds, 2)}秒)")
    print(f"是否在配送范围内: {result1['message']}")
    
    # 测试骑行模式 (2)
    print("\n2. 骑行模式测试:")
    result2 = check_delivery_range(test_address, "2")
    minutes = result1['duration'] // 60
    seconds = result1['duration'] % 60
    print(f"步行模式距离: {result2['distance']}公里 时间: {result2['duration']}秒 ({minutes}分{round(seconds, 2)}秒)")
    print(f"是否在配送范围内: {result2['message']}")

    # 测试驾车模式 (3)
    print("\n3. 驾车模式测试:")
    result3 = check_delivery_range(test_address, "3")
    minutes = result3['duration'] // 60
    seconds = result3['duration'] % 60
    print(f"步行模式距离: {result3['distance']}公里 时间: {result3['duration']}秒 ({minutes}分{round(seconds, 2)}秒)")
    print(f"是否在配送范围内: {result3['message']}")