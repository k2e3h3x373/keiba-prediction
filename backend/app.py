from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import pandas as pd
import joblib

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

# SQLAlchemy と Migrate をFlaskアプリケーションに登録
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# データベースのテーブルを定義するクラス（モデル）
class Race(db.Model):
    # テーブル名
    __tablename__ = "races"

    # カラムの定義
    id = db.Column(db.String(20), primary_key=True)  # 主キー (文字列型に変更)
    name = db.Column(
        db.String(100), nullable=False
    )  # レース名（100文字まで、NULL不可）
    venue = db.Column(db.String(100), nullable=False)  # 開催地（100文字まで、NULL不可）
    date = db.Column(db.Date, nullable=False)  # 開催日（日付型、NULL不可）

    # Raceモデルから関連するResultを簡単に参照できるようにするための設定
    results = db.relationship("Result", backref="race", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "venue": self.venue,
            "date": self.date.strftime("%Y-%m-%d"),
        }

    def __repr__(self):
        return f"<Race {self.name}>"


class Result(db.Model):
    __tablename__ = "results"
    id = db.Column(db.Integer, primary_key=True)
    rank = db.Column(db.Integer, nullable=False)
    waku = db.Column(db.Integer, nullable=False)
    umaban = db.Column(db.Integer, nullable=False)
    sex_age = db.Column(db.String(10), nullable=False)
    jockey_weight = db.Column(db.Float, nullable=False)
    single_price = db.Column(db.Float, nullable=False)
    popular = db.Column(db.Integer, nullable=False)
    horse_weight = db.Column(db.Integer, nullable=False)

    # 外部キーの設定
    race_id = db.Column(db.String(20), db.ForeignKey("races.id"), nullable=False)
    horse_id = db.Column(db.Integer, db.ForeignKey("horses.id"), nullable=False)
    jockey_id = db.Column(db.Integer, db.ForeignKey("jockeys.id"), nullable=False)

    def __repr__(self):
        return f"<Result {self.id}>"


class Horse(db.Model):
    __tablename__ = "horses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    results = db.relationship("Result", backref="horse", lazy=True)

    def __repr__(self):
        return f"<Horse {self.name}>"


class Jockey(db.Model):
    __tablename__ = "jockeys"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    results = db.relationship("Result", backref="jockey", lazy=True)

    def __repr__(self):
        return f"<Jockey {self.name}>"


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
    model_features = ["waku", "umaban", "jockey_weight", "horse_weight", "sex", "age"]
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
