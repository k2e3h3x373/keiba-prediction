from flask import Flask, jsonify, request
from flask_migrate import Migrate
from flask_cors import CORS
import os
import pandas as pd
import joblib

# 新しく作成したスクレイパーから関数をインポート
from race_card_scraper import scrape_race_card, preprocess_for_prediction

# モデル定義を分離した`models.py`からdbオブジェクトと必要なモデルをインポート
from models import db, Race


# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)
# 日本語がJSONで文字化けしないように設定
app.config["JSON_AS_ASCII"] = False

# データベース接続設定
# postgresql://<ユーザー名>:<パスワード>@<ホスト>:<ポート>/<データベース名>
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://user:password@localhost:5432/keiba_db"
)
# SQLAlchemyがデータベースの変更を追跡する機能を無効にする（パフォーマンス向上のため）
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# CORSを有効にする。これにより、異なるオリジン（http://localhost:3000）からのリクエストを受け入れる
CORS(app)

# SQLAlchemy と Migrate をFlaskアプリケーションに登録
db.init_app(app)  # dbオブジェクトをアプリケーションに初期化
migrate = Migrate(app, db)


# ============================================
# AIモデルの読み込み
# ============================================
# アプリケーションのルートディレクトリを取得
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "race_prediction_model.pkl")

# モデルの存在チェック
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
    print(f" * AI model loaded from {MODEL_PATH}")
    # 訓練時に使用した特徴量の順番を定義
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
else:
    model = None
    print(f" * Warning: AI model not found at {MODEL_PATH}")


# ============================================
# APIエンドポイント
# ============================================


# http://127.0.0.1:5000/api/hello というURLにアクセスがあったときに実行される関数
@app.route("/api/hello")
def hello_world():
    # フロントエンドに返すデータ
    data = {"message": "Hello! This is a response from the backend!"}
    # JSON形式でデータを返す
    return jsonify(data)


# http://127.0.0.1:5000/api/races というURLにアクセスがあったときに実行される関数
@app.route("/api/races")
def get_races():
    # データベースからすべてのレース情報を取得
    races = Race.query.all()
    # 取得したレースオブジェクトのリストを、辞書のリストに変換
    races_list = [race.to_dict() for race in races]
    # JSON形式でレースリストを返す
    return jsonify(races_list)


@app.route("/api/predict", methods=["POST"])
def predict():
    """
    AIモデルを使ってレース結果を予測するAPI
    """
    if model is None:
        return jsonify({"error": "AI model is not loaded."}), 500

    # POSTリクエストからJSONデータを取得
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "Invalid input"}), 400

    # リクエストデータから予測用データを抽出
    horses_data = json_data.get("horses")
    if not horses_data:
        return jsonify({"error": "Missing 'horses' data"}), 400

    try:
        # 受け取ったデータをpandas DataFrameに変換
        input_df = pd.DataFrame(horses_data)

        # モデルが学習した際の特徴量の順番にカラムを並び替える
        # これにより、リクエストのJSONの順番が違っても正しく予測できる
        input_df_reordered = input_df[model_features]

        # 予測の実行（3着以内に入る確率を予測）
        # predict_probaは [[クラス0の確率, クラス1の確率], ...] という形式で返す
        probabilities = model.predict_proba(input_df_reordered)[:, 1]

        # 予測結果を整形
        predictions = []
        for i, horse in enumerate(horses_data):
            predictions.append(
                {
                    "umaban": horse.get("umaban"),
                    "probability": round(
                        probabilities[i] * 100, 2
                    ),  # %に変換して四捨五入
                }
            )

        return jsonify({"predictions": predictions})

    except Exception as e:
        # エラーハンドリング
        return jsonify({"error": str(e)}), 500


@app.route("/api/predict_from_url", methods=["POST"])
def predict_from_url():
    """
    netkeibaの出馬表URLからレース結果を予測するAPI
    """
    if model is None:
        return jsonify({"error": "AI model is not loaded."}), 500

    # POSTリクエストからJSONデータを取得
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "Invalid input"}), 400

    # URLを取得
    url = json_data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    try:
        # 1. URLから出馬表をスクレイピング
        print(f"スクレイピングを開始します: {url}")
        raw_df = scrape_race_card(url)

        if raw_df.empty:
            return jsonify({"error": "出馬表データの取得に失敗しました。"}), 404

        # 2. 予測用にデータを前処理
        input_df = preprocess_for_prediction(raw_df)

        if input_df.empty:
            return jsonify({"error": "予測可能な馬がいません（データ不足など）。"}), 400

        # モデルが学習した特徴量の順番にカラムを並び替える
        input_df_reordered = input_df[model_features]

        # 3. 予測の実行
        probabilities = model.predict_proba(input_df_reordered)[:, 1]

        # 4. 予測結果を整形
        predictions = []
        # input_dfにはumabanカラムがあるので、それを利用する
        for index, row in input_df.iterrows():
            predictions.append(
                {
                    "umaban": int(row["umaban"]),
                    "probability": round(probabilities[index] * 100, 2),
                }
            )

        print("予測が完了しました。")
        return jsonify({"predictions": predictions})

    except Exception as e:
        # エラーハンドリング
        print(f"エラーが発生しました: {e}")
        return jsonify({"error": str(e)}), 500


# データベースに初期データを投入するためのカスタムコマンド
@app.cli.command("seed")
def seed_db():
    from datetime import date

    # 既存のデータをすべて削除
    Race.query.delete()

    # 初期データの作成
    races_to_seed = [
        Race(name="皐月賞", venue="中山競馬場", date=date(2024, 4, 14)),
        Race(name="天皇賞（春）", venue="京都競馬場", date=date(2024, 4, 28)),
        Race(name="日本ダービー", venue="東京競馬場", date=date(2024, 5, 26)),
    ]

    # データベースセッションにデータを追加
    db.session.bulk_save_objects(races_to_seed)
    # 変更をコミット（確定）
    db.session.commit()
    print("データベースに初期データを投入しました。")


# このファイルが直接実行された場合にサーバーを起動する
if __name__ == "__main__":
    # デバッグモードでサーバーを起動
    # これにより、コードを変更したときに自動でサーバーが再起動されるようになります
    app.run(debug=True)
