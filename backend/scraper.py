import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import time
from tqdm import tqdm
from datetime import datetime
import re

# Flaskアプリケーションのコンテキストをインポート
from app import app, db, Race, Result, Horse, Jockey


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


def save_results_to_db(races_data: list[dict], results_df: pd.DataFrame):
    """
    スクレイピングしたレース情報と結果データをデータベースに保存する関数
    """
    # Flaskのアプリケーションコンテキスト内で実行
    with app.app_context():
        # --- 1. レース情報を保存 ---
        saved_races = 0
        for race_info in races_data:
            # 既に同じIDのレースが存在しないか確認
            exists = db.session.get(Race, race_info["id"])
            if not exists:
                race = Race(**race_info)
                db.session.add(race)
                saved_races += 1

        if saved_races > 0:
            print(f"{saved_races}件の新しいレース情報を追加しました。")

        # --- 2. 馬と騎手の情報を先にまとめて登録 ---
        # 効率化のため、先にDBに存在する馬・騎手をすべて取得
        existing_horses = {h.name for h in Horse.query.all()}
        existing_jockeys = {j.name for j in Jockey.query.all()}

        # スクレイピング結果からユニークな馬名・騎手名を取得
        unique_horses = set(results_df["horse_name"].unique())
        unique_jockeys = set(results_df["jockey_name"].unique())

        # DBに存在しない新しい馬・騎手だけをセッションに追加
        new_horses = unique_horses - existing_horses
        new_jockeys = unique_jockeys - existing_jockeys

        for name in new_horses:
            db.session.add(Horse(name=name))
        for name in new_jockeys:
            db.session.add(Jockey(name=name))

        if new_horses or new_jockeys:
            print(
                f"新しい馬 {len(new_horses)}頭、新しい騎手 {len(new_jockeys)}名を登録します。"
            )

        # --- 3. レース結果を保存 ---
        # 一度コミットして、新しい馬・騎手のIDを確定させる
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"レース・馬・騎手の保存中にエラーが発生: {e}")
            return

        # IDを効率的に引けるように、馬名/騎手名をキーにした辞書を作成
        horse_map = {h.name: h.id for h in Horse.query.all()}
        jockey_map = {j.name: j.id for j in Jockey.query.all()}

        saved_results = 0
        for _, row in tqdm(
            results_df.iterrows(), total=len(results_df), desc="レース結果をDBに保存中"
        ):
            # 既に同じレースの同じ馬番の結果が存在しないか確認
            exists = Result.query.filter_by(
                race_id=row["race_id"], umaban=row["umaban"]
            ).one_or_none()
            if not exists:
                result = Result(
                    race_id=row["race_id"],
                    rank=row["rank"],
                    waku=row["waku"],
                    umaban=row["umaban"],
                    horse_id=horse_map[row["horse_name"]],
                    sex_age=row["sex_age"],
                    jockey_weight=row["jockey_weight"],
                    jockey_id=jockey_map[row["jockey_name"]],
                    single_price=row["single_price"],
                    popular=row["popular"],
                    horse_weight=row["horse_weight"],
                )
                db.session.add(result)
                saved_results += 1

        if saved_results > 0:
            print(f"{saved_results}件の新しいレース結果を追加しました。")

        # 最終的な変更をコミット
        try:
            db.session.commit()
            print("データベースへの保存が完了しました。")
        except Exception as e:
            db.session.rollback()
            print(f"レース結果の保存中にエラーが発生: {e}")


def main():
    """
    スクレイピングとDB保存を実行するメイン関数
    """
    # 2023年の全レースIDを取得
    race_ids = get_all_race_ids_in_year(2023)

    # 動作確認のため、最初の5件に絞る
    race_ids = race_ids[:5]

    all_results = []
    race_info_list = []

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
            race_info_list.append(race_info)

        # サーバーに負荷をかけないための待機
        time.sleep(1)

    # 全てのレース結果を一つのDataFrameに結合
    if all_results:
        # DataFrameのリストを一つのDataFrameに結合
        all_results_df = pd.concat(all_results, ignore_index=True)
        print("\nスクレイピングが完了しました。")
        print("取得したデータの一部:")
        print(all_results_df.head())
        print(f"\n全体の件数: {len(all_results_df)}")

        # データベースに保存
        save_results_to_db(race_info_list, all_results_df)

    else:
        print("有効なデータは一件も取得できませんでした。")


# このファイルが直接実行された場合に、main()関数を呼び出す
if __name__ == "__main__":
    main()
