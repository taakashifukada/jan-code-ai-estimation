"""
JANCODE LOOKUP APIとの連携を行うサービス
"""
import httpx
from urllib.parse import urlencode
from app.core.config import settings

class JANCodeLookupService:
    """JANCODE LOOKUP APIを利用して商品情報を検索するサービス"""
    
    def __init__(self):
        self.base_url = settings.JANCODE_API_URL
        self.app_id = settings.JANCODE_API_APP_ID
        
    async def search_by_keyword(self, keyword: str, hits: int = 5, page: int = 1) -> dict:
        """
        キーワードによる商品検索を行う
        
        Args:
            keyword: 検索キーワード
            hits: 取得件数（デフォルト: 5）
            page: 取得ページ（デフォルト: 1）
            
        Returns:
            dict: 検索結果
        """
        params = {
            'appId': self.app_id,
            'query': keyword,
            'hits': hits,
            'page': page,
            'type': 'keyword'
        }
        
        url = f"{self.base_url}?{urlencode(params)}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    
    async def search_by_code(self, code: str) -> dict:
        """
        JANコードによる商品検索を行う
        
        Args:
            code: JANコード（少なくとも7桁以上）
            
        Returns:
            dict: 検索結果
        """
        if len(code) < 7:
            raise ValueError("コード番号は少なくとも7桁以上である必要があります")
        
        params = {
            'appId': self.app_id,
            'query': code,
            'type': 'code'
        }
        
        url = f"{self.base_url}?{urlencode(params)}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    
    async def get_product_info(self, jancode: str) -> dict:
        """
        JANコードから商品情報を取得する
        
        Args:
            jancode: 13桁のJANコード
            
        Returns:
            dict: 商品情報（見つからない場合は空の辞書）
        """
        result = await self.search_by_code(jancode)
        
        # 商品が見つかった場合
        if result.get('info', {}).get('count', 0) > 0:
            products = result.get('products', [])
            if products:
                return products[0]
        
        return {}

# サービスのインスタンスを作成
jancode_service = JANCodeLookupService()