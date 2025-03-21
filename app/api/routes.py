"""
APIルートの定義
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.openai_service import openai_service
from app.services.jancode_service import jancode_service
from app.utils.jancode_utils import validate_jancode
from app.core.config import settings

router = APIRouter()

class JANCodeRequest(BaseModel):
    """JANコード推定リクエストモデル"""
    product_name: str
    product_image_url: str

class ProductInfo(BaseModel):
    """商品情報モデル"""
    codeNumber: str
    codeType: Optional[str] = None
    itemName: Optional[str] = None
    itemModel: Optional[str] = None
    itemUrl: Optional[str] = None
    itemImageUrl: Optional[str] = None
    brandName: Optional[str] = None
    makerName: Optional[str] = None
    makerNameKana: Optional[str] = None
    ProductDetails: Optional[Any] = None  # リストまたは辞書型を受け入れる
    searchKeyword: Optional[str] = None  # この商品情報を取得するために使用した検索キーワード

class JANCodeResponse(BaseModel):
    """JANコード推定レスポンスモデル"""
    jancode: Optional[str] = None
    candidates: List[ProductInfo] = []
    confidence: float = 0.0
    product_name: Optional[str] = None
    message: str = ""
    usedKeywords: List[str] = []  # 検索に使用したキーワードのリスト
    keywordHits: Dict[str, int] = {}  # 各キーワードに対するヒット数

@router.post("/estimate-jancode", response_model=JANCodeResponse)
async def estimate_jancode(request: JANCodeRequest):
    """
    商品名と商品画像URLからJANコードを推定する
    
    Args:
        request: JANコード推定リクエスト
            - product_name: 商品名
            - product_image_url: 商品画像のURL
        
    Returns:
        JANCodeResponse: 推定されたJANコード情報
    """
    try:
        product_name = request.product_name
        product_image_url = request.product_image_url
        
        if not product_image_url:
            raise HTTPException(status_code=400, detail="画像URLが空です")
        
        # ステップ1: 商品画像と商品名から検索キーワード候補を生成
        search_keywords = await openai_service.generate_search_keywords(
            image_url=product_image_url,
            product_name=product_name
        )
        
        # 検索キーワードが生成できなかった場合
        if not search_keywords:
            return JANCodeResponse(
                candidates=[],
                confidence=0.0,
                product_name=product_name,
                message="検索キーワードを生成できませんでした。より詳細な商品情報や鮮明な画像を提供してください。"
            )
        
        # ステップ2: 各キーワードでJANCODE LOOKUP APIを呼び出し
        all_products = []
        keyword_hits = {}  # 各キーワードに対するヒット数
        keyword_product_map = {}  # 各商品がどのキーワードで見つかったかを記録
        
        for keyword in search_keywords:
            try:
                search_result = await jancode_service.search_by_keyword(
                    keyword=keyword,
                    hits=3,  # 各キーワードで最大3件取得
                    page=1
                )
                
                # ヒット数を記録
                hit_count = search_result.get("info", {}).get("count", 0)
                keyword_hits[keyword] = hit_count
                
                # 検索結果から商品情報を取得
                products = search_result.get("product", [])
                if products:
                    # 各商品に検索キーワードを記録
                    for product in products:
                        code_number = product.get("codeNumber")
                        if code_number:
                            if code_number not in keyword_product_map:
                                keyword_product_map[code_number] = []
                            keyword_product_map[code_number].append(keyword)
                    
                    all_products.extend(products)
            except Exception as e:
                # 検索エラーは無視して次のキーワードに進む
                keyword_hits[keyword] = 0
                continue
        
        # 重複するJANコードを削除
        unique_products = {}
        for product in all_products:
            code_number = product.get("codeNumber")
            if code_number and code_number not in unique_products:
                # 商品情報に検索キーワードを追加
                if code_number in keyword_product_map:
                    product["searchKeyword"] = ", ".join(keyword_product_map[code_number])
                unique_products[code_number] = product
        
        # 候補がない場合
        if not unique_products:
            # 画像分析によるJANコード候補の推定（フォールバック）
            image_candidates = await openai_service.analyze_product_image(
                image_url=product_image_url,
                product_name=product_name
            )
            
            if not image_candidates:
                return JANCodeResponse(
                    candidates=[],
                    confidence=0.0,
                    product_name=product_name,
                    message="JANコードを推定できませんでした。より詳細な商品情報や鮮明な画像を提供してください。"
                )
            
            # JANコードのみを持つ簡易的な商品情報オブジェクトを作成
            candidate_products = []
            for jancode in image_candidates[:max(3, settings.MAX_CANDIDATES)]:  # 最低3つ、最大はMAX_CANDIDATES
                candidate_products.append(
                    ProductInfo(
                        codeNumber=jancode,
                        itemName=f"{product_name} (推定)",
                        codeType="JAN (推定)"
                    )
                )
            
            return JANCodeResponse(
                candidates=candidate_products,
                confidence=0.3,  # 低い確信度
                product_name=product_name,
                message="JANコード候補を推定しましたが、確度は低いです。JANCODE LOOKUP APIで商品情報が見つかりませんでした。",
                usedKeywords=search_keywords,
                keywordHits=keyword_hits
            )
        
        # ステップ3: 得られたJANコード候補を再度OpenAI APIで絞り込み
        product_list = list(unique_products.values())
        filtered_jancodes = await openai_service.filter_jancode_candidates(
            jancode_candidates=product_list,
            product_name=product_name,
            image_url=product_image_url
        )
        
        # 候補がない場合
        if not filtered_jancodes:
            # 元の候補をそのまま使用
            filtered_jancodes = list(unique_products.keys())
        
        # 候補の商品情報を取得
        candidate_products = []
        
        # 絞り込まれた候補の商品情報を追加
        for jancode in filtered_jancodes:
            if jancode in unique_products:
                candidate_products.append(unique_products[jancode])
            else:
                # JANコードが見つからない場合は、簡易的な商品情報を作成
                candidate_products.append({
                    "codeNumber": jancode,
                    "codeType": "JAN (推定)",
                    "itemName": f"{product_name} (推定)"
                })
        
        # 候補が3つ未満の場合、元の候補から追加
        if len(candidate_products) < 3 and len(product_list) > len(candidate_products):
            # 既に候補に含まれていないJANコードを抽出
            existing_jancodes = {product.get("codeNumber") for product in candidate_products}
            additional_products = [
                product for product in product_list
                if product.get("codeNumber") not in existing_jancodes
            ]
            
            # 必要な数だけ追加（最低3つになるまで）
            needed = 3 - len(candidate_products)
            candidate_products.extend(additional_products[:needed])
        
        # 最も可能性の高い候補
        primary_candidate = filtered_jancodes[0] if filtered_jancodes else None
        
        # 商品情報を取得
        product_info = unique_products.get(primary_candidate, {}) if primary_candidate else {}
        
        # ProductInfoモデルに変換
        candidate_product_models = []
        for product in candidate_products:
            candidate_product_models.append(
                ProductInfo(
                    codeNumber=product.get("codeNumber", ""),
                    codeType=product.get("codeType"),
                    itemName=product.get("itemName"),
                    itemModel=product.get("itemModel"),
                    itemUrl=product.get("itemUrl"),
                    itemImageUrl=product.get("itemImageUrl"),
                    brandName=product.get("brandName"),
                    makerName=product.get("makerName"),
                    makerNameKana=product.get("makerNameKana"),
                    ProductDetails=product.get("ProductDetails", []),
                    searchKeyword=product.get("searchKeyword")
                )
            )
        
        # レスポンスを作成
        if primary_candidate and product_info:
            confidence = 0.9  # 高い確信度
            return JANCodeResponse(
                jancode=primary_candidate,
                candidates=candidate_product_models,
                confidence=confidence,
                product_name=product_info.get("itemName", product_name),
                message="JANコードが正常に推定されました。",
                usedKeywords=search_keywords,
                keywordHits=keyword_hits
            )
        
        # 商品情報が見つからなかった場合
        return JANCodeResponse(
            candidates=candidate_product_models,
            confidence=0.7,  # 中程度の確信度
            product_name=product_name,
            message="複数のJANコード候補が見つかりました。最も可能性の高い候補から順に表示しています。",
            usedKeywords=search_keywords,
            keywordHits=keyword_hits
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エラーが発生しました: {str(e)}")