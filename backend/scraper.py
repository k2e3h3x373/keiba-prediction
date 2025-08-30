import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
from tqdm import tqdm


def scrape_race_result(race_id: str) -> pd.DataFrame:
    """
    指定されたレースIDの結果ページをスクレイピングし、整形されたDataFrameを返す関数
    """
    url = f"https://db.netkeiba.com/race/{race_id}/"
    try:
        response = requests.get(url)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        race_table = soup.find("table", class_="race_table_01")
        df = pd.read_html(StringIO(str(race_table)))[0]

        cleaned_df = clean_data(df)
        return cleaned_df

    except IndexError:
        print(
            f"エラー: レースID {race_id} のテーブルが見つかりませんでした。スキップします。"
        )
        return pd.DataFrame()  # 空のDataFrameを返す
    except Exception as e:
        print(f"エラー: レースID {race_id} の処理中に予期せぬエラーが発生しました: {e}")
        return pd.DataFrame()  # 空のDataFrameを返す


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    スクレイピングで取得したDataFrameを整形する関数
    """
    # 必要のない列を削除
    df = df.drop(["着差", "調教師", "タイム"], axis=1)

    # 列名をリネーム
    df = df.rename(
        columns={
            "着 順": "rank",
            "枠 番": "waku",
            "馬 番": "umaban",
            "馬名": "horse_name",
            "性齢": "sex_age",
            "斤量": "jockey_weight",
            "騎手": "jockey_name",
            "単勝": "single_price",
            "人 気": "popular",
            "馬体重": "horse_weight",
        }
    )

    # 'rank' 列が数値でない行を削除 (例: '除外', '中止' など)
    df = df[pd.to_numeric(df["rank"], errors="coerce").notna()]

    # データ型を変換
    df["rank"] = df["rank"].astype(int)
    df["waku"] = df["waku"].astype(int)
    df["umaban"] = df["umaban"].astype(int)
    df["jockey_weight"] = df["jockey_weight"].astype(float)
    df["single_price"] = df["single_price"].astype(float)
    df["popular"] = df["popular"].astype(int)

    # 'horse_weight' から体重のみを抽出し、数値に変換
    # 例: '498(+4)' -> 498
    df["horse_weight"] = df["horse_weight"].str.split("(", expand=True)[0].astype(int)

    return df


def main():
    """
    Webスクレイピング処理のメイン関数
    """
    # 2023年のG1レースのサンプルIDリスト
    race_ids = [
        "202305050812",  # ジャパンカップ
        "202306050811",  # 有馬記念
        "202309030811",  # 宝塚記念
    ]

    all_results = []

    print("レース結果のスクレイピングを開始します...")
    # tqdmを使ってプログレスバーを表示
    for race_id in tqdm(race_ids):
        result_df = scrape_race_result(race_id)
        # 取得したデータにレースIDを列として追加
        if not result_df.empty:
            result_df["race_id"] = race_id
            all_results.append(result_df)

        # サーバーに負荷をかけないための待機
        time.sleep(1)

    # 全てのレース結果を一つのDataFrameに結合
    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        print("スクレイピングが完了しました。")
        print("取得したデータの一部:")
        print(final_df.head())
        print("\n全体の件数:", len(final_df))
    else:
        print("有効なデータは一件も取得できませんでした。")


# このファイルが直接実行された場合に、main()関数を呼び出す
if __name__ == "__main__":
    main()
