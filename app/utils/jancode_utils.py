"""
JANコード（GTIN）に関するユーティリティ関数
"""

def validate_jancode(jancode: str) -> bool:
    """
    JANコード（GTIN-13）の検証を行う
    
    Args:
        jancode: 検証するJANコード文字列
        
    Returns:
        bool: 有効なJANコードの場合はTrue、そうでない場合はFalse
    """
    if not jancode or not jancode.isdigit() or len(jancode) != 13:
        return False
    
    # チェックディジットの計算
    total = 0
    for i in range(12):
        digit = int(jancode[i])
        if i % 2 == 0:  # 偶数位置（0から始まる）
            total += digit
        else:  # 奇数位置
            total += digit * 3
    
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(jancode[12])

def format_jancode(jancode: str) -> str:
    """
    JANコードを正規化する（スペースや記号を削除し、数字のみにする）
    
    Args:
        jancode: 正規化するJANコード文字列
        
    Returns:
        str: 正規化されたJANコード
    """
    # 数字以外の文字を削除
    return ''.join(c for c in jancode if c.isdigit())

def get_country_code(jancode: str) -> str:
    """
    JANコードから国コードを取得する
    
    Args:
        jancode: JANコード文字列
        
    Returns:
        str: 国コード（例: '49' = 日本）
    """
    if not jancode or len(jancode) < 3:
        return ""
    
    # 最初の2-3桁が国コード
    prefix = jancode[:3]
    
    # 日本のJANコードは45-49で始まる
    if prefix.startswith('45') or prefix.startswith('49'):
        return "日本"
    # その他の国コードは省略
    
    return "不明"