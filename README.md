# SMS転送ボット

SMS認証が必要なクラウドにログインするときなどにSlackに認証コードを転送するボット

## デモ

bot<br>
```bash
$ python main.py --log-level debug
[2022/10/07 15:01:49.343][   DEBUG] Start...
⚡️ Bolt app is running!
[2022/10/07 15:02:20.26 ][   DEBUG] <<<From 08053177709
2022-10-07 15:01:58
>>>Apple IDコードは次の通りです：737753。コードを共有しないでください。
@apple.com # 737753 %apple.com 
```

Slack<br>
<img src="./doc/img/demo_slack.png" width=700>

## 必須ライブラリ

- pyserial==3.5b0
- psutil==5.8.0
- schedule==1.1.0
- slack-sdk==3.18.3
- slack-bolt==1.15.0
- gsm0338==1.0.0
- jinja2==2.11.3

## インストール方法

```bash
$ pip install -r requirements.txt
```

## 使用方法

- ボット
      
    ```bash
    $ python main.py -h
    usage: main.py [-h] [--log-level {debug,info,warn,error,critical}] [--version]

    optional arguments:
      -h, --help            show this help message and exit
      --log-level {debug,info,warn,error,critical}
                            Set log level.
      --version             show program's version number and exit
    ```

- Slack(スラッシュコマンド一覧)

    - 除外リストに追加

        ```text
        /add_exclusion {対象の文字列} # ex) /add_exclusion NTT DOCOMO
        ```
    - 除外リストから削除

        ```text
        /delete_exclusion {対象の文字列} # ex) /delete_exclusion NTT DOCOMO
        ```
    
    - 除外リストを取得

        ```text
        /get_exclusion
        ```

    - ボットの情報を取得

        ```text
        /get_bot_info
        ```

## NOTE

```text
./
├ config/                  
│     ├ config.ini         : 設定ファイル
│     └ exclude_number.txt : 除外リスト
└ src/
      ├ util.py            : 共通ロジック
      ├ at.py              : ATコマンド
      ├ forwarding_task.py : 転送ロジック
      ├ sms_pdu.py         : PDUパース
      └ main.py            : メインスクリプト
```