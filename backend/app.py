from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

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
    id = db.Column(db.Integer, primary_key=True)  # 主キー
    name = db.Column(
        db.String(100), nullable=False
    )  # レース名（100文字まで、NULL不可）
    venue = db.Column(db.String(100), nullable=False)  # 開催地（100文字まで、NULL不可）
    date = db.Column(db.Date, nullable=False)  # 開催日（日付型、NULL不可）

    def __repr__(self):
        return f"<Race {self.name}>"


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
    # ダミーのレース情報を作成
    # 本来はここでデータベースから情報を取得する
    dummy_races = [
        {"id": 1, "name": "皐月賞", "venue": "中山競馬場", "date": "2024-04-14"},
        {"id": 2, "name": "天皇賞（春）", "venue": "京都競馬場", "date": "2024-04-28"},
        {"id": 3, "name": "日本ダービー", "venue": "東京競馬場", "date": "2024-05-26"},
    ]
    # JSON形式でレースリストを返す
    return jsonify(dummy_races)


# このファイルが直接実行された場合にサーバーを起動する
if __name__ == "__main__":
    # デバッグモードでサーバーを起動
    # これにより、コードを変更したときに自動でサーバーが再起動されるようになります
    app.run(debug=True)
