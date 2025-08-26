from flask import Flask, jsonify

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)
# 日本語がJSONで文字化けしないように設定
app.config["JSON_AS_ASCII"] = False


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
