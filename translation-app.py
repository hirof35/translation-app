import tkinter as tk
from tkinter import scrolledtext, messagebox
import requests
import datetime
import os
import json
import threading  # 非同期処理用
from googletrans import Translator

# --- 設定 ---
HISTORY_JSON = "wordbook_jp.json"
# 4.0.0-rc1を使用している場合、これで安定します
translator = Translator()

def load_data():
    if os.path.exists(HISTORY_JSON):
        try:
            with open(HISTORY_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_to_json(word, definition, translation):
    data = load_data()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 構造的なデータ管理
    data[word] = {
        "definition": definition,
        "translation": translation,
        "date": now
    }

    try:
        with open(HISTORY_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Save error: {e}")

def get_definition_thread():
    """GUIフリーズ防止のため別スレッドで実行"""
    word = entry.get().strip().lower()
    if not word:
        return

    # UIを「検索中」の状態にする
    search_button.config(state="disabled")
    status_label.config(text=f"「{word}」を検索中...", fg="gray")
    
    # 別スレッドで実行
    thread = threading.Thread(target=process_search, args=(word,))
    thread.daemon = True
    thread.start()

def process_search(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    
    try:
        response = requests.get(url, timeout=7)
        if response.status_code == 200:
            data = response.json()
            # 意味が複数ある場合も考慮して1つ目を取得
            meanings = data[0].get('meanings', [])
            if not meanings:
                update_ui_error("定義が見つかりませんでした。")
                return
                
            en_def = meanings[0]['definitions'][0]['definition']
            
            # 翻訳処理
            try:
                translated = translator.translate(en_def, src='en', dest='ja').text
            except Exception:
                translated = "（翻訳に失敗しました。再試行してください）"

            # 成功時のUI更新（Tkinterはメインスレッドで更新する必要がある）
            root.after(0, lambda: update_ui_success(word, en_def, translated))
            
        else:
            root.after(0, lambda: update_ui_error(f"「{word}」は見つかりませんでした。"))
            
    except requests.exceptions.RequestException:
        root.after(0, lambda: update_ui_error("ネットワーク接続エラーが発生しました。"))
    finally:
        root.after(0, lambda: search_button.config(state="normal"))

def update_ui_success(word, en_def, translated):
    result_text = f"【 {word.upper()} 】\n\n■ 英定義:\n{en_def}\n\n■ 日本語訳:\n{translated}"
    result_label.config(text=result_text, fg="black")
    
    save_to_json(word, en_def, translated)
    status_label.config(text=f"「{word}」を保存しました", fg="#2e7d32")
    entry.delete(0, tk.END) # 入力欄をクリア

def update_ui_error(msg):
    result_label.config(text=msg, fg="#d32f2f")
    status_label.config(text="エラー", fg="#d32f2f")

def show_history_window():
    history_win = tk.Toplevel(root)
    history_win.title("マイ単語帳 履歴")
    history_win.geometry("600x500")

    text_area = scrolledtext.ScrolledText(history_win, width=70, height=30, font=("Yu Gothic", 10))
    text_area.pack(padx=15, pady=15, fill=tk.BOTH, expand=True)

    data = load_data()
    if data:
        # 新しい登録順に表示（辞書の逆順）
        display_text = ""
        for word in reversed(list(data.keys())):
            info = data[word]
            display_text += f"● {word.upper()}\n"
            display_text += f"   [ 訳 ] {info['translation']}\n"
            display_text += f"   [ 英 ] {info['definition']}\n"
            display_text += f"   [ 日 ] {info['date']}\n"
            display_text += "-"*60 + "\n"
        text_area.insert(tk.INSERT, display_text)
    else:
        text_area.insert(tk.INSERT, "履歴はありません。")
    
    text_area.configure(state='disabled')

# --- UI構築 ---
root = tk.Tk()
root.title("Advanced English Wordbook")
root.geometry("500x580")
root.configure(bg="#f5f5f5")

# メインコンテナ
main_frame = tk.Frame(root, bg="#f5f5f5", padx=20, pady=20)
main_frame.pack(fill=tk.BOTH, expand=True)

tk.Label(main_frame, text="英単語を入力してください", font=("Arial", 12, "bold"), bg="#f5f5f5").pack(pady=(0,10))

entry = tk.Entry(main_frame, font=("Arial", 16), width=25, relief=tk.SOLID, bd=1)
entry.pack(pady=5)
entry.bind("<Return>", lambda e: get_definition_thread()) # Enterキー対応
entry.focus_set() # 起動時にフォーカス

btn_frame = tk.Frame(main_frame, bg="#f5f5f5")
btn_frame.pack(pady=20)

search_button = tk.Button(btn_frame, text="検索 ＆ 保存", command=get_definition_thread, 
                          bg="#4caf50", fg="white", font=("Arial", 10, "bold"), 
                          width=15, height=1, relief=tk.FLAT)
search_button.pack(side=tk.LEFT, padx=10)

tk.Button(btn_frame, text="履歴を表示", command=show_history_window, 
          bg="#2196f3", fg="white", font=("Arial", 10, "bold"), 
          width=15, height=1, relief=tk.FLAT).pack(side=tk.LEFT, padx=10)

status_label = tk.Label(main_frame, text="Ready", font=("MS Gothic", 9), bg="#f5f5f5", fg="gray")
status_label.pack()

# 結果表示エリア（枠を付けて見やすく）
display_frame = tk.LabelFrame(main_frame, text="Result", font=("Arial", 9), bg="white", padx=10, pady=10)
display_frame.pack(fill=tk.BOTH, expand=True, pady=10)

result_label = tk.Label(display_frame, text="", wraplength=400, justify="left", 
                        font=("Arial", 10), bg="white")
result_label.pack(anchor="nw")

root.mainloop()
