
from rag.rag_service import RagSummarizeService
import os
import random
import re
import json
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from utils.logger_handler import logger
from utils.config_handler import agent_conf
from utils.path_tool import get_abs_path1
from langchain.tools import tool

_IPV4_RE = re.compile(
    r"^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\."
    r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\."
    r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\."
    r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$"
)


def _is_valid_ipv4(ip: str) -> bool:
    return bool(_IPV4_RE.match(ip or ""))


def _get_public_ip()->str:
    ip_source=agent_conf.get("public_ip_sources",
    ["https://ipv4.icanhazip.com"],)
    timeout=agent_conf.get("public_ip_timeout",3)
    for source in ip_source:
        try:
            with urlopen(source,timeout=timeout) as resp:
                ip=resp.read().decode("utf-8").strip()
                print(ip)
                if _is_valid_ipv4(ip):
                    return ip
        except Exception as e:
            logger.error(f"无法获取ip地址,{str(e)}")
    return ""

GAODE_BASE_URL = agent_conf.get("gaode_base_url")
GAODE_TIMEOUT = float(agent_conf.get("gaode_timeout"))

def _gao_get(path:str,params:dict)->dict:
    gaode_key=agent_conf.get("gaode_key")
    if not gaode_key:
        raise ValueError("agent.yml中未配置gaode_key")
    query=dict(params)
    query["key"]=gaode_key
    print(query)
    url=f"{GAODE_BASE_URL}{path}?{urlencode(query)}"

    try:
        with urlopen(url,timeout=GAODE_TIMEOUT) as resp:
            data=resp.read().decode("utf-8")
            print("data",type(data),data,)
            return json.loads(data)
    except HTTPError as e:
        raise RuntimeError(f"高德HTTP错误: {e.code}") from e
    except URLError as e:
        raise RuntimeError(f"高德网络错误: {e.reason}") from e
    except Exception as e:
        raise RuntimeError(f"高德请求异常: {str(e)}") from e

def _resolve_city_to_adcode(city: str) -> tuple[str, str]:
    geo = _gao_get("/v3/geocode/geo", {"address": city})
    if geo.get("status") != "1" or not geo.get("geocodes"):
        raise RuntimeError(f"城市解析失败: {geo.get('info', 'unknown')}")
    first = geo["geocodes"][0]
    adcode = first.get("adcode")
    if not adcode:
        raise RuntimeError(f"城市解析成功但未返回adcode")
    resolved_city=first.get("city") or first.get("district") or city
    if isinstance(resolved_city,list):
        resolved_city="".join(resolved_city)
    return str(resolved_city), str(adcode)

#@tool(description="获取指定城市的天气，以消息字符串的形式返回")
def get_weather(city: str) -> str:
    if not city or not city.strip():
        return "未提供城市名称，无法查询天气"

    try:
        resolved_city, adcode = _resolve_city_to_adcode(city)
        weather = _gao_get(
            "/v3/weather/weatherInfo",
            {"city": adcode, "extensions": "base"}
        )
        print("weather:",type(weather),weather)
        if weather.get("status") != "1" or not weather.get("lives"):
            return f"城市{resolved_city}天气查询失败,{weather.get("info","unknown")}"

        live=weather.get("lives")[0]
        condition=live.get("weather","")
        temperature=live.get("temperature","")
        humidity=live.get("humidity","")
        wind_direction=live.get("winddirection","")
        wind_power=live.get("windpower","")
        report_time=live.get("reporttime","")

        return (
            f"城市{resolved_city}天气为{condition}，气温{temperature}摄氏度，"
            f"空气湿度{humidity}%，{wind_direction}风{wind_power}级，"
            f"数据发布时间{report_time}。"
        )
    except Exception as e:
        logger.error(f"[get_weather]天气查询失败 city={city} err={str(e)}")
        return f"城市{city}天气查询失败，请稍后重试"


#@tool获取用户所在城市的名称，以纯字符串形式返回
def get_user_location() -> str:
    try:
        public_ip = _get_public_ip()
        params = {"ip": public_ip} if public_ip else {}
        ip_info = _gao_get("/v3/ip", params)

        if ip_info["status"]!= "1" :
            logger.warning(
                f"[get_user_location]高德返回失败 info={ip_info.get('info')} "
                f"infocode={ip_info.get('infocode')} ip={public_ip or 'none'}"
            )
            return "未知城市"
        city=ip_info.get("city","")
        province=ip_info.get("province","")


        if isinstance(city, list):
            city = "".join(city)
        if isinstance(province, list):
            province = "".join(province)

        city = str(city).strip()
        province = str(province).strip()

        if city:
            return city
        if province:
            return province
        logger.warning(f"[get_user_location]空城市信息,info={ip_info.get("info")},"
                       f"infocode={ip_info.get("infocode")},ip={public_ip or "None"},raw={ip_info}")
        return "未知城市"

    except Exception as e:
        logger.error(f"[get_user_location]定位失败 err={str(e)}")
        return "未知城市"

if __name__=='__main__':
    public_ip = _get_public_ip()
    params = {"params": public_ip} if public_ip else {}
    city=get_user_location()
    weather=get_weather(city)
    print(weather)
    #ip_info = _gao_get("/v3/ip", params)