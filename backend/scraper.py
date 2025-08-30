import requests
from bs4 import BeautifulSoup


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

    except requests.exceptions.RequestException as e:
        print(f"URLの取得中にエラーが発生しました: {e}")


# このファイルが直接実行された場合に、main()関数を呼び出す
if __name__ == "__main__":
    main()
