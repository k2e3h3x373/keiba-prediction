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
