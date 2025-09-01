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


def preprocess_data(df: pd.DataFrame):
    """
    データの前処理と特徴量エンジ基本的なエンジニアリングを行う関数
    """
    print("\nデータの前処理を開始します...")

    df_processed = df.copy()

    # 1. 目的変数の作成 (3着以内に入ったか)
    df_processed["within_3_rank"] = df_processed["rank"].apply(
        lambda x: 1 if x <= 3 else 0
    )

    # 2. 特徴量エンジニアリング
    # 'sex_age' (例: "牡4") を 'sex' と 'age' に分割
    df_processed["sex"] = df_processed["sex_age"].str[0]
    df_processed["age"] = df_processed["sex_age"].str[1:].astype(int)

    # 'sex' を数値にエンコード (牡=0, 牝=1, セ=2)
    sex_map = {"牡": 0, "牝": 1, "セ": 2}
    df_processed["sex"] = df_processed["sex"].map(sex_map)

    # 3. 不要な列を削除
    # 目的変数の元になった 'rank'、処理済みの 'sex_age'
    # レース前に分からない情報 (単勝人気など)
    # 今回のモデルでは使わない情報 (名前、日付など)
    df_processed = df_processed.drop(
        columns=[
            "rank",
            "sex_age",
            "single_price",
            "popular",
            "race_name",
            "venue",
            "date",
            "horse_name",
            "jockey_name",
        ]
    )

    # 欠損値を含む行を削除 (今回は'sex'をmapした際に発生する可能性)
    df_processed = df_processed.dropna()

    print("データの前処理が完了しました。")
    return df_processed


def main():
    """
    モデルの訓練と評価を実行するメイン関数
    """
    # ステップ1: データの読み込み
    all_data = load_data()

    # ステップ2: データの前処理
    processed_data = preprocess_data(all_data)

    print("\n--- 前処理後のデータサンプル ---")
    print(processed_data.head())
    print(f"\n合計データ件数: {len(processed_data)}")
    print(f"カラム一覧: {processed_data.columns.tolist()}")


if __name__ == "__main__":
    main()
