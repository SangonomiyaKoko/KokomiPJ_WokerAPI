import asyncio

import httpx

from .api_base import BaseUrl
from app.log import ExceptionLogger
from app.response import JSONResponse


class BasicAPI:
    '''基础接口
    
    基础数据接口，包括以下功能：
    
    1. 获取用户基本数据
    2. 获取用户和工会的基本数据
    3. 获取搜索用户的结果
    4. 获取搜索工会的结果
    '''
    @ExceptionLogger.handle_network_exception_async
    async def fetch_data(url, method: str = 'get', data: dict | list = None):
        try:
            async with httpx.AsyncClient() as client:
                if method == 'get':
                    res = await client.get(url=url, timeout=BaseUrl.REQUEST_TIME_OUT)
                elif method == 'post': 
                    res = await client.post(url=url, json=data, timeout=BaseUrl.REQUEST_TIME_OUT)
                else:
                    raise ValueError('Invalid Method')
                requset_code = res.status_code
                requset_result = res.json()
                if '/clans.' in url:
                    if '/api/search/autocomplete/' in url and requset_code == 200:
                        # 查询工会接口的返回值处理
                        data = requset_result['search_autocomplete_result']
                        return JSONResponse.get_success_response(data)
                    if '/api/clanbase/' in url and requset_code == 200:
                        # 用户基础信息接口的返回值
                        data = requset_result['clanview']
                        return JSONResponse.get_success_response(data)
                    if '/api/clanbase/' in url and requset_code == 503:
                        return JSONResponse.API_1002_ClanNotExist
                elif (
                    '/clans/' in url
                    and requset_code == 404
                ):
                    # 用户所在工会接口，如果用户没有在工会会返回404
                    data = {
                        "clan_id": None,
                        "role": None, 
                        "joined_at": None, 
                        "clan": {},
                    }
                    return JSONResponse.get_success_response(data)
                elif (
                    '/accounts/search/' in url
                    and requset_code in [400, 500, 503]
                ):
                    # 用户搜索接口可能的返回值
                    data = []
                    return JSONResponse.get_success_response([])
                elif requset_code == 404:
                    # 用户不存在或者账号删除的情况
                    return JSONResponse.API_1001_UserNotExist
                elif method == 'post' and requset_code == 200:
                    return JSONResponse.get_success_response(requset_result)
                elif requset_code == 200:
                    # 正常返回值的处理
                    data = requset_result['data']
                    return JSONResponse.get_success_response(data)
                else:
                    res.raise_for_status()  # 其他状态码
        except Exception as e:
            raise e

    @classmethod
    async def get_user_basic(
        cls,
        account_id: int,
        region_id: int,
        ac_value: str = None
    ) -> list:
        '''获取用户基础信息

        参数：
            account_id： 用户id
            region_id； 用户服务器id
            ac_value: 是否使用ac查询数据

        返回：
            用户基础数据
        '''
        api_url = BaseUrl.get_vortex_base_url(region_id)
        urls = [
            f'{api_url}/api/accounts/{account_id}/' + (f'?ac={ac_value}' if ac_value else '')
        ]
        tasks = []
        responses = []
        async with asyncio.Semaphore(len(urls)):
            for url in urls:
                tasks.append(cls.fetch_data(url))
            responses = await asyncio.gather(*tasks)
            return responses
        
    @classmethod
    async def get_user_basic_and_clan(
        cls,
        account_id: int,
        region_id: int,
        ac_value: str = None
    ) -> list:
        '''获取用户基础信息和工会信息

        参数：
            account_id： 用户id
            region_id； 用户服务器id
            ac_value: 是否使用ac查询数据

        返回：
            用户基础数据
            用户工会信息
        '''
        api_url = BaseUrl.get_vortex_base_url(region_id)
        urls = [
            f'{api_url}/api/accounts/{account_id}/' + (f'?ac={ac_value}' if ac_value else ''),
            f'{api_url}/api/accounts/{account_id}/clans/'
        ]
        tasks = []
        responses = []
        async with asyncio.Semaphore(len(urls)):
            for url in urls:
                tasks.append(cls.fetch_data(url))
            responses = await asyncio.gather(*tasks)
            return responses
        

    @classmethod
    async def get_clan_basic(
        cls,
        clan_id: int,
        region_id: int,
    ):
        '''获取工会基础信息

        参数：
            clan_id： 工会id
            region_id； 工会服务器id

        返回：
            工会基础数据
        '''
        api_url = BaseUrl.get_clan_basse_url(region_id)
        urls = [
            f'{api_url}/api/clanbase/{clan_id}/claninfo/'
        ]
        tasks = []
        responses = []
        async with asyncio.Semaphore(len(urls)):
            for url in urls:
                tasks.append(cls.fetch_data(url))
            responses = await asyncio.gather(*tasks)
            return responses

    @classmethod
    async def get_user_search(
        cls,
        region_id: int,
        nickname: str,
        limit: int = 10
    ):
        '''获取用户名称搜索结构

        通过输入的用户名称搜索用户账号

        参数：
            region_id: 用户服务器id
            nickname: 用户名称
            limit: 搜索最多返回值，default=10，max=10
            check: 是否对结果进行匹配，返回唯一一个完全匹配的结果
        
        返回：
            结果列表
        '''
        if limit < 1:
            limit = 1
        if limit > 10:
            limit = 10
        nickname = nickname.lower()
        api_url = BaseUrl.get_vortex_base_url(region_id)
        url = f'{api_url}/api/accounts/search/{nickname.lower()}/?limit={limit}'
        result = await cls.fetch_data(url)
        return result
    
    @classmethod
    async def get_clan_search(
        cls,
        region_id: int,
        tag: str,
        limit: int = 10
    ):
        '''获取工会名称搜索结果

        通过输入的工会名称搜索工会账号

        参数：
            region_id: 工会服务器id
            tga: 工会名称
            limit: 搜索最多返回值，default=10，max=10
            check: 是否对结果进行匹配，返回唯一一个完全匹配的结果
        
        返回：
            结果列表
        '''
        if limit < 1:
            limit = 1
        if limit > 10:
            limit = 10
        tag = tag.lower()
        api_url = BaseUrl.get_clan_basse_url(region_id)
        url = f'{api_url}/api/search/autocomplete/?search={tag}&type=clans'
        result = await cls.fetch_data(url)
        return result
