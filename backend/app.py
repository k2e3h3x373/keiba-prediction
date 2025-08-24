from flask import Flask, jsonify

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)


# http://127.0.0.1:5000/api/hello というURLにアクセスがあったときに実行される関数
@app.route("/api/hello")
def hello_world():
    # フロントエンドに返すデータ
    data = {"message": "Hello! This is a response from the backend!"}
    # JSON形式でデータを返す
    return jsonify(data)


# このファイルが直接実行された場合にサーバーを起動する
if __name__ == "__main__":
    # デバッグモードでサーバーを起動
    # これにより、コードを変更したときに自動でサーバーが再起動されるようになります
    app.run(debug=True)
