import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO


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

    except requests.exceptions.RequestException as e:
        print(f"URLの取得中にエラーが発生しました: {e}")
    except IndexError as e:
        print(
            f"テーブルが見つかりませんでした。HTMLの構造が変更された可能性があります。"
        )


# このファイルが直接実行された場合に、main()関数を呼び出す
if __name__ == "__main__":
    main()
