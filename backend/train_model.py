import pandas as pd
from sqlalchemy import create_engine
from app import app, db, Result, Race, Horse, Jockey


def load_data():
    """
    データベースから全テーブルのデータを読み込み、一つのDataFrameに結合して返す関数
    """
    print("データベースからデータを読み込んでいます...")
    with app.app_context():
        # SQLAlchemyのエンジンを使って、Pandasで直接SQLクエリを実行
        engine = db.engine

        # 各テーブルをPandas DataFrameとして読み込む
        results_df = pd.read_sql_table("results", engine)
        races_df = pd.read_sql_table("races", engine).rename(
            columns={"id": "race_id", "name": "race_name"}
        )
        horses_df = pd.read_sql_table("horses", engine).rename(
            columns={"id": "horse_id", "name": "horse_name"}
        )
        jockeys_df = pd.read_sql_table("jockeys", engine).rename(
            columns={"id": "jockey_id", "name": "jockey_name"}
        )

        # テーブルを結合(マージ)していく
        # 1. results と races を 'race_id' で結合
        merged_df = pd.merge(results_df, races_df, on="race_id")
        # 2. horses を 'horse_id' で結合
        merged_df = pd.merge(merged_df, horses_df, on="horse_id")
        # 3. jockeys を 'jockey_id' で結合
        merged_df = pd.merge(merged_df, jockeys_df, on="jockey_id")

        # 不要になった外部キーカラムと主キーを削除
        merged_df = merged_df.drop(columns=["id", "race_id", "horse_id", "jockey_id"])

        print("データの読み込みと結合が完了しました。")
        return merged_df


def main():
    """
    モデルの訓練と評価を実行するメイン関数
    """
    # ステップ1: データの読み込み
    all_data = load_data()

    print("\n--- 結合後のデータサンプル ---")
    print(all_data.head())
    print(f"\n合計データ件数: {len(all_data)}")
    print(f"カラム一覧: {all_data.columns.tolist()}")


if __name__ == "__main__":
    main()
