# あるけみすと 市場価格変動確認

## 起動方法

```bash
cd 自動更新金額変動確認用
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`cookies.json` に `sessionid` と `csrftoken` を設定してから:

```bash
python app.py
```

ブラウザで http://127.0.0.1:5001 を開く。
