import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup

# JockeyモデルをインポートしてDBにアクセスできるようにする
from models import Jockey


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

            # 騎手IDをaタグのhrefから抽出
            jockey_link = cols[6].find("a")
            jockey_id_match = (
                re.search(r"/jockey/result/recent/(\d+)/", jockey_link["href"])
                if jockey_link
                else None
            )
            jockey_id = jockey_id_match.group(1) if jockey_id_match else None

            horse_data = {
                "waku": cols[0].text.strip(),
                "umaban": cols[1].text.strip(),
                "sex_age": cols[4].text.strip(),
                "jockey_weight": cols[5].text.strip(),
                "jockey_id": jockey_id,  # 騎手IDを追加
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
    # 関数が呼び出されたタイミングでappをインポートする（循環インポート対策）
    from app import app

    if df.empty:
        return df

    df_processed = df.copy()

    # --- 1. Jockeyの成績データを取得してマージ ---
    with app.app_context():
        # スクレイピング結果からユニークなjockey_idを取得
        jockey_ids = [int(jid) for jid in df_processed["jockey_id"].unique() if jid]
        if jockey_ids:
            # データベースから該当騎手の成績を取得
            jockeys = Jockey.query.filter(Jockey.id.in_(jockey_ids)).all()
            jockey_stats = {
                j.id: {
                    "win_rate": j.win_rate,
                    "place_rate": j.place_rate,
                    "show_rate": j.show_rate,
                }
                for j in jockeys
            }
            jockey_stats_df = pd.DataFrame.from_dict(jockey_stats, orient="index")
            jockey_stats_df.index.name = "jockey_id"

            # jockey_idを数値型に変換してからマージ
            df_processed["jockey_id"] = pd.to_numeric(
                df_processed["jockey_id"], errors="coerce"
            )
            df_processed = pd.merge(
                df_processed, jockey_stats_df, on="jockey_id", how="left"
            )

    # 成績データがない騎手(新人など)は0で埋める
    df_processed["win_rate"] = df_processed["win_rate"].fillna(0)
    df_processed["place_rate"] = df_processed["place_rate"].fillna(0)
    df_processed["show_rate"] = df_processed["show_rate"].fillna(0)

    # 2. データ型の変換と不要な行の削除
    df_processed["waku"] = pd.to_numeric(df_processed["waku"], errors="coerce")
    df_processed["umaban"] = pd.to_numeric(df_processed["umaban"], errors="coerce")
    df_processed["jockey_weight"] = pd.to_numeric(
        df_processed["jockey_weight"], errors="coerce"
    )

    # 3. 'horse_weight_info' から馬体重を抽出
    # "480(+2)" や "計不" (計測不能) といった形式に対応
    def extract_weight(text):
        match = re.search(r"^\d{3}", text)
        return int(match.group(0)) if match else None

    df_processed["horse_weight"] = df_processed["horse_weight_info"].apply(
        extract_weight
    )

    # 4. 'sex_age' を 'sex' と 'age' に分割
    df_processed["sex"] = df_processed["sex_age"].str[0]
    df_processed["age"] = pd.to_numeric(
        df_processed["sex_age"].str[1:], errors="coerce"
    )

    # 'sex' を数値にエンコード (牡=0, 牝=1, セ=2)
    sex_map = {"牡": 0, "牝": 1, "セ": 2}
    df_processed["sex"] = df_processed["sex"].map(sex_map)

    # 5. 必要なカラムだけに絞り込み、順番をモデルに合わせる
    model_features = [
        "waku",
        "umaban",
        "jockey_weight",
        "horse_weight",
        "sex",
        "age",
        "win_rate",
        "place_rate",
        "show_rate",
    ]
    df_processed = df_processed[model_features]

    # 6. 処理中に欠損値が発生した行を削除
    df_processed = df_processed.dropna()

    # 7. データ型を最終調整
    df_processed = df_processed.astype(
        {
            "waku": int,
            "umaban": int,
            "jockey_weight": float,
            "horse_weight": int,
            "sex": int,
            "age": int,
            "win_rate": float,
            "place_rate": float,
            "show_rate": float,
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
