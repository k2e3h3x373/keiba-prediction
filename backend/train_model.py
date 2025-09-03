import pandas as pd
from app import app, db
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


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

        # ★★★ 修正点 ★★★
        # カラム名を一つずつ強制的に文字列に変換する
        merged_df.columns = [str(col) for col in merged_df.columns]

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


def train_and_evaluate_model(df: pd.DataFrame):
    """
    データセットを受け取り、モデルの訓練、評価、保存を行う関数
    """
    print("\nモデルの訓練と評価を開始します...")

    # 目的変数 (y) と特徴量 (X) に分割
    X = df.drop("within_3_rank", axis=1)
    y = df["within_3_rank"]

    # データを訓練用とテスト用に分割 (テストデータ20%, 乱数シード42)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # モデルの選択 (ランダムフォレスト)
    model = RandomForestClassifier(n_estimators=100, random_state=42)

    # モデルの訓練
    print("モデルを訓練中...")
    model.fit(X_train, y_train)

    # モデルの評価
    print("モデルを評価中...")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print("-" * 30)
    print(f"モデルの正解率 (Accuracy): {accuracy:.4f}")
    print("-" * 30)

    # 訓練済みモデルの保存
    model_path = "race_prediction_model.pkl"
    joblib.dump(model, model_path)
    print(f"訓練済みモデルを '{model_path}' に保存しました。")

    return model


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

    # ステップ3: モデルの訓練と評価
    if not processed_data.empty:
        train_and_evaluate_model(processed_data)
    else:
        print("訓練データがありません。")


if __name__ == "__main__":
    main()
