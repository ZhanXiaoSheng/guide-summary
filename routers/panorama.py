from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import Response
from config.logging_conf import logger
from config.settings import settings
import httpx


router = APIRouter(prefix="/panorama", tags=["panorama"])

# 百度全景图API地址
PANORAMA_API_URL = settings.PANORAMA_API_URL


def get_baidu_ak():
    """获取百度地图AK，从环境变量中读取"""
    baidu_ak = getattr(settings, "PANORAMA_API_KEY", None)
    if not baidu_ak:
        logger.error("百度地图AK未配置，请在.env文件中设置PANORAMA_API_KEY")
        raise HTTPException(status_code=500, detail="百度地图服务未配置")
    return baidu_ak


# ======================
#  通用代理：代理所有百度地图相关资源
# ======================

# 百度地图允许的域名白名单
BAIDU_MAP_DOMAINS = {
    "api.map.baidu.com",
    "apimaponline0.bdimg.com",
    "apimaponline1.bdimg.com",
    "apimaponline2.bdimg.com",
    "apimaponline3.bdimg.com",
    "online1.map.bdimg.com",
    "api0.map.bdimg.com",
    "api1.map.bdimg.com",
    "api2.map.bdimg.com",
    "api3.map.bdimg.com",
    "static0.map.baidu.com",
    "static1.map.baidu.com",
    "apistatic.map.baidu.com",
    "dlswbr.baidu.com",
    "miao.baidu.com",
    "apisv1.bdimg.com",
    "apisv0.bdimg.com",
    "apisv2.bdimg.com",
    "apisv3.bdimg.com",
}


@router.get("/baidu-proxy/{path:path}")
async def proxy_baidu_resources(path: str, request: Request):
    """
    通用代理：代理所有百度地图相关资源
    使用方式：?host=目标域名&其他参数
    示例：
        /baidu-proxy/api?host=api.map.baidu.com&v=3.0&ak=xxx
        /baidu-proxy/getscript?host=api.map.baidu.com&...
        /baidu-proxy/tile?host=apimaponline1.bdimg.com&...
    """
    query_params = dict(request.query_params)
    target_host = query_params.pop("host", None)

    if not target_host:
        raise HTTPException(status_code=400, detail="Missing 'host' parameter")

    if target_host not in BAIDU_MAP_DOMAINS:
        logger.error(f"拒绝代理非法域名: {target_host}")
        raise HTTPException(status_code=403, detail="拒绝代理非法域名")

    # 构建目标 URL
    scheme = "https" if target_host == "api.map.baidu.com" else "http"
    target_url = f"{scheme}://{target_host}/{path.lstrip('/')}"

    # 请求头
    headers = {
        "Host": target_host,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://www.baidu.com/" if target_host == "api.map.baidu.com" else f"http://{target_host}/",
    }

    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        try:
            resp = await client.get(
                target_url,
                params=query_params,
                headers=headers,
                follow_redirects=True
            )

            # 删除 Content-Length，让 FastAPI 自动计算
            headers_to_send = {
                key: value for key, value in resp.headers.items()
                if key.lower() not in ["content-length", "connection", "transfer-encoding"]
            }

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=headers_to_send,
                media_type=resp.headers.get(
                    "content-type", "application/javascript")
            )

        except Exception as e:
            logger.error(f"代理失败 {target_url}: {e}")
            return Response(
                content="console.error('Failed to load resource')",
                status_code=500,
                media_type="application/javascript"
            )


# ======================
#  获取百度全景图
# ======================

@router.get("")
async def get_panorama(
    location: str = Query(..., description="经纬度坐标，格式为'经度,纬度'"),
    width: int = Query(512, description="图片宽度，范围[10,1024]", ge=10, le=1024),
    height: int = Query(256, description="图片高度，范围[10,512]", ge=10, le=512),
    fov: int = Query(180, description="水平方向范围，范围[10,360]", ge=10, le=360),
    heading: int = Query(0, description="水平视角，范围[0,360]", ge=0, le=360),
    pitch: int = Query(0, description="垂直视角，范围[0,90]", ge=0, le=90),
    coordtype: str = Query("bd09ll", description="坐标类型，bd09ll或wgs84ll"),
    return_type: str = Query("image", description="返回类型，image或json"),
    baidu_ak: str = Depends(get_baidu_ak)
):
    """
    获取百度全景图中转接口
    参数说明：见文档
    """
    try:
        if coordtype not in ['bd09ll', 'wgs84ll']:
            raise HTTPException(
                status_code=400, detail="coordtype参数只能是bd09ll或wgs84ll")

        params = {
            'ak': baidu_ak,
            'location': location,
            'width': width,
            'height': height,
            'fov': fov,
            'heading': heading,
            'pitch': pitch,
            'coordtype': coordtype
        }

        logger.info(f"请求百度全景图API，参数: {params}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.get(PANORAMA_API_URL, params=params, headers=headers, follow_redirects=True)

        logger.info(f"百度全景图API响应状态: {resp.status_code}")

        if resp.status_code != 200:
            error_info = resp.text
            logger.error(f"百度API返回错误: {error_info}")
            raise HTTPException(
                status_code=500, detail=f"百度API请求失败: {error_info}")

        content_type = resp.headers.get('Content-Type', '')

        if 'application/json' in content_type:
            error_data = resp.json()
            logger.error(f"百度API返回JSON错误: {error_data}")
            raise HTTPException(
                status_code=500, detail=f"百度API返回错误: {error_data}")

        if 'text/html' in content_type:
            logger.error(f"收到HTML响应，可能是反爬或错误页：\n{resp.text[:500]}")
            raise HTTPException(status_code=500, detail="百度API返回HTML错误页")

        if 'image' in content_type:
            if return_type == 'json':
                return {
                    'url': f"{PANORAMA_API_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}",
                    'location': location,
                    'width': width,
                    'height': height,
                    'fov': fov,
                    'heading': heading,
                    'pitch': pitch,
                    'coordtype': coordtype
                }
            else:
                return Response(
                    content=resp.content,
                    media_type=content_type,
                    headers={
                        "Content-Disposition": f"inline; filename=panorama_{location.replace(',', '_')}.jpg"}
                )
        else:
            logger.error(f"未知的返回类型: {content_type}")
            raise HTTPException(
                status_code=500, detail=f"未知的返回类型: {content_type}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("处理请求时发生异常")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@router.get("/health")
async def panorama_health_check():
    """全景图服务健康检查"""
    return {"status": "healthy", "service": "baidu-panorama"}
