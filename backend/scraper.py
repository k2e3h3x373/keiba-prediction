import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO


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
    # サンプルとして、特定のレース結果ページのURLを指定 (2023年ジャパンカップ)
    target_url = "https://db.netkeiba.com/race/202305050812/"

    try:
        # 1. requestsでURLにアクセスし、HTMLを取得
        response = requests.get(target_url)
        response.encoding = response.apparent_encoding  # 文字化け防止

        # 2. BeautifulSoupでHTMLを解析
        soup = BeautifulSoup(response.text, "html.parser")

        # 3. ページのタイトルを取得して表示 (動作確認)
        page_title = soup.title.string
        print("ページのタイトルを取得しました:")
        print(page_title)
        print("-" * 30)  # 区切り線

        # 4. レース結果のテーブルを抽出
        # classが'RaceTable01'であるtable要素を検索
        race_table = soup.find("table", class_="race_table_01")

        # 5. pandasのread_htmlを使って、テーブルをDataFrameに変換
        # read_htmlはリストを返すので、最初の要素を取得
        df = pd.read_html(StringIO(str(race_table)))[0]

        print("レース結果テーブルを取得しました:")
        print(df)
        print("-" * 30)

        # 6. データを整形する
        cleaned_df = clean_data(df)
        print("整形後のデータ:")
        print(cleaned_df)
        print("-" * 30)
        print("各列のデータ型:")
        print(cleaned_df.info())

    except requests.exceptions.RequestException as e:
        print(f"URLの取得中にエラーが発生しました: {e}")
    except IndexError as e:
        print(
            f"テーブルが見つかりませんでした。HTMLの構造が変更された可能性があります。"
        )


# このファイルが直接実行された場合に、main()関数を呼び出す
if __name__ == "__main__":
    main()
