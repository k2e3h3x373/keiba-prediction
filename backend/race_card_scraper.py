import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup


def scrape_race_card(url: str) -> pd.DataFrame:
    """
    指定されたnetkeibaの出馬表URLから馬のリストをスクレイピングし、
    DataFrameとして返す関数
    """
    # サイトに負荷をかけないように待機
    time.sleep(1)

    try:
        response = requests.get(url)
        # 文字化けを防ぐ
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")

        # 出馬表のテーブルを取得
        table = soup.find("table", class_="RaceTable01")
        if table is None:
            print("エラー: 出馬表のテーブルが見つかりませんでした。")
            return pd.DataFrame()

        rows = table.find_all("tr", class_="HorseList")

        horse_list = []
        for row in rows:
            cols = row.find_all("td")

            # 必要なデータが揃っているかチェック
            if len(cols) < 14:
                continue

            horse_data = {
                "waku": cols[0].text.strip(),
                "umaban": cols[1].text.strip(),
                "sex_age": cols[4].text.strip(),
                "jockey_weight": cols[5].text.strip(),
                "horse_weight_info": cols[8].text.strip(),
            }
            horse_list.append(horse_data)

        return pd.DataFrame(horse_list)

    except requests.exceptions.RequestException as e:
        print(f"HTTPリクエストエラー: {e}")
        return pd.DataFrame()


def preprocess_for_prediction(df: pd.DataFrame) -> pd.DataFrame:
    """
    スクレイピングした出馬表データをAIの予測に使える形式に前処理する関数
    """
    if df.empty:
        return df

    df_processed = df.copy()

    # 1. データ型の変換と不要な行の削除
    df_processed["waku"] = pd.to_numeric(df_processed["waku"], errors="coerce")
    df_processed["umaban"] = pd.to_numeric(df_processed["umaban"], errors="coerce")
    df_processed["jockey_weight"] = pd.to_numeric(
        df_processed["jockey_weight"], errors="coerce"
    )

    # 2. 'horse_weight_info' から馬体重を抽出
    # "480(+2)" や "計不" (計測不能) といった形式に対応
    def extract_weight(text):
        match = re.search(r"^\d{3}", text)
        return int(match.group(0)) if match else None

    df_processed["horse_weight"] = df_processed["horse_weight_info"].apply(
        extract_weight
    )

    # 3. 'sex_age' を 'sex' と 'age' に分割
    df_processed["sex"] = df_processed["sex_age"].str[0]
    df_processed["age"] = pd.to_numeric(
        df_processed["sex_age"].str[1:], errors="coerce"
    )

    # 'sex' を数値にエンコード (牡=0, 牝=1, セ=2)
    sex_map = {"牡": 0, "牝": 1, "セ": 2}
    df_processed["sex"] = df_processed["sex"].map(sex_map)

    # 4. 必要なカラムだけに絞り込み、順番をモデルに合わせる
    model_features = ["waku", "umaban", "jockey_weight", "horse_weight", "sex", "age"]
    df_processed = df_processed[model_features]

    # 5. 処理中に欠損値が発生した行を削除
    df_processed = df_processed.dropna()

    # 6. データ型を最終調整
    df_processed = df_processed.astype(
        {
            "waku": int,
            "umaban": int,
            "jockey_weight": float,
            "horse_weight": int,
            "sex": int,
            "age": int,
        }
    )

    return df_processed


def main():
    """
    テスト用のメイン関数
    """
    # テスト用のURL (例: 2024年の安田記念)
    # netkeibaのURL構造が変わった場合、このURLは無効になる可能性があります
    test_url = "https://race.netkeiba.com/race/shutuba.html?race_id=202405020811"

    print(f"テストURLから出馬表データを取得します: {test_url}")

    # スクレイピング実行
    raw_df = scrape_race_card(test_url)

    if not raw_df.empty:
        print("\n--- スクレイピング結果 (生データ) ---")
        print(raw_df)

        # 前処理実行
        processed_df = preprocess_for_prediction(raw_df)

        print("\n--- AI予測用の前処理済みデータ ---")
        print(processed_df)
        print("\nカラムのデータ型:")
        print(processed_df.dtypes)
    else:
        print("データを取得できませんでした。")


if __name__ == "__main__":
    main()
