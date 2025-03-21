"""
OpenAI APIとの連携を行うサービス
"""
import base64
import json
import httpx
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
from app.core.config import settings

class OpenAIService:
    """OpenAI APIを利用して画像分析や商品情報の推定を行うサービス"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def analyze_product_image(self, image_url: str, product_name: str) -> List[str]:
        """
        商品画像を分析し、JANコードの候補を推定する
        
        Args:
            image_url: 商品画像のURL
            product_name: 商品名
            
        Returns:
            List[str]: 推定されたJANコードの候補リスト
        """
        try:
            # 画像URLから画像をダウンロード
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
            
            # 画像をBase64エンコード
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # GPT-4 Visionを使用して画像分析
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # gpt-4o-miniモデルを使用
                messages=[
                    {
                        "role": "system",
                        "content": """
                        あなたは商品画像からJANコード（GTIN-13）を識別する専門家です。
                        JANコードは通常、商品のパッケージに印刷されたバーコードの下に13桁の数字で表示されています。
                        日本のJANコードは通常、45または49から始まります。
                        画像からJANコードが見つかった場合は、そのコードのみを返してください。
                        複数の候補がある場合は、最も可能性の高いものから順に最大5つまで返してください。
                        JANコードが見つからない場合は、商品名から推測される可能性のあるJANコードの特徴（メーカーコードなど）を返してください。
                        """
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"この商品画像から商品「{product_name}」のJANコード（GTIN-13）を識別してください。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
        except httpx.HTTPError as e:
            # 画像のダウンロードに失敗した場合
            return [f"画像のダウンロードに失敗しました: {str(e)}"]
        
        # レスポンスからJANコード候補を抽出
        content = response.choices[0].message.content
        return self._extract_jancodes(content)
    
    async def estimate_jancode_from_name(self, product_name: str) -> List[str]:
        """
        商品名からJANコードの候補を推定する
        
        Args:
            product_name: 商品名
            
        Returns:
            List[str]: 推定されたJANコードの候補リスト
        """
        response = await self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """
                    あなたは商品名からJANコード（GTIN-13）を推定する専門家です。
                    日本の商品のJANコードは通常、45または49から始まります。
                    商品名から推測される可能性のあるJANコードの候補を最大5つまで返してください。
                    各候補について、なぜその候補が可能性があるのか簡潔な理由も添えてください。
                    """
                },
                {
                    "role": "user",
                    "content": f"商品名「{product_name}」から考えられるJANコード（GTIN-13）の候補を推定してください。"
                }
            ],
            max_tokens=300
        )
        
        # レスポンスからJANコード候補を抽出
        content = response.choices[0].message.content
        return self._extract_jancodes(content)
    
    async def generate_search_keywords(self, image_url: str, product_name: str) -> List[str]:
        """
        商品画像と商品名から検索キーワード候補を生成する
        
        Args:
            image_url: 商品画像のURL
            product_name: 商品名
            
        Returns:
            List[str]: 検索キーワード候補のリスト（最大5つ）
        """
        try:
            # 画像URLから画像をダウンロード
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
            
            # 画像をBase64エンコード
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # GPT-4 Visionを使用して画像分析
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        あなたは商品画像と商品名から、JANコード検索に最適なキーワードを生成する専門家です。
                        商品の特徴（ブランド名、メーカー名、商品名、型番など）を抽出し、検索キーワードとして最適な形に整形してください。
                        複数の検索キーワード候補を生成し、最も検索に有効と思われるものから順に最大5つまで返してください。
                        返答は以下のJSON形式で返してください：
                        {
                          "keywords": ["キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"]
                        }
                        """
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"この商品画像と商品名「{product_name}」から、JANコード検索に最適なキーワードを生成してください。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # レスポンスからキーワード候補を抽出
            content = response.choices[0].message.content
            data = json.loads(content)
            keywords = data.get("keywords", [])
            
            # 空のキーワードを除外
            keywords = [k for k in keywords if k.strip()]
            
            # 商品名も検索キーワードに追加（まだリストにない場合）
            if product_name and product_name not in keywords:
                keywords.append(product_name)
                
            return keywords[:5]  # 最大5つまでに制限
            
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            # エラーが発生した場合は商品名のみを返す
            return [product_name] if product_name else []
    
    async def filter_jancode_candidates(self,
                                       jancode_candidates: List[Dict[str, Any]],
                                       product_name: str,
                                       image_url: str) -> List[str]:
        """
        JANコード候補リストから最適な候補を選択する
        
        Args:
            jancode_candidates: JANコード候補のリスト（JANCODE LOOKUP APIのレスポンス）
            product_name: 商品名
            image_url: 商品画像のURL
            
        Returns:
            List[str]: 絞り込まれたJANコード候補のリスト（最大5つ）
            注意: 実際の実装ではJANコード（文字列）のリストを返しますが、
                 APIルートでこれらのJANコードを使って商品情報を取得します
        """
        try:
            # 画像URLから画像をダウンロード
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
            
            # 画像をBase64エンコード
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # 候補がない場合は空のリストを返す
            if not jancode_candidates:
                return []
            
            # JANコード候補をJSON文字列に変換
            candidates_json = json.dumps(jancode_candidates, ensure_ascii=False, indent=2)
            
            # GPT-4 Visionを使用して候補を絞り込む
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        あなたは商品画像と商品名から、最適なJANコード候補を選択する専門家です。
                        提供されたJANコード候補リストから、商品画像と商品名に最も一致する候補を選択してください。
                        商品名、ブランド名、メーカー名、商品画像の特徴などを総合的に判断し、最も可能性の高いJANコードを選んでください。
                        返答は以下のJSON形式で返してください：
                        {
                          "jancodes": ["4901234567890", "4902345678901", "4903456789012"]
                        }
                        """
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"この商品画像と商品名「{product_name}」に最も一致するJANコードを、以下の候補から選んでください：\n\n{candidates_json}"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # レスポンスからJANコード候補を抽出
            content = response.choices[0].message.content
            data = json.loads(content)
            jancodes = data.get("jancodes", [])
            
            # 重複を削除し、最大5つまでに制限
            unique_jancodes = list(dict.fromkeys(jancodes))
            return unique_jancodes[:settings.MAX_CANDIDATES]
            
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            # エラーが発生した場合は元の候補をそのまま返す
            return [candidate.get("codeNumber") for candidate in jancode_candidates
                   if candidate.get("codeNumber")][:settings.MAX_CANDIDATES]
    
    def _extract_jancodes(self, text: str) -> List[str]:
        """
        テキストからJANコード（13桁の数字）を抽出する
        
        Args:
            text: JAN候補を含むテキスト
            
        Returns:
            List[str]: 抽出されたJANコードのリスト
        """
        import re
        
        # 13桁の数字を抽出
        jancode_pattern = r'\b\d{13}\b'
        jancodes = re.findall(jancode_pattern, text)
        
        # 重複を削除し、最大5つまでに制限
        unique_jancodes = list(dict.fromkeys(jancodes))
        return unique_jancodes[:settings.MAX_CANDIDATES]

# サービスのインスタンスを作成
openai_service = OpenAIService()