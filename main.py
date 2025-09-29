# main.py
import uuid
from datetime import datetime

# 必要なモジュールをインポート
from lm_studio_rag.storage import RAGStorage
from lm_studio_rag.lm_studio_client import LMStudioClient
from architecture.concrete_understanding.base import ConcreteUnderstanding
from architecture.concrete_understanding.schema_architecture import EpisodeData
from architecture.user_response.generator import UserResponseGenerator

def setup_storage() -> RAGStorage:
    """RAGStorageを初期化し、サンプルデータを投入する"""
    print("RAGストレージを初期化しています...")
    # 永続化モードで初期化 (データが保存されます)
    storage = RAGStorage(USE_MEMORY_RUN=False)

    # --- サンプルデータの追加 ---
    # ここでは簡単な例を数件だけ追加します。
    # 実際のアプリケーションでは、より多くのデータを事前にロードすることが望ましいです。
    print("サンプルの経験データをデータベースに追加します。")
    
    # sample_experience_data= [
    #     "昔、犬に追いかけられて怖い思いをした",
    #     "子供の頃、人懐っこい犬と遊んで楽しかった",
    #     "私はもともと動物が好きだ"
    # ]
    sample_experience_data = [
        "幼少期に、周囲に家がある田舎と都会の中間くらいの都市で育った。小学4年生の時にTokyo Game Showに行ったことがきっかけで、ゲーム制作に興味を持ち、3ヶ月かけてクソゲーを作った。",
        "小学校の先生の影響を強く受け、作れば自分の欲を叶えられるという考え方を学んだ。周囲からは「聞き魔」と呼ばれる。",
        "強迫観念があり、謎の天使と悪魔のような存在が頭の中に現れる。社会的にまずいと思われる可能性があるため、他人にはあまり話さない。",
        "今を全力で生きることを重視し、真面目で集中力がある。一方で視野が狭く、不注意な面もある。周囲からは真面目な性格で、哲学が好きな変わり者だと言われる。",
        "裏切らないことを最も大切にし、自分が決めたルールは破らない。毎日を全力でやることはやったと言える生き方が理想。",
        "人がどんな考えを持っているのかに興味がある。趣味はゲーム作りで、自分の欲を叶えるために自由に設定を盛り込んだゲームを制作し、販売している。",
        "初対面の人とは、相手が嫌がらないように心がけて接する。親しい友人とは本音で言い合える関係を築いている。人との距離感は慎重に調節していくべきだと考えている。",
        "問題を解決した時や、作ったもので人が幸せになった時に喜びを感じる。大切にしている人や物が自分のせいで被害を被った時に悲しみを感じ、大切にしていたものが壊された時に怒りを感じる。同じ問題に対して進捗があまり感じられない時にストレスを感じやすい。",
        "将来はどんな課題でもより良くカスタマイズしたものを提出できるようにしたい。自分が作ったもので自分がより楽に暮らせるような人生を送りたい。今後の世代が少しでも続いてくれるような社会を実現したい。",
        "コンテストに応募しようとしたが期限切れで応募できなかった。この経験から、早い段階で行動すること、だらだらしないこと、現実を直視することの重要性を学んだ。",
        "現実と理想の間で葛藤している。やりたいことがたくさんあるが、今やっていることを修了するまではそれをすることが許されないため、優先順位をつけざるを得ない状況。",
        "自分が考えたことが叶った時に嬉しさを感じ、他者や自分の大切なものに危害が加えられた時に悲しみや怒りを感じる。自分がやらなければいけないことをしていない時に不安を感じる。",
        "ストレスを感じた時にやるべきことに力を入れる。自分が決めたことは得意で、素直にミスを認めやすい。無意識のうちに何が問題かを考えている。",
        "何かを決断する時は、現状が良くなるかを考える。問題を解決する時は、観察->検証 -> 解決策 -> 解決という手順を踏む。新しいことを学ぶ時は、まず何のための学びかを観察し、具体例を学んでから概念として捉える。",
        "「私は」という言葉をよく使う。頷いたり肯定するジェスチャーをするが、心の中ではただの情報としてカウントしていることが多い。",
        "根本的な価値観はあまり変わっていないが、叶えられるものは限り少ないので優先順位をしっかり考えるようになった。",
        "人に聞きまくる人間の考えを知るのが好きな生命体だと考えている。長所は集中する時間が長いことで、短所は不注意であること。他人からは人に聞きまくる人だと思われている。",
        "他人と意見が対立した場合は、できるだけ納得がいくようにするが、考え方が違うなら離れる。人間関係でトラブルが起きた場合は、責任のありどころを明示して解決しようとするが、ダメなら逃げる。対立やトラブルを避けるために、自分の考えをあまり明確に定義しないようにしている。",
        "人間に対して好きだと言ったことを否定されたことが印象に残っている。Tokyo Game Showでゲーム制作者からフィードバックを受けられたことが成功体験。我を知らない人に見せて引かれた時に小出しにすることのリスクを学んだ。",
        "将来に対する不安はあまりない。自分が良くなった素敵な未来があるだろうと考えている。どこで死んでも良い、今を全力に生きれるような人でありたいと考えている。"
    ]
    
    for d in sample_experience_data:
        storage.save_experience_data(
            text=d,
            metadata={"source": "initial_data"}
        )
 
    print("ストレージの準備が完了しました。")
    return storage

