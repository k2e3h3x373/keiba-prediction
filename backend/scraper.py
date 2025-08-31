import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
from tqdm import tqdm
from datetime import datetime
import re

# 競馬場IDと競馬場名の対応表
PLACE_MAP = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "京都",
    "09": "阪神",
    "10": "小倉",
}


def get_all_race_ids_in_year(year: int) -> list[str]:
    """
    指定された年のすべてのレースIDを生成ロジックに基づいて取得する関数
    """
    all_race_ids = []
    print(f"{year}年の全レースIDを探索します...")

    # 競馬場ID (01: 札幌, 02: 函館, ..., 10: 東京)
    for place_id in tqdm(range(1, 11), desc="競馬場"):
        # 開催回 (通常1〜5回)
        for kaisai_kai in range(1, 7):
            # 開催日 (通常1〜12日)
            for kaisai_nichi in range(1, 13):
                # レース番号 (1〜12レース)
                for race_num in range(1, 13):
                    race_id = (
                        f"{year}"
                        f"{str(place_id).zfill(2)}"
                        f"{str(kaisai_kai).zfill(2)}"
                        f"{str(kaisai_nichi).zfill(2)}"
                        f"{str(race_num).zfill(2)}"
                    )
                    all_race_ids.append(race_id)

    print(f"合計 {len(all_race_ids)} 件のレースIDを生成しました。")
    return all_race_ids


def scrape_race_result(race_id: str) -> tuple[dict | None, pd.DataFrame]:
    """
    指定されたレースIDの結果ページをスクレイピングし、(レース情報, 整形済みDataFrame)を返す関数
    """
    url = f"https://db.netkeiba.com/race/{race_id}/"
    try:
        response = requests.get(url)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # --- レース情報の抽出 ---
        race_info = {"id": race_id}

        # <title>タグからレース名などを抽出
        title_tag = soup.find("title")
        if not title_tag:
            return None, pd.DataFrame()  # titleタグがなければ存在しないページ
        title_text = title_tag.text

        # 正規表現でレース名を抽出 (例: 'ジャパンカップ' の部分)
        name_match = re.search(r"(.+?)｜", title_text)
        if name_match:
            race_info["name"] = name_match.group(1).strip()

        # 日付の抽出 (例: 2023年11月26日)
        date_match = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", title_text)
        if date_match:
            dt = datetime.strptime(date_match.group(1), "%Y年%m月%d日")
            race_info["date"] = dt.date()

        # race_idから開催地を抽出
        place_id = race_id[4:6]
        race_info["venue"] = PLACE_MAP.get(place_id, "不明")

        # --- レース結果テーブルの抽出 ---
        race_table = soup.find("table", class_="race_table_01")
        df = pd.read_html(StringIO(str(race_table)))[0]

        cleaned_df = clean_data(df)

        # 必要な情報が全て揃っているか確認
        if "name" in race_info and "date" in race_info and "venue" in race_info:
            return race_info, cleaned_df
        else:
            # 情報が不十分な場合は、存在しないレースと見なす
            return None, pd.DataFrame()

    except IndexError:
        # テーブルが見つからない場合は、存在しないレースと見なす
        return None, pd.DataFrame()
    except Exception as e:
        print(f"エラー: レースID {race_id} の処理中に予期せぬエラーが発生しました: {e}")
        return None, pd.DataFrame()


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
    # 2023年の全レースIDを取得
    race_ids = get_all_race_ids_in_year(2023)

    # (デバッグ用) 少数のIDで試す場合は、以下のようにスライスする
    race_ids = race_ids[:5]  # 5件に減らしてテスト

    all_results = []

    print(f"合計 {len(race_ids)} 件のレース結果をスクレイピングします...")
    # tqdmを使ってプログレスバーを表示
    for race_id in tqdm(race_ids):
        race_info, result_df = scrape_race_result(race_id)

        # 取得したデータにレースIDを列として追加
        if race_info and not result_df.empty:
            print(
                f"\n取得成功: {race_info['name']}, {race_info['date']}, {race_info['venue']}, ({race_id})"
            )
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
