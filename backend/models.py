from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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

    # 騎手の成績を追加
    win_rate = db.Column(db.Float, nullable=True)  # 勝率
    place_rate = db.Column(db.Float, nullable=True)  # 連対率
    show_rate = db.Column(db.Float, nullable=True)  # 複勝率

    results = db.relationship("Result", backref="jockey", lazy=True)

    def __repr__(self):
        return f"<Jockey {self.name}>"