def main_cli():
    """ユーザーが状況を入力し、AIの応答を生成するCLIアプリケーション"""

    storage = setup_storage()
    lm_client = LMStudioClient()

    # 各アーキテクチャのインスタンスを生成
    concrete_process = ConcreteUnderstanding(storage=storage, lm_client=lm_client)
    response_gen = UserResponseGenerator(lm_client=lm_client)

    print("\n--- 自己分析AIシミュレーション --- V1.1")
    print("あなたの身の回りで起きている状況を文章で入力してください。")

    while True:
        try:
            field_info_input = input("\n状況を入力してください (終了するには 'exit' と入力): > ")
            if field_info_input.lower() == 'exit':
                print("アプリケーションを終了します。")
                break
            if not field_info_input:
                continue
            print("\033[37;43m-----section1[抽象的理解の推論]--------\033[0m")
            print("\n推論を実行中... (応答まで数秒かかります)")

            # 1. 抽象的理解の取得
            abstract_result = concrete_process.start_inference(field_info_input)
            if not abstract_result:
                print("エラー: 抽象的理解の取得に失敗しました。")
                continue
            
            print("\033[37;43m-----section2[具体的理解の推論]--------\033[0m")
            
            # 2. 具象的理解データの簡易生成 (CLI入力から作成)
            concrete_info = EpisodeData(
                episode_id=str(uuid.uuid4()),
                thread_id="cli_thread",
                timestamp=datetime.now(),
                sequence_in_thread=0,
                source_type="user_cli_input",
                author="user",
                content_type="situational_description",
                text_content=field_info_input,
                status="active",
                sensitivity_level="medium"
            )
            print("\033[37;43m-----section3[最終応答の推論]--------\033[0m")
            # 3. 最終応答の生成
            final_response = response_gen.generate(
                abstract_info=abstract_result,
                concrete_info=concrete_info,
                field_info=field_info_input
            )

            print("\033[37;43m-----section4[思考の表示]--------\033[0m")
            # 4. 結果の表示
            print("\n--- 推論結果 ---")
            print(f"🤔 推論された意思決定: {final_response.inferred_decision}")
            print(f"🏃 推論された行動: {final_response.inferred_action}")
            
            print("\n--- 思考プロセス ---")
            if final_response.thought_process:
                for key, value in final_response.thought_process.items():
                    print(f"- {key}: {value}")
            
            print("\n--- AIからの応答 ---")
            print(f"- NUANCE: {final_response.nuance}")
            print(f"- DIALOGUE: {final_response.dialogue}")
            print(f"- BEHAVIOR: {final_response.behavior}")
            print("--------------------")

        except Exception as e:
            print(f"\n予期せぬエラーが発生しました: {e}")
            print("処理を続行します。")

if __name__ == "__main__":
    main_cli()
