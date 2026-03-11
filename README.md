# あるけみすと 市場価格変動確認

Render にデプロイして表示。データは `push_data.py` で送信する。

## データ送信

```bash
cd auto-check
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`cookies.json` に `sessionid` と `csrftoken` を設定し、環境変数を設定してから:

```bash
export RENDER_URL=https://your-app.onrender.com
export API_SECRET=your-secret
python push_data.py
```
